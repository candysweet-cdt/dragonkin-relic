# -*- coding: utf-8 -*-
"""龙巢召唤：右键龙巢召唤一只龙蛇。

首召（每个世界一次）：主手拿龙鳞，消耗 8 龙鳞，不需要龙心 ——
否则「龙心只有龙蛇掉」会形成死循环。
之后：主手拿龙心，消耗 1 龙心 + 4 龙鳞；祭司 5% 掉龙心、龙蛇玩家击杀保底 1 颗。
限制：龙巢 32 格内已有龙蛇时拒绝；同一玩家 8 秒冷却；龙巢上方要 4 格净空。
"""
import time

import mod.server.extraServerApi as serverApi

ServerSystem = serverApi.GetServerSystemCls()
compFactory = serverApi.GetEngineCompFactory()
LEVEL_ID = serverApi.GetLevelId()

NEST = 'fycq:dragon_nest'
HEART = 'fycq:dragon_heart'
SCALE = 'fycq:dragon_scale'
BOSS = 'fycq:drasnea'

COST_HEART = 1
COST_SCALE = 4
FIRST_COST_SCALE = 8
EVER_FLAG = 'fycq_drasnea_ever_summoned'
FIRST_SUMMON_NODE = 'fycq_dragonkin_first_summon'
NEAR_RADIUS = 32
COOLDOWN = 8.0
INVENTORY_SLOTS = 36


def itemName(itemDict):
    return (itemDict or {}).get('newItemName') or (itemDict or {}).get('itemName') or ''


