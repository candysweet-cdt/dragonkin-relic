# -*- coding: utf-8 -*-
"""龙息斩技能按钮（客户端 HUD）：手持龙牙剑时出现、可拖动、点击释放。

为什么不只靠右键：`ServerItemTryUseEvent` 对 `netease:weapon` 这种没有使用动画的物品
根本不触发（实机确认），触屏玩家也没有稳定的右键。所以：
  · 主触发 = HUD 技能按钮（按下/移动/弹起自己判定：位移 > 6 只保存位置，不放技能）
  · 备触发 = RightClickBeforeClientEvent（鼠标右键、新触控交互键），不拦截原版交互
两者都只发一个 NotifyToServer，手持校验、伤害与冷却全部由服务端裁决。
按钮位置用 CreateConfigClient 全局配置存盘；冷却数字只是本地显示。
"""
import math
import time

import mod.client.extraClientApi as clientApi

ClientSystem = clientApi.GetClientSystemCls()
ScreenNode = clientApi.GetScreenNodeCls()
compFactory = clientApi.GetEngineCompFactory()
LEVEL_ID = clientApi.GetLevelId()

MOD_NAME = 'DrasneaScripts'
UI_KEY = 'dragonskillhud'
UI_DEF = 'dragonskillhud.main'
SCREEN_PATH = MOD_NAME + '.dragonSkillClient.DragonSkillHudScreen'
SERVER_SYSTEM = 'DragonSlashServer'
CAST_EVENT = 'FycqDragonSkillCast'
RESULT_EVENT = 'FycqDragonSkillResult'
SWORDS = ('fycq:dragon_fang_sword', 'fycq:dragon_fang_sword_awakened')
COOLDOWN = 12.0
CONFIG_KEY = 'fycq_dragonskill_hud'
BTN_PATH = '/skillPanel/skillButton'
LABEL_PATH = BTN_PATH + '/button_label'
DRAG_SLOP = 6.0
REFRESH_EVERY = 20         # tick，兜底刷新可见性（进世界/换存档时事件可能不补发）
FLASH_TICKS = 30           # 服务端回执在按钮上停留的 tick 数
# 世界粒子的发射方向是 JSON 里写死的，所以「锥形」靠沿朝向摆点做出来
BREATH_FX = 'effects/fycq_dragon_breath.json'
HIT_FX = 'effects/fycq_dragon_breath_hit.json'
FX_STEPS = (0.6, 1.6, 2.7, 3.8)
FX_HEIGHT = 1.35           # 喷息高度（玩家脚底往上）
FX_LIFE = 1.2              # 秒，到点回收，不留垃圾粒子实体
FX_MAX = 16

_node = [None]
_system = [None]


def itemName(itemDict):
    return (itemDict or {}).get('newItemName') or (itemDict or {}).get('itemName') or ''


def heldIsSword():
    item = compFactory.CreateItem(clientApi.GetLocalPlayerId()).GetPlayerItem(
        clientApi.GetMinecraftEnum().ItemPosType.CARRIED, 0)
    return itemName(item) in SWORDS


