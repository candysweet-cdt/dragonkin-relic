# -*- coding: utf-8 -*-
"""龙息斩（服务端）：两条触发路径，服务端统一校验并结算。

1. 客户端上报（HUD 技能按钮 / 右键）：`FycqDragonSkillCast` —— 依赖跨端事件；
2. 服务端兜底：手持龙牙剑**命中**任何生物（`PlayerAttackEntityEvent`，本包击杀归属已实机
   验证会触发）时直接放锥形斩 —— 完全不依赖跨端上报。

前方 5.5 格锥形（约 ±65°）内的非玩家生物受到伤害并击退；12 秒冷却（两条路共用）。
普通剑 8 伤害、觉醒剑 12 伤害。
伤害来源用 `ActorDamageCause.EntityAttack`，攻击者记为玩家，方便战利品与仇恨归属。

每次施放都会 `NotifyToClient` 回执（命中数 / 未命中 / 拒绝原因），按钮上直接显示，
这样实机一眼就能分辨「服务端没收到」和「收到了但没打中」。
"""
import math
import time

import mod.server.extraServerApi as serverApi

ServerSystem = serverApi.GetServerSystemCls()
compFactory = serverApi.GetEngineCompFactory()
LEVEL_ID = serverApi.GetLevelId()

CLIENT_MOD = 'DrasneaScripts'
CLIENT_SYSTEM = 'DragonSkillClient'
CAST_EVENT = 'FycqDragonSkillCast'
RESULT_EVENT = 'FycqDragonSkillResult'

SWORDS = {
    'fycq:dragon_fang_sword': 8,
    'fycq:dragon_fang_sword_awakened': 12,
}
RANGE = 5.5
SCAN_RADIUS = int(RANGE + 0.5)   # 引擎的 get_entity_around 只收整数半径
HALF_ANGLE = 65.0
COOLDOWN = 12.0
SOUND = '/playsound mob.enderdragon.growl @s ~ ~ ~ 1 1.25'


def itemName(itemDict):
    return (itemDict or {}).get('newItemName') or (itemDict or {}).get('itemName') or ''


def dot(ax, az, bx, bz):
    return ax * bx + az * bz