class AltarSummonServer(ServerSystem):

    def __init__(self, namespace, systemName):
        super(AltarSummonServer, self).__init__(namespace, systemName)
        self.last = {}
        self.bosses = {}
        engineNs = serverApi.GetEngineNamespace()
        engineSys = serverApi.GetEngineSystemName()
        self.ListenForEvent(engineNs, engineSys, 'ServerBlockUseEvent', self, self.OnBlockUse)
        self.ListenForEvent(engineNs, engineSys, 'AddEntityServerEvent', self, self.OnAddEntity)
        self.ListenForEvent(engineNs, engineSys, 'MobDieEvent', self, self.OnDie)

    def OnAddEntity(self, args):
        if args.get('engineTypeStr') == BOSS:
            self.bosses[args.get('id')] = True

    def OnDie(self, args):
        self.bosses.pop(args.get('id'), None)

    def OnBlockUse(self, args):
        if args.get('blockName') != NEST:
            return
        held = itemName(args.get('itemDict'))
        if held not in (HEART, SCALE):
            return
        playerId = args.get('playerId')
        args['cancel'] = True
        itemComp = compFactory.CreateItem(playerId)
        if itemName(itemComp.GetPlayerItem(serverApi.GetMinecraftEnum().ItemPosType.CARRIED, 0)) != held:
            self.tip(playerId, serverApi.GenerateColor('YELLOW') + '请把龙心/龙鳞拿在主手')
            return
        everSummoned = bool(compFactory.CreateExtraData(LEVEL_ID).GetExtraData(EVER_FLAG))
        if held == HEART:
            heartCost, scaleCost = COST_HEART, COST_SCALE
        elif everSummoned:
            self.tip(playerId, serverApi.GenerateColor('YELLOW') +
                     '龙巢首召已完成，请把龙心拿在主手')
            return
        else:
            heartCost, scaleCost = 0, FIRST_COST_SCALE
        now = time.time()
        left = COOLDOWN - (now - self.last.get(playerId, 0))
        if left > 0:
            self.tip(playerId, serverApi.GenerateColor('YELLOW') + '龙巢余烬未散，%d 秒后再试' % int(left + 0.99))
            return
        if self.bossNear(playerId):
            self.tip(playerId, serverApi.GenerateColor('RED') + '龙巢 32 格内已有龙蛇，先击败它')
            return
        dim = compFactory.CreateDimension(playerId).GetEntityDimensionId()
        x, y, z = args.get('x'), args.get('y'), args.get('z')
        if not self.spaceAbove(x, y, z, dim):
            self.tip(playerId, serverApi.GenerateColor('RED') + '龙巢上方需要 4 格净空')
            return
        hearts = self.count(itemComp, HEART)
        scales = self.count(itemComp, SCALE)
        if hearts < heartCost or scales < scaleCost:
            if heartCost:
                message = ('召唤需要 %d 龙心 + %d 龙鳞（背包 %d 心 / %d 鳞）'
                           % (heartCost, scaleCost, hearts, scales))
            else:
                message = '召唤需要 %d 龙鳞（背包 %d 鳞）' % (scaleCost, scales)
            self.tip(playerId, serverApi.GenerateColor('RED') + message)
            return
        rot = compFactory.CreateRot(playerId).GetRot()
        yaw = ((rot[1] if rot else 0.0) + 180.0) % 360.0
        eid = self.CreateEngineEntityByTypeStr(BOSS, (x + 0.5, y + 1.0, z + 0.5), (0.0, yaw), dim)
        if not eid:
            self.tip(playerId, serverApi.GenerateColor('RED') + '召唤失败，材料未消耗')
            return
        if heartCost:
            self.consume(itemComp, HEART, heartCost)
        self.consume(itemComp, SCALE, scaleCost)
        self.last[playerId] = now
        self.bosses[eid] = True
        compFactory.CreateExtraData(LEVEL_ID).SetExtraData(EVER_FLAG, 1)
        compFactory.CreateAchievement(LEVEL_ID).SetNodeFinish(playerId, FIRST_SUMMON_NODE)
        if heartCost:
            message = '龙巢觉醒，龙蛇降临'
        else:
            message = '龙巢初次苏醒（消耗 8 龙鳞），龙蛇降临'
        self.tip(playerId, serverApi.GenerateColor('GREEN') + message)
        command = compFactory.CreateCommand(LEVEL_ID)
        if command:
            command.SetCommand('/playsound mob.enderdragon.growl @s ~ ~ ~ 2 0.8', playerId)
        print('[fycq-altar] summon by %s at (%s,%s,%s) dim=%s cost=%s'
              % (playerId, x, y, z, dim, 'heart' if heartCost else 'first-scales'))

    def bossNear(self, playerId):
        try:
            game = compFactory.CreateGame(playerId)
            filters = {'test': 'is_family', 'subject': 'other', 'value': 'drasnea'}
            if game.GetEntitiesAround(playerId, NEAR_RADIUS, filters):
                return True
        except Exception as e:
            print('[fycq-altar] GetEntitiesAround failed: %s' % e)
        nestDim = compFactory.CreateDimension(playerId).GetEntityDimensionId()
        nestPos = compFactory.CreatePos(playerId).GetPos()
        for eid in list(self.bosses):
            try:
                if compFactory.CreateEngineType(eid).GetEngineTypeStr() != BOSS:
                    self.bosses.pop(eid, None)
                    continue
                if compFactory.CreateDimension(eid).GetEntityDimensionId() != nestDim:
                    continue
                pos = compFactory.CreatePos(eid).GetPos()
                if (pos[0] - nestPos[0]) ** 2 + (pos[1] - nestPos[1]) ** 2 + (pos[2] - nestPos[2]) ** 2 <= NEAR_RADIUS ** 2:
                    return True
            except Exception:
                self.bosses.pop(eid, None)
        return False

    def spaceAbove(self, x, y, z, dim):
        blockInfo = compFactory.CreateBlockInfo(LEVEL_ID)
        for i in range(1, 5):
            block = blockInfo.GetBlockNew((x, y + i, z), dim)
            if not block or block.get('name') != 'minecraft:air':
                return False
        return True

    def count(self, itemComp, name):
        posType = serverApi.GetMinecraftEnum().ItemPosType.INVENTORY
        total = 0
        for slot in range(INVENTORY_SLOTS):
            item = itemComp.GetPlayerItem(posType, slot)
            if itemName(item) == name:
                total += item.get('count', 0)
        return total

    def consume(self, itemComp, name, amount):
        posType = serverApi.GetMinecraftEnum().ItemPosType.INVENTORY
        left = amount
        for slot in range(INVENTORY_SLOTS):
            if left <= 0:
                return
            item = itemComp.GetPlayerItem(posType, slot)
            if itemName(item) != name:
                continue
            have = item.get('count', 0)
            used = min(have, left)
            itemComp.SetInvItemNum(slot, have - used)
            left -= used

    def tip(self, playerId, message):
        compFactory.CreateGame(playerId).SetOneTipMessage(playerId, message)
