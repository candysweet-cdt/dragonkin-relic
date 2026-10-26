# -*- coding: utf-8 -*-
"""龙巢修复：手拿龙裔装备右键龙巢，消耗龙鳞回满耐久（保留附魔与自定义名）。

为什么不做铁砧修复（实测 + 官方文档结论）：
  · 工具：铁砧材料被 netease:weapon.level 锁死（0 木/金、1 石、2 铁、3 钻石、>3 不能修），
    level 同时是挖掘等级，降到 2 就挖不了黑曜石，所以龙鳞进不了铁砧。
  · 盔甲：netease:armor 没有修复材料字段，铁砧完全修不了。
  · minecraft:repairable 在本引擎不生效，已从装备 JSON 撤掉。
所以修复走龙巢交互：主手/副手拿装备，右键龙巢，1 片龙鳞 = 25% 最大耐久（向上取整）。
另保留合成台重铸配方（装备 + 2 龙鳞 → 新件），两条路互补。
"""
import math

import mod.server.extraServerApi as serverApi

ServerSystem = serverApi.GetServerSystemCls()
compFactory = serverApi.GetEngineCompFactory()
LEVEL_ID = serverApi.GetLevelId()

NEST = 'fycq:dragon_nest'
SCALE = 'fycq:dragon_scale'
INVENTORY_SLOTS = 36
COST_FRACTION = 0.25        # 1 片龙鳞修复最大耐久的 25%

GEAR = {
    'fycq:dragon_fang_sword': '龙牙剑',
    'fycq:dragon_scale_pickaxe': '龙鳞镐',
    'fycq:dragon_scale_axe': '龙鳞斧',
    'fycq:dragon_scale_shovel': '龙鳞锹',
    'fycq:dragon_scale_hoe': '龙鳞锄',
    'fycq:dragon_scale_helmet': '龙鳞头盔',
    'fycq:dragon_scale_chestplate': '龙鳞胸甲',
    'fycq:dragon_scale_leggings': '龙鳞护腿',
    'fycq:dragon_scale_boots': '龙鳞靴',
}


def itemName(itemDict):
    return (itemDict or {}).get('newItemName') or (itemDict or {}).get('itemName') or ''


class RepairStationServer(ServerSystem):

    def __init__(self, namespace, systemName):
        super(RepairStationServer, self).__init__(namespace, systemName)
        self.pending = set()
        engineNs = serverApi.GetEngineNamespace()
        engineSys = serverApi.GetEngineSystemName()
        self.ListenForEvent(engineNs, engineSys, 'ServerBlockUseEvent', self, self.OnBlockUse)

    def OnBlockUse(self, args):
        if args.get('blockName') != NEST:
            return
        playerId = args.get('playerId')
        name = itemName(args.get('itemDict'))
        display = GEAR.get(name)
        if not display:
            return
        args['cancel'] = True
        if playerId in self.pending:
            return
        itemComp = compFactory.CreateItem(playerId)
        posType = self.heldSlot(itemComp, name)
        if posType is None:
            return
        maxDur = itemComp.GetItemMaxDurability(posType, 0, False)
        durability = itemComp.GetItemDurability(posType, 0)
        if maxDur <= 0:
            return
        if durability >= maxDur:
            self.tip(playerId, serverApi.GenerateColor('YELLOW') + '%s 耐久已满' % display)
            return
        need = int(math.ceil((maxDur - durability) / float(maxDur) / COST_FRACTION))
        have, slots = self.countScales(itemComp)
        if have < need:
            self.tip(playerId, serverApi.GenerateColor('RED') +
                     '龙巢需要 %d 片龙鳞修复 %s（背包 %d 片）' % (need, display, have))
            return
        self.pending.add(playerId)
        # SetItemDurability 在方块使用/物品事件里直接调用会失效，必须延迟一帧
        compFactory.CreateGame(LEVEL_ID).AddTimer(
            0.05, self.applyRepair, playerId, posType, maxDur, display, need, slots)
        self.tip(playerId, serverApi.GenerateColor('YELLOW') + '龙巢正在修复 %s…' % display)

    def heldSlot(self, itemComp, name):
        posTypeEnum = serverApi.GetMinecraftEnum().ItemPosType
        for posType in (posTypeEnum.CARRIED, posTypeEnum.OFFHAND):
            if itemName(itemComp.GetPlayerItem(posType, 0)) == name:
                return posType
        return None

    def countScales(self, itemComp):
        posType = serverApi.GetMinecraftEnum().ItemPosType.INVENTORY
        total = 0
        slots = []
        for slot in range(INVENTORY_SLOTS):
            item = itemComp.GetPlayerItem(posType, slot)
            if itemName(item) != SCALE:
                continue
            count = item.get('count', 0)
            if count > 0:
                total += count
                slots.append((slot, count))
        return total, slots

    def consumeScales(self, itemComp, slots, need):
        left = need
        for slot, count in slots:
            if left <= 0:
                break
            used = min(count, left)
            itemComp.SetInvItemNum(slot, count - used)
            left -= used

    def applyRepair(self, playerId, posType, maxDur, display, need, slots):
        self.pending.discard(playerId)
        itemComp = compFactory.CreateItem(playerId)
        if not itemComp.SetItemDurability(posType, 0, maxDur):
            self.tip(playerId, serverApi.GenerateColor('RED') + '龙巢修复失败，龙鳞未消耗')
            return
        self.consumeScales(itemComp, slots, need)
        self.tip(playerId, serverApi.GenerateColor('GREEN') +
                 '龙巢吸收 %d 片龙鳞，%s 已修复' % (need, display))
        command = compFactory.CreateCommand(LEVEL_ID)
        if command:
            command.SetCommand('/playsound random.anvil_use @s ~ ~ ~ 1 1', playerId)

    def tip(self, playerId, message):
        compFactory.CreateGame(playerId).SetOneTipMessage(playerId, message)
