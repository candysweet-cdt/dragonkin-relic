# -*- coding: utf-8 -*-
"""龙息斩（服务端）：客户端技能按钮/右键上报，服务端校验并结算。

前方 5.5 格锥形（约 ±65°）内的生物受到伤害并击退；12 秒冷却。
普通剑 8 伤害、觉醒剑 12 伤害。
伤害来源用 `ActorDamageCause.EntityAttack`，攻击者记为玩家，方便战利品与仇恨归属。

每一次施放都会 `NotifyToClient` 回执（命中数 / 未命中 / 拒绝原因），按钮上直接显示，
这样实机一眼就能分辨「服务端没收到事件」和「收到了但没打中」。
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
        print('[fycq-slash] server ready, listening %s.%s.%s' % (
            CLIENT_MOD, CLIENT_SYSTEM, CAST_EVENT))

    def OnCast(self, args):
        args = args or {}
        # 引擎会给跨端事件注入 __id__ = 发送方玩家 id，比客户端自报的更可信
        playerId = args.get('__id__') or args.get('playerId')
        players = serverApi.GetPlayerList()
        if playerId not in players:
            print('[fycq-slash] reject: sender=%r not in players=%r' % (playerId, players))
            return
        print('[fycq-slash] cast from %s' % playerId)

        now = time.time()
        left = COOLDOWN - (now - self.last.get(playerId, 0.0))
        if left > 0:
            self.Reply(playerId, {'state': 'cooldown', 'left': int(math.ceil(left))})
            return

        item = itemName(compFactory.CreateItem(playerId).GetPlayerItem(
            serverApi.GetMinecraftEnum().ItemPosType.CARRIED, 0))
        if item not in SWORDS:
            print('[fycq-slash] reject: carried=%r' % item)
            self.Reply(playerId, {'state': 'no_sword'})
            return

        self.last[playerId] = now
        hits, candidates = self.Swing(playerId, SWORDS[item])
        self.Reply(playerId, {'state': 'hit' if hits else 'miss', 'hits': hits})
        command = compFactory.CreateCommand(LEVEL_ID)
        if command:
            command.SetCommand(SOUND, playerId)
        print('[fycq-slash] %s %s candidates=%d hits=%d' % (
            playerId, item, candidates, hits))

    def Swing(self, playerId, damage):
        itemComp = compFactory.CreateItem(playerId)
        rot = compFactory.CreateRot(playerId).GetRot()
        dx, _, dz = serverApi.GetDirFromRot(rot)
        length = math.sqrt(dx * dx + dz * dz)
        if length < 0.01:
            dx, dz = 0.0, 1.0
        else:
            dx, dz = dx / length, dz / length
        foot = compFactory.CreatePos(playerId).GetFootPos()
        ids = compFactory.CreateGame(playerId).GetEntitiesAround(
            playerId, RANGE + 0.5,
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

    def Reply(self, playerId, payload):
        data = dict(payload)
        data['playerId'] = playerId
        self.NotifyToClient(playerId, RESULT_EVENT, data)
        state = payload.get('state')
        tip = {'cooldown': u'龙息斩冷却中（%d 秒）' % payload.get('left', 0),
               'no_sword': u'需要手持龙牙剑',
               'hit': u'龙息斩命中 %d 个目标' % payload.get('hits', 0),
               'miss': u'龙息斩未命中'}.get(state)
        if tip:
            color = 'GREEN' if state == 'hit' else 'YELLOW'
            compFactory.CreateGame(LEVEL_ID).SetOneTipMessage(
                playerId, serverApi.GenerateColor(color) + tip)
