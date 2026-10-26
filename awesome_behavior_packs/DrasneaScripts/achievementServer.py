# -*- coding: utf-8 -*-
"""首杀成就：每个玩家第一次击杀龙蛇 → 弹出「龙裔猎人」成就 + 一次性奖励。

MobDieEvent.attacker 在这台引擎上是占位 id（实测 -4294967295），不能用来认击杀者。
改为记录「最后一个打中 BOSS 的玩家」：近战走 PlayerAttackEntityEvent，
弹射物走 ActuallyHurtServerEvent 的 projectileId → GetSourceEntityId 找主人。
击杀时 attacker 不是玩家就用最近 60 秒内的记录。

成就节点在 customAchievements/dragonkin_first_kill.json；节点不配 goal_details，
由脚本 SetNodeFinish 完成，保证「按玩家各算一次」且与奖励同批触发。
玩家标记写 ExtraData（随存档保存），奖励只发一次。
注意：计时器是 Game 组件的 AddTimer，ServerSystem 本身没有 AddTimer。
"""
import time

import mod.server.extraServerApi as serverApi

ServerSystem = serverApi.GetServerSystemCls()
compFactory = serverApi.GetEngineCompFactory()
LEVEL_ID = serverApi.GetLevelId()

BOSS = 'fycq:drasnea'
NODE_ID = 'fycq_dragonkin_first_kill'
FLAG = 'fycq_drasnea_first_kill_v2'
REWARD = (('fycq:dragon_blood_crystal', 3), ('fycq:dragon_scale', 8))
BLAME_TTL = 60.0

FULL_SET_NODE = 'fycq_dragonkin_full_set'
FULL_SET = ('fycq:dragon_scale_helmet', 'fycq:dragon_scale_chestplate',
            'fycq:dragon_scale_leggings', 'fycq:dragon_scale_boots')
CHECK_EVERY = 150        # tick，5 秒查一次
INVENTORY_SLOTS = 36


def itemName(itemDict):
    return (itemDict or {}).get('newItemName') or (itemDict or {}).get('itemName') or ''


class AchievementServer(ServerSystem):

    def __init__(self, namespace, systemName):
        super(AchievementServer, self).__init__(namespace, systemName)
        self.bosses = {}
        self.lastHit = {}
        self.tick = 0
        self.fullSetDone = set()
        engineNs = serverApi.GetEngineNamespace()
        engineSys = serverApi.GetEngineSystemName()
        self.ListenForEvent(engineNs, engineSys, 'AddEntityServerEvent', self, self.OnAddEntity)
        self.ListenForEvent(engineNs, engineSys, 'PlayerAttackEntityEvent', self, self.OnPlayerAttack)
        self.ListenForEvent(engineNs, engineSys, 'ActuallyHurtServerEvent', self, self.OnActuallyHurt)
        self.ListenForEvent(engineNs, engineSys, 'MobDieEvent', self, self.OnDie)
        self.ListenForEvent(engineNs, engineSys, 'OnScriptTickServer', self, self.OnTick)

    def OnAddEntity(self, args):
        if args.get('engineTypeStr') == BOSS:
            self.bosses[args.get('id')] = True

    def OnPlayerAttack(self, args):
        victim = args.get('victimId')
        playerId = args.get('playerId')
        if victim in self.bosses and playerId in serverApi.GetPlayerList():
            self.lastHit[victim] = (playerId, time.time())

    def OnActuallyHurt(self, args):
        victim = args.get('entityId')
        if victim not in self.bosses:
            return
        players = serverApi.GetPlayerList()
        playerId = args.get('srcId')
        if playerId not in players:
            projectileId = args.get('projectileId')
            if projectileId and projectileId != '-1':
                try:
                    playerId = compFactory.CreateBulletAttributes(projectileId).GetSourceEntityId()
                except Exception:
                    playerId = None
        if playerId in players:
            self.lastHit[victim] = (playerId, time.time())

    def OnDie(self, args):
        eid = args.get('id')
        if eid not in self.bosses and not self.isBoss(eid):
            return
        self.bosses.pop(eid, None)
        attacker = args.get('attacker')
        players = serverApi.GetPlayerList()
        if attacker not in players:
            hit = self.lastHit.pop(eid, None)
            if not hit or time.time() - hit[1] > BLAME_TTL:
                return
            attacker = hit[0]
        self.lastHit.pop(eid, None)
        extra = compFactory.CreateExtraData(attacker)
        if extra.GetExtraData(FLAG):
            return
        extra.SetExtraData(FLAG, 1)
        self.tip(attacker, serverApi.GenerateColor('YELLOW') + '龙裔猎人：首次击杀龙蛇！')
        # MobDieEvent 里不能改玩家手持物品，奖励延迟一帧
        compFactory.CreateGame(LEVEL_ID).AddTimer(0.05, self.grant, attacker)

    def OnTick(self, args=None):
        self.tick += 1
        if self.tick % CHECK_EVERY:
            return
        posType = serverApi.GetMinecraftEnum().ItemPosType
        for playerId in serverApi.GetPlayerList():
            if playerId in self.fullSetDone:
                continue
            itemComp = compFactory.CreateItem(playerId)
            names = set()
            for slot in range(INVENTORY_SLOTS):
                names.add(itemName(itemComp.GetPlayerItem(posType.INVENTORY, slot)))
            for slot in range(4):
                names.add(itemName(itemComp.GetPlayerItem(posType.ARMOR, slot)))
            if all(name in names for name in FULL_SET):
                compFactory.CreateAchievement(LEVEL_ID).SetNodeFinish(playerId, FULL_SET_NODE)
                self.fullSetDone.add(playerId)
                print('[fycq-achievement] full set by %s' % playerId)

    def isBoss(self, entityId):
        try:
            return compFactory.CreateEngineType(entityId).GetEngineTypeStr() == BOSS
        except Exception:
            return False

    def grant(self, playerId):
        compFactory.CreateAchievement(LEVEL_ID).SetNodeFinish(playerId, NODE_ID)
        itemComp = compFactory.CreateItem(playerId)
        for name, count in REWARD:
            item = {'newItemName': name, 'newAuxValue': 0, 'count': count}
            if itemComp.SpawnItemToPlayerInv(item, playerId):
                continue
            pos = compFactory.CreatePos(playerId).GetPos()
            dim = compFactory.CreateDimension(playerId).GetEntityDimensionId()
            self.CreateEngineItemEntity(item, dim, pos)
        self.tip(playerId, serverApi.GenerateColor('GREEN') +
                 '龙裔猎人成就达成：龙血结晶 ×3、龙鳞 ×8')
        print('[fycq-achievement] first kill by %s' % playerId)

    def tip(self, playerId, message):
        compFactory.CreateGame(playerId).SetOneTipMessage(playerId, message)
