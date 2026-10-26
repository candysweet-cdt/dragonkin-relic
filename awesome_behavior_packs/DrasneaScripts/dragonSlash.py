# -*- coding: utf-8 -*-
"""龙牙剑右键：龙息斩。

前方 5.5 格锥形（约 ±69°）内，对非龙裔生物造成伤害并击退；12 秒冷却。
觉醒剑 13 伤害 → 斩击 12；普通剑 10 → 斩击 8。
只打 mob 家族，不误伤玩家；幼龙/祭司/龙卫是友军，跳过。
"""
import math
import time

import mod.server.extraServerApi as serverApi

ServerSystem = serverApi.GetServerSystemCls()
compFactory = serverApi.GetEngineCompFactory()
LEVEL_ID = serverApi.GetLevelId()

SWORDS = {
    'fycq:dragon_fang_sword': 8,
    'fycq:dragon_fang_sword_awakened': 12,
}
ALLY = {'fycq:dragon_whelp', 'fycq:dragon_priest', 'fycq:dragon_guard'}
RANGE = 5.5
MIN_DOT = 0.35            # 约 ±69°
COOLDOWN = 12.0
SOUND = '/playsound mob.enderdragon.growl @s ~ ~ ~ 1 1.25'


def itemName(itemDict):
    return (itemDict or {}).get('newItemName') or (itemDict or {}).get('itemName') or ''


class DragonSlashServer(ServerSystem):

    def __init__(self, namespace, systemName):
        super(DragonSlashServer, self).__init__(namespace, systemName)
        self.last = {}
        self.lastBlockUse = {}
        self.ListenForEvent(serverApi.GetEngineNamespace(), serverApi.GetEngineSystemName(),
                            'ServerItemTryUseEvent', self, self.OnTryUse)
        self.ListenForEvent(serverApi.GetEngineNamespace(), serverApi.GetEngineSystemName(),
                            'ServerItemUseOnEvent', self, self.OnUseOn)

    def OnUseOn(self, args):
        # 右键方块不是斩击；记一下，防止同一次右键同时触发修复/斩击
        if args.get('entityId'):
            self.lastBlockUse[args.get('entityId')] = time.time()

    def OnTryUse(self, args):
        item = itemName(args.get('itemDict'))
        if item not in SWORDS:
            return
        playerId = args.get('playerId')
        now = time.time()
        if now - self.lastBlockUse.get(playerId, 0.0) < 0.2:
            return
        args['cancel'] = True
        left = COOLDOWN - (now - self.last.get(playerId, 0.0))
        if left > 0:
            self.tip(playerId, serverApi.GenerateColor('YELLOW') +
                     '龙息斩冷却中（%d 秒）' % int(math.ceil(left)))
            return
        rot = compFactory.CreateRot(playerId).GetRot()
        dx, _, dz = serverApi.GetDirFromRot(rot)
        length = math.sqrt(dx * dx + dz * dz)
        if length < 0.01:
            dx, dz = 0.0, 1.0
        else:
            dx, dz = dx / length, dz / length
        pos = compFactory.CreatePos(playerId).GetPos()
        game = compFactory.CreateGame(playerId)
        ids = game.GetEntitiesAround(playerId, RANGE + 0.5,
                                     {'test': 'is_family', 'subject': 'other', 'value': 'mob'})
        hits = 0
        for eid in ids or []:
            if eid == playerId:
                continue
            etype = compFactory.CreateEngineType(eid).GetEngineTypeStr()
            if etype in ALLY:
                continue
            epos = compFactory.CreatePos(eid).GetPos()
            tx, tz = epos[0] - pos[0], epos[2] - pos[2]
            dist = math.sqrt(tx * tx + tz * tz)
            if dist < 0.01 or dist > RANGE:
                continue
            if (tx * dx + tz * dz) / dist < MIN_DOT:
                continue
            hurt = compFactory.CreateHurt(eid)
            if hurt and hurt.Hurt(SWORDS[item], serverApi.GetMinecraftEnum().ActorDamageCause.EntityAttack,
                                  playerId, None, True):
                hits += 1
        if hits:
            self.tip(playerId, serverApi.GenerateColor('GREEN') + '龙息斩命中 %d 个目标' % hits)
        else:
            self.tip(playerId, serverApi.GenerateColor('YELLOW') + '龙息斩未命中')
        compFactory.CreateCommand(LEVEL_ID).SetCommand(SOUND, playerId)
        self.last[playerId] = now
        print('[fycq-slash] %s %s hits=%d' % (playerId, item, hits))

    def tip(self, playerId, message):
        compFactory.CreateGame(playerId).SetOneTipMessage(playerId, message)
