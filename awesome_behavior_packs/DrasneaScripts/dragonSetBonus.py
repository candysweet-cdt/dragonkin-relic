# -*- coding: utf-8 -*-
"""龙鳞套装效果：四件龙鳞甲（原版/觉醒混搭均可）→ 抗火 I + 生命恢复 I。

每 2 秒检查一次盔甲槽；效果每次续 4 秒，脱下一件后 4 秒内自然消失。
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
CHECK_EVERY = 40          # tick，2 秒
EFFECT_TIME = 4.0         # 秒，比检查间隔长，套装不脱就一直续


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
                effect.AddEffectToEntity('fire_resistance', EFFECT_TIME, 0, False)
                effect.AddEffectToEntity('regeneration', EFFECT_TIME, 0, False)
                if playerId not in self.active:
                    self.active.add(playerId)
                    self.tip(playerId, '龙鳞套装：抗火 + 缓慢恢复')
                    print('[fycq-set] active %s' % playerId)
            elif playerId in self.active:
                self.active.discard(playerId)
                self.tip(playerId, '龙鳞套装效果结束')
                print('[fycq-set] off %s' % playerId)

    def tip(self, playerId, message):
        compFactory.CreateGame(playerId).SetOneTipMessage(
            playerId, serverApi.GenerateColor('GREEN') + message)
