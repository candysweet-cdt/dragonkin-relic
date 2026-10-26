# -*- coding: utf-8 -*-
"""服务端探针：只监听、只打日志，不改任何状态。"""
import mod.server.extraServerApi as serverApi

ServerSystem = serverApi.GetServerSystemCls()
compFactory = serverApi.GetEngineCompFactory()
PREFIX = 'fycq:'


def log(msg):
    print('[fycq-probe] ' + msg)


class DrasneaProbeServer(ServerSystem):

    def __init__(self, namespace, systemName):
        super(DrasneaProbeServer, self).__init__(namespace, systemName)
        engineNs = serverApi.GetEngineNamespace()
        engineSys = serverApi.GetEngineSystemName()
        # 世界侧事件（AddEntityServerEvent 记在世界.md）
        self.ListenForEvent(engineNs, engineSys, 'AddEntityServerEvent', self, self.OnAddEntity)
        # 实体侧事件
        self.ListenForEvent(engineNs, engineSys, 'ActorHurtServerEvent', self, self.OnHurt)
        self.ListenForEvent(engineNs, engineSys, 'MobDieEvent', self, self.OnDie)
        log('server system ready')

    def EngineType(self, entityId):
        comp = compFactory.CreateEngineType(entityId)
        return comp.GetEngineTypeStr() if comp else '?'

    def Health(self, entityId):
        comp = compFactory.CreateAttr(entityId)
        if not comp:
            return -1
        return comp.GetAttrValue(serverApi.GetMinecraftEnum().AttrType.HEALTH)

    def OnAddEntity(self, args):
        engineType = args.get('engineTypeStr') or ''
        if not engineType.startswith(PREFIX):
            return
        log('add %s id=%s pos=(%.1f, %.1f, %.1f) hp=%s'
            % (engineType, args.get('id'), args.get('posX', 0.0),
               args.get('posY', 0.0), args.get('posZ', 0.0),
               self.Health(args.get('id'))))

    def OnHurt(self, args):
        entityId = args.get('entityId')
        engineType = self.EngineType(entityId)
        if not engineType.startswith(PREFIX):
            return
        log('hurt %s id=%s cause=%s dmg=%s hp=%s'
            % (engineType, entityId, args.get('cause'),
               args.get('damage'), self.Health(entityId)))

    def OnDie(self, args):
        entityId = args.get('id')
        engineType = self.EngineType(entityId)
        if not engineType.startswith(PREFIX):
            return
        log('die %s id=%s attacker=%s cause=%s'
            % (engineType, entityId, args.get('attacker'), args.get('cause')))
