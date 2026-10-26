# -*- coding: utf-8 -*-
"""龙巢召唤：主手拿龙心、背包里有龙鳞，右键龙巢召唤一只龙蛇。

代价：1 龙心 + 4 龙鳞（龙心是龙蛇的玩家击杀保底掉落，龙鳞 6–10，击杀一次基本够再开一次）。
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
        if itemName(args.get('itemDict')) != HEART:
            return
        playerId = args.get('playerId')
        args['cancel'] = True
        itemComp = compFactory.CreateItem(playerId)
        if itemName(itemComp.GetPlayerItem(serverApi.GetMinecraftEnum().ItemPosType.CARRIED, 0)) != HEART:
            self.tip(playerId, serverApi.GenerateColor('YELLOW') + '请把龙心拿在主手')
            return
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
        if hearts < COST_HEART or scales < COST_SCALE:
            self.tip(playerId, serverApi.GenerateColor('RED') +
                     '召唤需要 1 龙心 + 4 龙鳞（背包 %d 心 / %d 鳞）' % (hearts, scales))
            return
        rot = compFactory.CreateRot(playerId).GetRot()
        yaw = ((rot[1] if rot else 0.0) + 180.0) % 360.0
        eid = self.CreateEngineEntityByTypeStr(BOSS, (x + 0.5, y + 1.0, z + 0.5), (0.0, yaw), dim)
        if not eid:
            self.tip(playerId, serverApi.GenerateColor('RED') + '召唤失败，材料未消耗')
            return
        self.consume(itemComp, HEART, COST_HEART)
        self.consume(itemComp, SCALE, COST_SCALE)
        self.last[playerId] = now
        self.bosses[eid] = True
        self.tip(playerId, serverApi.GenerateColor('GREEN') + '龙巢觉醒，龙蛇降临')
        command = compFactory.CreateCommand(LEVEL_ID)
        if command:
            command.SetCommand('/playsound mob.enderdragon.growl @s ~ ~ ~ 2 0.8', playerId)
        print('[fycq-altar] summon by %s at (%s,%s,%s) dim=%s' % (playerId, x, y, z, dim))

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
