# -*- coding: utf-8 -*-
"""龙息斩（服务端）：客户端技能按钮/右键上报，服务端校验并结算。

前方 5.5 格锥形（约 ±69°）内的非龙裔生物受到伤害并击退；12 秒冷却。
普通剑 8 伤害、觉醒剑 12 伤害。
伤害来源用 `ActorDamageCause.EntityAttack`，攻击者记为玩家，方便战利品与仇恨归属。
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
        self.ListenForEvent(CLIENT_MOD, CLIENT_SYSTEM, CAST_EVENT, self, self.OnCast)

    def OnCast(self, args):
        playerId = args.get('playerId')
        if playerId not in serverApi.GetPlayerList():
            return
        now = time.time()
        left = COOLDOWN - (now - self.last.get(playerId, 0.0))
        if left > 0:
            self.tip(playerId, serverApi.GenerateColor('YELLOW') +
                     '龙息斩冷却中（%d 秒）' % int(math.ceil(left)))
            return
        item = itemName(compFactory.CreateItem(playerId).GetPlayerItem(
            serverApi.GetMinecraftEnum().ItemPosType.CARRIED, 0))
        if item not in SWORDS:
            return
        self.last[playerId] = now
        hits = self.Swing(playerId, SWORDS[item])
        if hits:
            self.tip(playerId, serverApi.GenerateColor('GREEN') + '龙息斩命中 %d 个目标' % hits)
        else:
            self.tip(playerId, serverApi.GenerateColor('YELLOW') + '龙息斩未命中')
        command = compFactory.CreateCommand(LEVEL_ID)
        if command:
            command.SetCommand(SOUND, playerId)
        print('[fycq-slash] %s %s hits=%d' % (playerId, item, hits))

    def Swing(self, playerId, damage):
        rot = compFactory.CreateRot(playerId).GetRot()
        dx, _, dz = serverApi.GetDirFromRot(rot)
        length = math.sqrt(dx * dx + dz * dz)
        if length < 0.01:
            dx, dz = 0.0, 1.0
        else:
            dx, dz = dx / length, dz / length
        pos = compFactory.CreatePos(playerId).GetPos()
        ids = compFactory.CreateGame(playerId).GetEntitiesAround(
            playerId, RANGE + 0.5, {'test': 'is_family', 'subject': 'other', 'value': 'mob'})
        cause = serverApi.GetMinecraftEnum().ActorDamageCause.EntityAttack
        hits = 0
        for eid in ids or []:
            if eid == playerId:
                continue
            if compFactory.CreateEngineType(eid).GetEngineTypeStr() in ALLY:
                continue
            epos = compFactory.CreatePos(eid).GetPos()
            tx, tz = epos[0] - pos[0], epos[2] - pos[2]
            dist = math.sqrt(tx * tx + tz * tz)
            if dist < 0.01 or dist > RANGE:
                continue
            if (tx * dx + tz * dz) / dist < MIN_DOT:
                continue
            hurt = compFactory.CreateHurt(eid)
            if hurt and hurt.Hurt(damage, cause, playerId, None, True):
                hits += 1
        return hits

    def tip(self, playerId, message):
        compFactory.CreateGame(playerId).SetOneTipMessage(playerId, message)