class DragonSkillHudScreen(ScreenNode):

    def __init__(self, namespace, name, param):
        ScreenNode.__init__(self, namespace, name, param)
        self.btn = None
        self.label = None
        self._dragFrom = None
        self._touchFrom = None
        self._moved = False

    def Create(self):
        self.btn = self.GetBaseUIControl(BTN_PATH)
        if self.btn is None:
            print('[fycq-skill] missing control %s' % BTN_PATH)
            return
        button = self.btn.asButton()
        button.AddTouchEventParams({'isSwallow': True})
        button.SetButtonTouchDownCallback(self.OnDown)
        button.SetButtonTouchMoveCallback(self.OnMove)
        button.SetButtonTouchUpCallback(self.OnUp)
        self.label = self.GetBaseUIControl(LABEL_PATH)
        pos = self._loadPos()
        if pos:
            self.btn.SetPosition(pos)
        self.btn.SetVisible(False)
        _node[0] = self
        print('[fycq-skill] hud created')

    def Destroy(self):
        if _node[0] is self:
            _node[0] = None

    def OnDown(self, args):
        self._moved = False
        self._dragFrom = self.btn.GetPosition()
        self._touchFrom = (args.get('TouchPosX'), args.get('TouchPosY'))

    def OnMove(self, args):
        if not self._dragFrom or self._touchFrom[0] is None:
            return
        dx = args.get('TouchPosX') - self._touchFrom[0]
        dy = args.get('TouchPosY') - self._touchFrom[1]
        if abs(dx) > DRAG_SLOP or abs(dy) > DRAG_SLOP:
            self._moved = True
        self.btn.SetPosition((self._dragFrom[0] + dx, self._dragFrom[1] + dy))

    def OnUp(self, args):
        print('[fycq-skill] touch up moved=%s system=%s' % (self._moved, bool(_system[0])))
        if self._moved:
            self._savePos(self.btn.GetPosition())
        elif _system[0]:
            _system[0].RequestCast()
        self._dragFrom = None
        self._moved = False

    def show(self, shown):
        if self.btn:
            self.btn.SetVisible(bool(shown))

    def setLabel(self, text):
        if not self.label:
            return
        try:
            self.label.asLabel().SetText(text)
        except Exception:
            pass

    def _loadPos(self):
        try:
            data = compFactory.CreateConfigClient(LEVEL_ID).GetConfigData(CONFIG_KEY, True) or {}
            pos = data.get('btnPos')
            if pos and len(pos) == 2:
                return (float(pos[0]), float(pos[1]))
        except Exception:
            pass
        return None

    def _savePos(self, pos):
        try:
            comp = compFactory.CreateConfigClient(LEVEL_ID)
            data = comp.GetConfigData(CONFIG_KEY, True) or {}
            data['btnPos'] = [pos[0], pos[1]]
            comp.SetConfigData(CONFIG_KEY, data, True)
            print('[fycq-skill] button moved to (%.0f, %.0f)' % (pos[0], pos[1]))
        except Exception:
            pass


