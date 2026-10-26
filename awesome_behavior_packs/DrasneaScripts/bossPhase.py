# -*- coding: utf-8 -*-
"""龙蛇 BOSS：血量三阶段 + 限量召唤幼龙。

阶段（ActorHurtServerEvent 读血量比例）：
  66% → phase2：移速 0.36 / 伤害 16 / 震地 CD 8 / 火球升级龙息火球 / 加冲锋 / 血条「龙蛇·血怒」
  33% → phase3：移速 0.42 / 伤害 22 / 震地 CD 6 / 贴身灼烧(area_attack) / 召唤 3 只 / 血条「龙蛇·狂怒」

召唤为什么走脚本：JSON 的 behavior.summon_entity 没有数量上限，多只 BOSS/祭司叠起来
会直接堆爆刷怪量。这里统一按「全场幼龙总数 ≤ SUMMON_CAP」限流，任何来源（蛋、
祭司、BOSS）召唤的幼龙都计入。

注意：
  · ActorHurtServerEvent 在死亡后还会再触发一次（实测 hp=-8.5），必须 hp>0 守卫
  · 幼龙集合会包含蛋召唤的，卸载/死亡后靠 engine type 校验清理，避免虚高占用名额
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
PHASE_SUMMON = {1: 1, 2: 2, 3: 3}   # 每次召唤波次生成几只（受总量上限约束）
SUMMON_CAP = 8                      # 全场幼龙总数上限
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
        self.whelps = set()
        self.phase = {}
        self.tick = 0
        self.lastSummonLog = -LOG_EVERY
        self.ListenForEvent(engineNs, engineSys, 'AddEntityServerEvent', self, self.OnAddEntity)
        self.ListenForEvent(engineNs, engineSys, 'ActorHurtServerEvent', self, self.OnHurt)
        self.ListenForEvent(engineNs, engineSys, 'MobDieEvent', self, self.OnDie)
        self.ListenForEvent(engineNs, engineSys, 'OnScriptTickServer', self, self.OnTick)
        log('phase+summon ready (cap=%d)' % SUMMON_CAP)

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
        elif t == WHELP:
            self.whelps.add(eid)

    def OnDie(self, args):
        eid = args.get('id')
        self.bosses.discard(eid)
        self.priests.discard(eid)
        self.whelps.discard(eid)
        self.phase.pop(eid, None)

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

    # ---------------- 限量召唤 ----------------
    def OnTick(self, args=None):
        self.tick += 1
        if self.tick % SUMMON_EVERY:
            return
        try:
            self.Summon()
        except Exception as e:
            log('Summon error: %s' % e)

    def Summon(self):
        # 清理已死/已卸载的幼龙，避免名额被虚占
        self.whelps = set(w for w in self.whelps if self.EngineType(w) == WHELP)
        slots = SUMMON_CAP - len(self.whelps)
        if slots <= 0:
            self.LogSummon('cap reached (%d/%d), skip' % (len(self.whelps), SUMMON_CAP))
            return
        spawned = 0
        for boss in sorted(self.bosses):
            if slots <= 0:
                break
            if self.EngineType(boss) != BOSS:
                self.bosses.discard(boss)
                continue
            count = min(PHASE_SUMMON.get(self.phase.get(boss, 1), 1), slots)
            for _ in range(count):
                if self.SpawnWhelp(boss):
                    slots -= 1
                    spawned += 1
        for priest in sorted(self.priests):
            if slots <= 0:
                break
            if self.EngineType(priest) != PRIEST:
                self.priests.discard(priest)
                continue
            if self.SpawnWhelp(priest):
                slots -= 1
                spawned += 1
        if spawned:
            self.LogSummon('summon %d whelp (now %d/%d)' % (spawned, len(self.whelps), SUMMON_CAP))

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
            if eid:
                self.whelps.add(eid)
                return True
        except Exception as e:
            log('SpawnWhelp error: %s' % e)
        return False

    def LogSummon(self, msg):
        if self.tick - self.lastSummonLog >= LOG_EVERY:
            self.lastSummonLog = self.tick
            log(msg)
