# -*- coding: utf-8 -*-
"""创造/旁观模式下不被追逐。

JSON 侧没有「是否创造模式」的过滤器（官方文档与参考模组全库无此测试项），
所以只能脚本兜底：每 5 tick 检查本包生物的仇恨目标，若目标是创造/旁观玩家就清空。
不改其它任何状态。
"""
import mod.server.extraServerApi as serverApi

ServerSystem = serverApi.GetServerSystemCls()
compFactory = serverApi.GetEngineCompFactory()
LEVEL_ID = serverApi.GetLevelId()
PREFIX = 'fycq:'
CHECK_INTERVAL = 5      # tick（1 秒 30 tick）
LOG_COOLDOWN = 300      # 同一只怪 10 秒内不重复打日志


def log(msg):
    print('[fycq-guard] ' + msg)


class AggroGuardServer(ServerSystem):

    def __init__(self, namespace, systemName):
        super(AggroGuardServer, self).__init__(namespace, systemName)
        engineNs = serverApi.GetEngineNamespace()
        engineSys = serverApi.GetEngineSystemName()
        self.mobs = {}
        self.tick = 0
        self.lastLog = {}
        self.lastAllyLog = {}
        self.ListenForEvent(engineNs, engineSys, 'AddEntityServerEvent', self, self.OnAddEntity)
        self.ListenForEvent(engineNs, engineSys, 'MobDieEvent', self, self.OnDie)
        self.ListenForEvent(engineNs, engineSys, 'OnScriptTickServer', self, self.OnTick)
        log('aggro guard ready')

    def OnAddEntity(self, args):
        engineType = args.get('engineTypeStr') or ''
        if engineType.startswith(PREFIX):
            self.mobs[args.get('id')] = engineType

    def OnDie(self, args):
        self.mobs.pop(args.get('id'), None)

    def OnTick(self, args=None):
        self.tick += 1
        if self.tick % CHECK_INTERVAL:
            return
        safeTypes = (serverApi.GetMinecraftEnum().GameType.Creative,
                     serverApi.GetMinecraftEnum().GameType.Spectator)
        gameComp = compFactory.CreateGame(LEVEL_ID)
        for entityId in list(self.mobs.keys()):
            try:
                action = compFactory.CreateAction(entityId)
                target = action.GetAttackTarget() if action else None
                if not target:
                    continue
                # 兜底 2：仇恨目标是本包另一个生物（同族）→ 立刻放弃，防内讧。
                # JSON 侧的 damage_sensor family 免伤只管伤害，管不住弹射物归属不确定的情况。
                if target in self.mobs:
                    action.SetAttackTarget(None)
                    if self.tick - self.lastAllyLog.get(entityId, -LOG_COOLDOWN) >= LOG_COOLDOWN:
                        self.lastAllyLog[entityId] = self.tick
                        log('drop ally target %s -> %s'
                            % (self.mobs[entityId], self.mobs[target]))
                    continue
                typeComp = compFactory.CreateEngineType(target)
                if not typeComp or typeComp.GetEngineTypeStr() != 'minecraft:player':
                    continue
                if gameComp.GetPlayerGameType(target) not in safeTypes:
                    continue
                action.SetAttackTarget(None)
                if self.tick - self.lastLog.get(entityId, -LOG_COOLDOWN) >= LOG_COOLDOWN:
                    self.lastLog[entityId] = self.tick
                    log('drop target %s -> player %s (creative/spectator)'
                        % (self.mobs[entityId], target))
            except Exception:
                # 实体卸载 / 跨维度时接口会抛，忽略即可
                pass