class DragonSlashServer(ServerSystem):

    def __init__(self, namespace, systemName):
        super(DragonSlashServer, self).__init__(namespace, systemName)
        self.last = {}
        self.ListenForEvent(CLIENT_MOD, CLIENT_SYSTEM, CAST_EVENT, self, self.OnCast)
        # 服务端本地兜底：手持龙牙剑**命中**任何生物时直接放锥形斩。
        # 这条路只依赖 PlayerAttackEntityEvent（本包击杀归属已实机验证会触发），
        # 不依赖客户端→服务端事件，所以技能跨端上报万一不通也照样能用。
        self.ListenForEvent(serverApi.GetEngineNamespace(), serverApi.GetEngineSystemName(),
                            'PlayerAttackEntityEvent', self, self.OnPlayerAttack)
        print('[fycq-slash] server ready, listening %s.%s.%s' % (
            CLIENT_MOD, CLIENT_SYSTEM, CAST_EVENT))

    def OnPlayerAttack(self, args):
        playerId = (args or {}).get('playerId')
        victimId = (args or {}).get('victimId')
        if not playerId or playerId not in serverApi.GetPlayerList():
            return
        if playerId == victimId:
            return
        self.TryCast(playerId, 'on-hit', notify=False)

    def OnCast(self, args):
        args = args or {}
        # 引擎会给跨端事件注入 __id__ = 发送方玩家 id，比客户端自报的更可信
        players = serverApi.GetPlayerList()
        playerId = args.get('__id__') or args.get('playerId')
        via = '__id__' if '__id__' in args else 'playerId'
        if playerId not in players:
            # 单机时客户端 id 与服务端 id 可能不同名；只有场上 exactly 1 名玩家才回退，
            # 多人在线时不回退（否则任何人都能冒充别人放技能）
            if len(players) == 1:
                print('[fycq-slash] sender=%r not in %r -> fallback single player' % (
                    playerId, players))
                playerId, via = players[0], 'fallback'
            else:
                print('[fycq-slash] reject: sender=%r not in players=%r' % (playerId, players))
                return
        print('[fycq-slash] cast from %s via %s' % (playerId, via))
        self.TryCast(playerId, via, notify=True)

    def TryCast(self, playerId, via, notify):
        now = time.time()
        left = COOLDOWN - (now - self.last.get(playerId, 0.0))
        if left > 0:
            if notify:
                self.Reply(playerId, {'state': 'cooldown', 'left': int(math.ceil(left))}, notify)
            return
        item = itemName(compFactory.CreateItem(playerId).GetPlayerItem(
            serverApi.GetMinecraftEnum().ItemPosType.CARRIED, 0))
        print('[fycq-slash] carried=%r sword=%s via=%s' % (item, item in SWORDS, via))
        if item not in SWORDS:
            if notify:
                self.Reply(playerId, {'state': 'no_sword'}, notify)
            return
        self.last[playerId] = now
        hits, candidates = self.Swing(playerId, SWORDS[item])
        self.Reply(playerId, {'state': 'hit' if hits else 'miss', 'hits': hits}, notify)
        command = compFactory.CreateCommand(LEVEL_ID)
        if command and hits:
            command.SetCommand(SOUND, playerId)
        print('[fycq-slash] %s %s via=%s candidates=%d hits=%d' % (
            playerId, item, via, candidates, hits))

    def Swing(self, playerId, damage):
        rot = compFactory.CreateRot(playerId).GetRot()
        dx, _, dz = serverApi.GetDirFromRot(rot)
        length = math.sqrt(dx * dx + dz * dz)
        if length < 0.01:
            dx, dz = 0.0, 1.0
        else:
            dx, dz = dx / length, dz / length
        foot = compFactory.CreatePos(playerId).GetFootPos()
        # get_entity_around 的半径必须是整数（传 6.0 会 TypeError: integer argument
        # expected, got float，整条技能在事件回调里静默炸掉）
        ids = compFactory.CreateGame(playerId).GetEntitiesAround(
            playerId, SCAN_RADIUS,
            {'any_of': {'test': 'is_family', 'subject': 'other',
                        'operator': 'not', 'value': 'player'}}) or []
        cause = serverApi.GetMinecraftEnum().ActorDamageCause.EntityAttack
        hits = 0
        for eid in ids:
            if eid == playerId:
                continue
            epos = compFactory.CreatePos(eid).GetFootPos()
            if not epos:
                continue
            tx, tz = epos[0] - foot[0], epos[2] - foot[2]
            dist = math.sqrt(tx * tx + tz * tz)
            if dist < 0.01 or dist > RANGE:
                continue
            if math.degrees(math.acos(max(-1.0, min(1.0, dot(tx, tz, dx, dz) / dist)))) > HALF_ANGLE:
                continue
            hurt = compFactory.CreateHurt(eid)
            if not hurt:
                continue
            hurt.Hurt(damage, cause, playerId, None, True)
            hits += 1
        return hits, len(ids)

    def Reply(self, playerId, payload, notify=True):
        data = dict(payload)
        data['playerId'] = playerId
        self.NotifyToClient(playerId, RESULT_EVENT, data)
        if not notify:
            return
        state = payload.get('state')
        tip = {'cooldown': u'龙息斩冷却中（%d 秒）' % payload.get('left', 0),
               'no_sword': u'需要手持龙牙剑',
               'hit': u'龙息斩命中 %d 个目标' % payload.get('hits', 0),
               'miss': u'龙息斩未命中'}.get(state)
        if tip:
            color = 'GREEN' if state == 'hit' else 'YELLOW'
            compFactory.CreateGame(LEVEL_ID).SetOneTipMessage(
                playerId, serverApi.GenerateColor(color) + tip)
