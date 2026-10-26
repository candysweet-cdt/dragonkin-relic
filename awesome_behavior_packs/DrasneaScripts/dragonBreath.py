# -*- coding: utf-8 -*-
"""龙息火球落地云：原版 dragon_fireball 的 AoE 云 duration=120 秒，太久。

只处理「本包 BOSS 发射的龙息火球」生成的那朵云：命中后 5 秒销毁。
其它原版云（末影龙/药水）不碰。
龙裔免疫龙息伤害走实体 JSON 的 damage_sensor（cause: magic），不在这里做。
注意：计时器是 Game 组件的 AddTimer，ServerSystem 本身没有 AddTimer。
"""
import time

import mod.server.extraServerApi as serverApi

ServerSystem = serverApi.GetServerSystemCls()
compFactory = serverApi.GetEngineCompFactory()
LEVEL_ID = serverApi.GetLevelId()

BOSS = 'fycq:drasnea'
PROJECTILE = 'minecraft:dragon_fireball'
CLOUD = 'minecraft:area_effect_cloud'
CLOUD_LIFE = 5.0        # 秒
MATCH_SECONDS = 3.0     # 命中后多久内生成的云算这发火球的
MATCH_RADIUS = 4.0      # 云与命中点的最大距离


class DragonBreathServer(ServerSystem):

    def __init__(self, namespace, systemName):
        super(DragonBreathServer, self).__init__(namespace, systemName)
        self.fireballs = set()
        self.impacts = []
        engineNs = serverApi.GetEngineNamespace()
        engineSys = serverApi.GetEngineSystemName()
        self.ListenForEvent(engineNs, engineSys, 'SpawnProjectileServerEvent',
                            self, self.OnSpawnProjectile)
        self.ListenForEvent(engineNs, engineSys, 'ProjectileDoHitEffectEvent',
                            self, self.OnHit)
        self.ListenForEvent(engineNs, engineSys, 'AddEntityServerEvent',
                            self, self.OnAddEntity)

    def isBoss(self, entityId):
        try:
            return compFactory.CreateEngineType(entityId).GetEngineTypeStr() == BOSS
        except Exception:
            return False

    def dimOf(self, entityId):
        try:
            return compFactory.CreateDimension(entityId).GetEntityDimensionId()
        except Exception:
            return -999

    def OnSpawnProjectile(self, args):
        if args.get('projectileIdentifier') != PROJECTILE:
            return
        if self.isBoss(args.get('spawnerId')):
            self.fireballs.add(args.get('projectileId'))

    def OnHit(self, args):
        projectileId = args.get('id')
        srcId = args.get('srcId')
        if projectileId not in self.fireballs and not self.isBoss(srcId):
            return
        self.fireballs.discard(projectileId)
        now = time.time()
        self.impacts = [i for i in self.impacts if now - i[4] <= MATCH_SECONDS]
        self.impacts.append((args.get('x'), args.get('y'), args.get('z'),
                             self.dimOf(srcId), now))

    def OnAddEntity(self, args):
        if args.get('engineTypeStr') != CLOUD:
            return
        pos = (args.get('posX'), args.get('posY'), args.get('posZ'))
        # 云可能在命中事件之前生成，延迟一帧再匹配
        compFactory.CreateGame(LEVEL_ID).AddTimer(
            0.1, self.markCloud, args.get('id'), pos, args.get('dimensionId'))

    def markCloud(self, cloudId, pos, dim):
        now = time.time()
        for x, y, z, d, t in self.impacts:
            if d != dim or now - t > MATCH_SECONDS:
                continue
            if ((x - pos[0]) ** 2 + (y - pos[1]) ** 2 + (z - pos[2]) ** 2
                    <= MATCH_RADIUS ** 2):
                compFactory.CreateGame(LEVEL_ID).AddTimer(CLOUD_LIFE, self.DestroyEntity, cloudId)
                print('[fycq-breath] cloud %s will expire in %.0fs' % (cloudId, CLOUD_LIFE))
                return
