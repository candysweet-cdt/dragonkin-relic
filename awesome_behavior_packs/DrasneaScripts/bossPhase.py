# -*- coding: utf-8 -*-
"""龙蛇 BOSS：血量三阶段 + 每只召唤者限量召唤。

阶段（ActorHurtServerEvent 读血量比例）：
  66% → phase2：移速 0.36 / 伤害 16 / 震地 CD 8 / 火球升级龙息火球 / 加冲锋 / 血条「龙蛇·血怒」
  33% → phase3：移速 0.42 / 伤害 22 / 震地 CD 6 / 贴身灼烧(area_attack) / 血条「龙蛇·狂怒」

召唤为什么走脚本：JSON 的 behavior.summon_entity 没有数量上限，多只 BOSS/祭司叠起来
会堆爆刷怪量。这里按每个召唤者独立计数限流：
  · 每只龙蛇最多同时保有自己的 6 只幼龙（phase1/2/3 每波 1/2/3 只）
  · 每只龙祭司最多 2 只
  · 玩家用刷怪蛋召的、野生的幼龙不计入、不受限（不归任何召唤者）

注意：ActorHurtServerEvent 在死亡后还会再触发一次（实测 hp=-8.5），必须 hp>0 守卫。
"""
import math
import random

import mod.server.extraServerApi as serverApi

ServerSystem = serverApi.GetServerSystemCls()
compFactory = serverApi.GetEngineCompFactory()

BOSS = 'fycq:drasnea'
PRIEST = 'fycq:dragon_priest'
WHELP = 'fycq:dragon_whelp'

PHASES = ((2, 0.66, 'fycq:drasnea_phase2'),
          (3, 0.33, 'fycq:drasnea_phase3'))
PHASE_SUMMON = {1: 1, 2: 2, 3: 3}   # 龙蛇每波生成几只（受自身名额约束）
CAP_BOSS = 6                        # 每只龙蛇同时保有的幼龙上限
CAP_PRIEST = 2                      # 每只祭司同时保有的幼龙上限
SUMMON_EVERY = 300                  # tick：10 秒一波
LOG_EVERY = 900                     # tick：30 秒最多打一条召唤日志


def log(msg):
    print('[fycq-phase] ' + msg)


class BossPhaseServer(ServerSystem):

    def __init__(self, namespace, systemName):
        super(BossPhaseServer, self).__init__(namespace, systemName)
        engineNs = serverApi.GetEngineNamespace()
        engineSys = serverApi.GetEngineSystemName()
        self.bosses = set()
        self.priests = set()
        self.phase = {}
        self.summoned = {}      # ownerId -> set(whelpId)，按召唤者独立计数
        self.ownerOf = {}       # whelpId -> ownerId
        self.tick = 0
        self.lastSummonLog = -LOG_EVERY
        self.ListenForEvent(engineNs, engineSys, 'AddEntityServerEvent', self, self.OnAddEntity)
        self.ListenForEvent(engineNs, engineSys, 'ActorHurtServerEvent', self, self.OnHurt)
        self.ListenForEvent(engineNs, engineSys, 'MobDieEvent', self, self.OnDie)
        self.ListenForEvent(engineNs, engineSys, 'OnScriptTickServer', self, self.OnTick)
        log('phase ready | cap boss=%d priest=%d' % (CAP_BOSS, CAP_PRIEST))

    # ---------------- 基础工具 ----------------
    def EngineType(self, entityId):
        try:
            comp = compFactory.CreateEngineType(entityId)
            return comp.GetEngineTypeStr() if comp else ''
        except Exception:
            return ''

    def OnAddEntity(self, args):
        t = args.get('engineTypeStr') or ''
        eid = args.get('id')
        if t == BOSS:
            self.bosses.add(eid)
            self.phase[eid] = 1
        elif t == PRIEST:
            self.priests.add(eid)

    def OnDie(self, args):
        eid = args.get('id')
        self.bosses.discard(eid)
        self.priests.discard(eid)
        self.phase.pop(eid, None)
        self.summoned.pop(eid, None)
        owner = self.ownerOf.pop(eid, None)
        if owner is not None:
            self.summoned.get(owner, set()).discard(eid)

    # ---------------- 阶段 ----------------
    def OnHurt(self, args):
        entityId = args.get('entityId')
        try:
            if self.EngineType(entityId) != BOSS:
                return
            attr = compFactory.CreateAttr(entityId)
            if not attr:
                return
            health = serverApi.GetMinecraftEnum().AttrType.HEALTH
            hp = attr.GetAttrValue(health)
            hpMax = attr.GetAttrMaxValue(health)
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

    # ---------------- 按召唤者限量召唤 ----------------
    def OnTick(self, args=None):
        self.tick += 1
        if self.tick % SUMMON_EVERY:
            return
        try:
            self.Summon()
        except Exception as e:
            log('Summon error: %s' % e)

    def Summon(self):
        for owner in list(self.bosses) + list(self.priests):
            isBoss = owner in self.bosses
            if self.EngineType(owner) != (BOSS if isBoss else PRIEST):
                self.bosses.discard(owner)
                self.priests.discard(owner)
                continue
            owned = self.summoned.get(owner, set())
            owned = set(w for w in owned if self.EngineType(w) == WHELP)
            self.summoned[owner] = owned
            cap = CAP_BOSS if isBoss else CAP_PRIEST
            room = cap - len(owned)
            if room <= 0:
                continue
            want = PHASE_SUMMON.get(self.phase.get(owner, 1), 1) if isBoss else 1
            spawned = 0
            for _ in range(min(want, room)):
                eid = self.SpawnWhelp(owner)
                if eid:
                    owned.add(eid)
                    self.ownerOf[eid] = owner
                    spawned += 1
            if spawned:
                self.LogSummon('%s summon %d (own %d/%d)'
                               % ('boss' if isBoss else 'priest', spawned, len(owned), cap))

    def SpawnWhelp(self, owner):
        try:
            pos = compFactory.CreatePos(owner).GetPos()
            rot = compFactory.CreateRot(owner).GetRot()
            angle = random.uniform(0, 6.2831853)
            radius = random.uniform(2.0, 3.5)
            at = (pos[0] + radius * math.cos(angle),
                  pos[1],
                  pos[2] + radius * math.sin(angle))
            result = self.CreateEngineEntityByTypeStr(WHELP, at, (0.0, rot[1] if rot else 0.0))
            eid = result[0] if isinstance(result, tuple) else result
            return eid or None
        except Exception as e:
            log('SpawnWhelp error: %s' % e)
        return None

    def LogSummon(self, msg):
        if self.tick - self.lastSummonLog >= LOG_EVERY:
            self.lastSummonLog = self.tick
            log(msg)
