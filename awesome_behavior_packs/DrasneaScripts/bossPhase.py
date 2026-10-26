# -*- coding: utf-8 -*-
"""龙蛇血量三阶段（纯数值+组件组，由脚本在血量阈值处触发实体事件）。

66% → phase2：移速 0.3→0.36、伤害 12→16、震地 CD 12→8、血条名「龙蛇·血怒」
33% → phase3：移速 0.42、伤害 22、震地 CD 6、召唤改成 3 只/CD 14、血条名「龙蛇·狂怒」

注意：ActorHurtServerEvent 在死亡后还会再触发一次（实测 hp=-8.5），必须加 hp>0 守卫。
"""
import mod.server.extraServerApi as serverApi

ServerSystem = serverApi.GetServerSystemCls()
compFactory = serverApi.GetEngineCompFactory()
BOSS = 'fycq:drasnea'
ATTR_HEALTH = None   # 延迟取，避免 import 期就用枚举
PHASES = ((2, 0.66, 'fycq:drasnea_phase2'),
          (3, 0.33, 'fycq:drasnea_phase3'))


def log(msg):
    print('[fycq-phase] ' + msg)


class BossPhaseServer(ServerSystem):

    def __init__(self, namespace, systemName):
        super(BossPhaseServer, self).__init__(namespace, systemName)
        engineNs = serverApi.GetEngineNamespace()
        engineSys = serverApi.GetEngineSystemName()
        self.phase = {}
        self.ListenForEvent(engineNs, engineSys, 'ActorHurtServerEvent', self, self.OnHurt)
        self.ListenForEvent(engineNs, engineSys, 'MobDieEvent', self, self.OnDie)
        log('boss phase ready')

    def OnHurt(self, args):
        entityId = args.get('entityId')
        try:
            typeComp = compFactory.CreateEngineType(entityId)
            if not typeComp or typeComp.GetEngineTypeStr() != BOSS:
                return
            attr = compFactory.CreateAttr(entityId)
            if not attr:
                return
            ATTR_HEALTH = serverApi.GetMinecraftEnum().AttrType.HEALTH
            hp = attr.GetAttrValue(ATTR_HEALTH)
            hpMax = attr.GetAttrMaxValue(ATTR_HEALTH)
            if not hp or not hpMax or hp <= 0:
                return          # 尸体上不再触发（死亡后仍会收到一次 hurt）
            ratio = float(hp) / float(hpMax)
            current = self.phase.get(entityId, 1)
            for phase, threshold, event in PHASES:
                if phase > current and ratio <= threshold:
                    compFactory.CreateEntityEvent(entityId).TriggerCustomEvent(entityId, event)
                    self.phase[entityId] = phase
                    log('phase %d | hp %.0f/%.0f (%.0f%%)' % (phase, hp, hpMax, ratio * 100))
        except Exception as e:
            log('OnHurt error: %s' % e)

    def OnDie(self, args):
        self.phase.pop(args.get('id'), None)
