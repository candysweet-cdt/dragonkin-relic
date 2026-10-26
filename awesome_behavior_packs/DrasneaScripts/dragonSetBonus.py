# -*- coding: utf-8 -*-
"""龙鳞套装效果：四件龙鳞甲（原版/觉醒混搭均可）→ 抗火 I + 生命恢复 I。

每 2 秒检查一次盔甲槽；效果一次给 10 秒，且只在剩余不足 4 秒时才续，
避免反复刷新让状态图标/粒子一闪一闪。脱一件后最多 10 秒自然结束。
不改物品数值，避免和装备 JSON 的防御/韧性打架。
"""
import mod.server.extraServerApi as serverApi

ServerSystem = serverApi.GetServerSystemCls()
compFactory = serverApi.GetEngineCompFactory()

SET_SLOTS = (
    ('fycq:dragon_scale_helmet', 'fycq:dragon_scale_helmet_awakened'),
    ('fycq:dragon_scale_chestplate', 'fycq:dragon_scale_chestplate_awakened'),
    ('fycq:dragon_scale_leggings', 'fycq:dragon_scale_leggings_awakened'),
    ('fycq:dragon_scale_boots', 'fycq:dragon_scale_boots_awakened'),
)
CHECK_EVERY = 40          # tick，2 秒查一次套装状态
EFFECT_TIME = 10.0        # 秒；每次只给 10 秒，避免频繁刷新导致图标/粒子闪
REFRESH_BELOW = 4.0       # 剩余不足 4 秒才续，穿着期间基本只加两次


def itemName(itemDict):
    return (itemDict or {}).get('newItemName') or (itemDict or {}).get('itemName') or ''


class DragonSetBonusServer(ServerSystem):

    def __init__(self, namespace, systemName):
        super(DragonSetBonusServer, self).__init__(namespace, systemName)
        self.tick = 0
        self.active = set()
        self.ListenForEvent(serverApi.GetEngineNamespace(), serverApi.GetEngineSystemName(),
                            'OnScriptTickServer', self, self.OnTick)

    def OnTick(self, args=None):
        self.tick += 1
        if self.tick % CHECK_EVERY:
            return
        posType = serverApi.GetMinecraftEnum().ItemPosType.ARMOR
        for playerId in serverApi.GetPlayerList():
            itemComp = compFactory.CreateItem(playerId)
            worn = [itemName(itemComp.GetPlayerItem(posType, i)) for i in range(4)]
            if all(any(name in worn[i] for name in slot) for i, slot in enumerate(SET_SLOTS)):
                effect = compFactory.CreateEffect(playerId)
                self.ensure(effect, 'fire_resistance')
                self.ensure(effect, 'regeneration')
                if playerId not in self.active:
                    self.active.add(playerId)
                    self.tip(playerId, '龙鳞套装：抗火 + 缓慢恢复')
                    print('[fycq-set] active %s' % playerId)
            elif playerId in self.active:
                self.active.discard(playerId)
                self.tip(playerId, '龙鳞套装效果结束')
                print('[fycq-set] off %s' % playerId)

    def ensure(self, effectComp, name):
        # 只有快到期才重新加：反复 AddEffectToEntity 会让状态图标与粒子一闪一闪
        for effect in effectComp.GetAllEffects() or []:
            if effect.get('effectName') == name:
                if (effect.get('duration_f') or effect.get('duration') or 0) >= REFRESH_BELOW:
                    return
                break
        effectComp.AddEffectToEntity(name, EFFECT_TIME, 0, False)

    def tip(self, playerId, message):
        compFactory.CreateGame(playerId).SetOneTipMessage(
            playerId, serverApi.GenerateColor('GREEN') + message)
