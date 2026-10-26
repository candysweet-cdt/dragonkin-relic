# -*- coding: utf-8 -*-
"""首杀成就：每个玩家第一次击杀龙蛇 → 弹出「龙裔猎人」成就 + 一次性奖励。

成就节点在 customAchievements/dragonkin_first_kill.json；节点不配 goal_details，
由脚本 SetNodeFinish 完成，保证「按玩家各算一次」且与奖励同批触发。
玩家标记写 ExtraData（随存档保存），奖励只发一次。
"""
import mod.server.extraServerApi as serverApi

ServerSystem = serverApi.GetServerSystemCls()
compFactory = serverApi.GetEngineCompFactory()
LEVEL_ID = serverApi.GetLevelId()

BOSS = 'fycq:drasnea'
NODE_ID = 'fycq_dragonkin_first_kill'
FLAG = 'fycq_drasnea_first_kill'
REWARD = (('fycq:dragon_blood_crystal', 3), ('fycq:dragon_scale', 8))


class AchievementServer(ServerSystem):

    def __init__(self, namespace, systemName):
        super(AchievementServer, self).__init__(namespace, systemName)
        self.bosses = {}
        engineNs = serverApi.GetEngineNamespace()
        engineSys = serverApi.GetEngineSystemName()
        self.ListenForEvent(engineNs, engineSys, 'AddEntityServerEvent', self, self.OnAddEntity)
        self.ListenForEvent(engineNs, engineSys, 'MobDieEvent', self, self.OnDie)

    def OnAddEntity(self, args):
        if args.get('engineTypeStr') == BOSS:
            self.bosses[args.get('id')] = True

    def OnDie(self, args):
        eid = args.get('id')
        if eid not in self.bosses and not self.isBoss(eid):
            return
        self.bosses.pop(eid, None)
        attacker = args.get('attacker')
        if attacker not in serverApi.GetPlayerList():
            return
        extra = compFactory.CreateExtraData(attacker)
        if extra.GetExtraData(FLAG):
            return
        extra.SetExtraData(FLAG, 1)
        self.tip(attacker, serverApi.GenerateColor('YELLOW') + '龙裔猎人：首次击杀龙蛇！')
        # MobDieEvent 里不能改玩家手持物品，奖励延迟一帧
        self.AddTimer(0.05, self.grant, attacker)

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