class DragonSkillClient(ClientSystem):

    def __init__(self, namespace, systemName):
        super(DragonSkillClient, self).__init__(namespace, systemName)
        _system[0] = self
        self.tick = 0
        self.cdUntil = 0.0
        self.lastSent = 0.0
        self.flashText = ''
        self.flashUntil = 0.0
        self.fxIds = []
        engineNs = clientApi.GetEngineNamespace()
        engineSys = clientApi.GetEngineSystemName()
        self.ListenForEvent(engineNs, engineSys, 'UiInitFinished', self, self.OnUiInit)
        self.ListenForEvent(engineNs, engineSys, 'OnCarriedNewItemChangedClientEvent',
                            self, self.OnCarried)
        self.ListenForEvent(engineNs, engineSys, 'RightClickBeforeClientEvent',
                            self, self.OnRightClick)
        self.ListenForEvent(engineNs, engineSys, 'OnScriptTickClient', self, self.OnTick)
        self.ListenForEvent(MOD_NAME, SERVER_SYSTEM, RESULT_EVENT, self, self.OnResult)
        print('[fycq-skill] client system ready')

    def OnUiInit(self, args):
        clientApi.RegisterUI(MOD_NAME, UI_KEY, SCREEN_PATH, UI_DEF)
        clientApi.CreateUI(MOD_NAME, UI_KEY, {'isHud': 1})
        self.refresh()

    def OnCarried(self, args):
        self.refresh()

    def OnRightClick(self, args):
        sword = heldIsSword()
        print('[fycq-skill] right click heldSword=%s' % sword)
        if sword:
            self.RequestCast()

    def OnTick(self, args=None):
        self.tick += 1
        if self.tick % 200 == 0:
            print('[fycq-skill] alive tick=%d node=%s' % (self.tick, bool(_node[0])))
        node = _node[0]
        if not node:
            return
        if self.tick % 5 == 0:
            now = time.time()
            if now < self.flashUntil:
                node.setLabel(self.flashText)
            else:
                left = self.cdUntil - now
                node.setLabel('%d' % int(math.ceil(left)) if left > 0 else '')
        if self.tick % REFRESH_EVERY == 0:
            self.refresh()

    def OnResult(self, args):
        args = args or {}
        state = args.get('state')
        if state == 'cooldown':
            self.cdUntil = time.time() + (args.get('left') or 0)
            self.flashText = ''
            self.flashUntil = 0.0
            return
        if state == 'hit':
            self.flashText = '%d' % args.get('hits', 0)
            self.SpawnHitFx(args.get('positions'))
        elif state == 'no_sword':
            self.flashText = u'剑'
        else:
            self.flashText = '0'
        self.flashUntil = time.time() + FLASH_TICKS / 20.0
        print('[fycq-skill] server ack %s' % args)

    # ---- 特效：世界粒子（客户端建，创建后必须 Play 才播） ----
    def SpawnFx(self, path, pos):
        try:
            pid = self.CreateEngineParticle(path, (float(pos[0]), float(pos[1]), float(pos[2])))
        except Exception as e:
            print('[fycq-fx] CreateEngineParticle 异常 %r' % (e,))
            return
        if not pid:
            print('[fycq-fx] 建粒子失败 %s' % path)
            return
        try:
            control = compFactory.CreateParticleControl(pid)
            if control is not None:
                control.Play()
        except Exception as e:
            print('[fycq-fx] Play 异常 %r' % (e,))
        while len(self.fxIds) >= FX_MAX:
            self.RecycleFx(self.fxIds[0])
        self.fxIds.append(pid)
        try:
            compFactory.CreateGame(LEVEL_ID).AddTimer(FX_LIFE, self.RecycleFx, pid)
        except Exception as e:
            print('[fycq-fx] 回收定时器异常 %r' % (e,))

    def RecycleFx(self, pid):
        if pid in self.fxIds:
            self.fxIds.remove(pid)
        try:
            self.DestroyEntity(pid)
        except Exception as e:
            print('[fycq-fx] DestroyEntity 异常 %r' % (e,))

    def SpawnCastFx(self):
        """沿玩家朝向摆 4 个喷息点，做出「一口龙息扫出去」的锥形。"""
        playerId = clientApi.GetLocalPlayerId()
        pos = compFactory.CreatePos(playerId).GetPos()
        if not pos:
            return
        dx, _, dz = clientApi.GetDirFromRot(compFactory.CreateRot(playerId).GetRot())
        length = (dx * dx + dz * dz) ** 0.5
        if length < 0.01:
            dx, dz = 0.0, 1.0
        else:
            dx, dz = dx / length, dz / length
        for step in FX_STEPS:
            self.SpawnFx(BREATH_FX, (pos[0] + dx * step, pos[1] + FX_HEIGHT,
                                     pos[2] + dz * step))

    def SpawnHitFx(self, positions):
        for pos in (positions or [])[:4]:
            try:
                self.SpawnFx(HIT_FX, (pos[0], pos[1] + 1.1, pos[2]))
            except (TypeError, IndexError):
                continue

    def refresh(self):
        node = _node[0]
        if node:
            node.show(heldIsSword())

    def RequestCast(self):
        now = time.time()
        if now < self.cdUntil:
            print('[fycq-skill] blocked by local cd %.1fs' % (self.cdUntil - now))
            return
        if now - self.lastSent < 0.3:
            print('[fycq-skill] blocked by 0.3s debounce')
            return
        print('[fycq-skill] request cast localId=%s' % clientApi.GetLocalPlayerId())
        try:
            self.NotifyToServer(CAST_EVENT, {'playerId': clientApi.GetLocalPlayerId()})
        except Exception as e:
            print('[fycq-skill] NotifyToServer FAILED %r' % (e,))
            self.tip(u'技能上报异常 %r' % (e,))
            return
        # 冷却只在真正发出去之后才起算，否则按钮会假装有倒计时
        self.lastSent = now
        self.cdUntil = now + COOLDOWN
        self.flashUntil = 0.0
        self.SpawnCastFx()
        print('[fycq-skill] sent cast')

    def tip(self, message):
        try:
            compFactory.CreateGame(clientApi.GetLevelId()).SetTipMessage(message)
        except Exception:
            pass
