"""波1（龙裔遗骸）JSON 生成器：物品定义、图标注册、盔甲 attachables、配方、创造栏、lang、BOSS 掉落。

只写 JSON 与 lang，不产美术（图标由 draw_wave1.py 手绘）。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ids import fid

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BP = os.path.join(ROOT, 'awesome_behavior_packs')
RP = os.path.join(ROOT, 'awesome_resource_packs')
CATEGORY = 'drasnea'

MATERIALS = {
    'dragon_scale': '龙鳞',
    'dragon_fang': '龙牙',
    'dragon_heart': '龙心',
    'dragon_blood_crystal': '龙血结晶',
    'dragon_soul': '龙魂',
}

# 工具/武器：netease:weapon 的 type 选项是 sword / shovel / pickaxe / hatchet / hoe
S_SCALE = fid('dragon_scale')
S_FANG = fid('dragon_fang')

TOOL_SPEED = 10
TOOL_DURABILITY = 2341

TOOLS = {
    'dragon_fang_sword': ('龙牙剑', 'sword', 10, TOOL_DURABILITY, 18),
    'dragon_scale_pickaxe': ('龙鳞镐', 'pickaxe', 7, TOOL_DURABILITY, 12),
    'dragon_scale_axe': ('龙鳞斧', 'hatchet', 9, TOOL_DURABILITY, 12),
    'dragon_scale_shovel': ('龙鳞锹', 'shovel', 7, TOOL_DURABILITY, 12),
    'dragon_scale_hoe': ('龙鳞锄', 'hoe', 3, TOOL_DURABILITY, 12),
}

# 觉醒档：龙牙剑 + 龙魂 + 4 龙鳞；四件甲各 +1 防御、+2 韧性、+10% 耐久
AWAKENED_TOOLS = {
    'dragon_fang_sword_awakened': ('龙牙剑·觉醒', 'sword', 13, 2800, 20),
}
AWAKENED_ARMORS = {
    'dragon_scale_helmet_awakened': ('龙鳞头盔·觉醒', 0, 4, 448, 'helmet', 'helmet_layer_visible'),
    'dragon_scale_chestplate_awakened': ('龙鳞胸甲·觉醒', 1, 9, 651, 'chestplate', 'chest_layer_visible'),
    'dragon_scale_leggings_awakened': ('龙鳞护腿·觉醒', 2, 7, 611, 'leggings', 'leg_layer_visible'),
    'dragon_scale_boots_awakened': ('龙鳞靴·觉醒', 3, 4, 529, 'boots', 'boot_layer_visible'),
}

# 盔甲：armor_slot 0头 1胸 2腿 3靴；defense 取下界与钻石同档
ARMORS = {
    'dragon_scale_helmet': ('龙鳞头盔', 0, 3, 407, 'helmet', 'helmet_layer_visible', 1),
    'dragon_scale_chestplate': ('龙鳞胸甲', 1, 8, 592, 'chestplate', 'chest_layer_visible', 1),
    'dragon_scale_leggings': ('龙鳞护腿', 2, 6, 555, 'leggings', 'leg_layer_visible', 2),
    'dragon_scale_boots': ('龙鳞靴', 3, 3, 481, 'boots', 'boot_layer_visible', 1),
}


# 刷怪蛋：官方规范要求 custom_item_type=egg + netease:egg；zz_ 前缀让它在分页内排最后
# 消耗品：龙血凝露（龙血结晶 + 玻璃瓶），饮用回血 + 抗性
CONSUMABLES = {
    'dragon_blood_dew': '龙血凝露',
}

EGG_NAMES = {
    'zz_drasnea_egg': '龙蛇刷怪蛋',
    'zz_dragon_whelp_egg': '幼龙刷怪蛋',
    'zz_dragon_priest_egg': '龙祭司刷怪蛋',
    'zz_dragon_guard_egg': '龙卫刷怪蛋',
}

EGGS = {
    'zz_drasnea_egg': 'fycq:drasnea',
    'zz_dragon_whelp_egg': 'fycq:dragon_whelp',
    'zz_dragon_priest_egg': 'fycq:dragon_priest',
    'zz_dragon_guard_egg': 'fycq:dragon_guard',
}


def dump(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, ensure_ascii=False, indent=4)
        f.write('\n')


def item_beh(ident, components, custom_type=None):
    desc = {
        'identifier': fid(ident),
        'category': CATEGORY,
        'register_to_create_menu': True,
    }
    if custom_type:
        desc['custom_item_type'] = custom_type
    return {'format_version': '1.10', 'minecraft:item': {'description': desc, 'components': components}}


def item_res(ident, extra=None):
    comps = {'minecraft:icon': fid(ident)}
    if extra:
        comps.update(extra)
    return {
        'format_version': '1.10',
        'minecraft:item': {
            'description': {
                'identifier': fid(ident),
                'category': CATEGORY,
                'register_to_create_menu': True,
            },
            'components': comps,
        },
    }


def shaped(ident, pattern, key, count=1):
    return {
        'format_version': '1.12',
        'minecraft:recipe_shaped': {
            'description': {'identifier': f'fycq:{ident}'},
            'tags': ['crafting_table'],
            'pattern': pattern,
            'key': {k: {'item': v} for k, v in key.items()},
            'result': {'item': fid(ident), 'count': count},
        },
    }


def shapeless(ident, ingredients, count=1, result=None):
    return {
        'format_version': '1.12',
        'minecraft:recipe_shapeless': {
            'description': {'identifier': f'fycq:{ident}'},
            'tags': ['crafting_table'],
            'ingredients': [{'item': i} for i in ingredients],
            'result': [{'item': result or fid(ident), 'count': count}],
        },
    }


def main():
    names = {}

    # 材料
    for ident, cn in MATERIALS.items():
        comps = {'minecraft:max_stack_size': 64}
        if ident == 'dragon_heart':
            # 不配 minecraft:foil：附魔光效会把暗红底染成品红，材料件不该发光
            comps['netease:customtips'] = {'value': '§7龙蛇的心脏，仍在跳动'}
        if ident == 'dragon_blood_crystal':
            # 让稀有掉落有实际去处：可在附魔台当材料（原版青金石位）
            comps['netease:enchant_material'] = {'value': True}
            comps['netease:customtips'] = {'value': '§7可作附魔材料'}
        if ident == 'dragon_soul':
            comps['netease:customtips'] = {'value': '§7龙蛇之魂，可将龙裔装备觉醒'}
        dump(os.path.join(BP, 'netease_items_beh', ident + '.json'), item_beh(ident, comps))
        names[ident] = cn

    # 工具与武器
    for ident, (cn, wtype, dmg, dura, ench) in TOOLS.items():
        comps = {
            'minecraft:max_stack_size': 1,
            'minecraft:max_damage': dura,
            'minecraft:hand_equipped': True,
            # 修复：铁砧只认 netease:weapon.level 决定的材料（level 3 = 钻石，实测
            # minecraft:repairable 不生效）；龙鳞路线靠重铸配方 repair_<id>
            'netease:weapon': {
                'type': wtype,
                'level': 3,
                'speed': TOOL_SPEED,
                'attack_damage': dmg,
                'enchantment': ench,
            },
        }
        if wtype == 'sword':
            comps['netease:customtips'] = {'value': '§7右键释放龙息斩（12 秒冷却）'}
        dump(os.path.join(BP, 'netease_items_beh', ident + '.json'), item_beh(ident, comps, 'weapon'))
        names[ident] = cn

    # 觉醒武器
    for ident, (cn, wtype, dmg, dura, ench) in AWAKENED_TOOLS.items():
        comps = {
            'minecraft:max_stack_size': 1,
            'minecraft:max_damage': dura,
            'minecraft:hand_equipped': True,
            'netease:weapon': {
                'type': wtype,
                'level': 3,
                'speed': TOOL_SPEED,
                'attack_damage': dmg,
                'enchantment': ench,
            },
            'netease:customtips': {'value': '§7右键释放更强的龙息斩（12 秒冷却）'},
        }
        dump(os.path.join(BP, 'netease_items_beh', ident + '.json'), item_beh(ident, comps, 'weapon'))
        names[ident] = cn

    # 盔甲
    for ident, (cn, slot, defense, dura, geo, var, layer) in ARMORS.items():
        comps = {
            'minecraft:max_stack_size': 1,
            'minecraft:max_damage': dura,
            'netease:armor': {
                'defense': defense,
                'enchantment': 15,
                'armor_slot': slot,
                'toughness': 6,            # 高伤害时减伤不被穿透（体感：越打越抗）
                'knockback_resistance': 0.6,  # 站桩不被打飞
            },
        }
        dump(os.path.join(BP, 'netease_items_beh', ident + '.json'), item_beh(ident, comps, 'armor'))
        names[ident] = cn
        dump(os.path.join(RP, 'attachables', ident + '.json'), {
            'format_version': '1.8.0',
            'minecraft:attachable': {
                'description': {
                    'identifier': fid(ident),
                    'materials': {'default': 'armor', 'enchanted': 'armor_enchanted'},
                    'textures': {
                        'default': f'textures/models/armor/dragon_scale_{layer}',
                        'enchanted': 'textures/misc/enchanted_item_glint',
                    },
                    'geometry': {'default': f'geometry.humanoid.armor.{geo}'},
                    'scripts': {'parent_setup': f'variable.{var} = 0.0;'},
                    'render_controllers': ['controller.render.armor'],
                },
            },
        })

    # 觉醒盔甲（甲片用 *_awakened_1/2）
    for ident, (cn, slot, defense, dura, geo, var) in AWAKENED_ARMORS.items():
        comps = {
            'minecraft:max_stack_size': 1,
            'minecraft:max_damage': dura,
            'netease:armor': {
                'defense': defense,
                'enchantment': 18,
                'armor_slot': slot,
                'toughness': 8,
                'knockback_resistance': 0.7,
            },
        }
        dump(os.path.join(BP, 'netease_items_beh', ident + '.json'), item_beh(ident, comps, 'armor'))
        names[ident] = cn
        layer = 2 if slot == 2 else 1
        dump(os.path.join(RP, 'attachables', ident + '.json'), {
            'format_version': '1.8.0',
            'minecraft:attachable': {
                'description': {
                    'identifier': fid(ident),
                    'materials': {'default': 'armor', 'enchanted': 'armor_enchanted'},
                    'textures': {
                        'default': f'textures/models/armor/dragon_scale_awakened_{layer}',
                        'enchanted': 'textures/misc/enchanted_item_glint',
                    },
                    'geometry': {'default': f'geometry.humanoid.armor.{geo}'},
                    'scripts': {'parent_setup': f'variable.{var} = 0.0;'},
                    'render_controllers': ['controller.render.armor'],
                },
            },
        })

    # 刷怪蛋（右键生成实体，支持刷怪笼与发射器）
    for ident, entity in EGGS.items():
        comps = {
            'minecraft:max_stack_size': 64,
            'netease:egg': {'entity': entity},
        }
        dump(os.path.join(BP, 'netease_items_beh', ident + '.json'), item_beh(ident, comps, 'egg'))
        names[ident] = EGG_NAMES[ident]

    # 消耗品（可饮用）
    for ident, cn in CONSUMABLES.items():
        comps = {
            'minecraft:max_stack_size': 1,
            'minecraft:use_duration': 32,
            'minecraft:food': {
                'nutrition': 0,
                'saturation_modifier': 'poor',
                'using_converts_to': 'minecraft:glass_bottle',
                'effects': [
                    {'name': 'regeneration', 'chance': 1.0, 'duration': 12, 'amplifier': 1},
                    {'name': 'absorption', 'chance': 1.0, 'duration': 90, 'amplifier': 0},
                    {'name': 'fire_resistance', 'chance': 1.0, 'duration': 60, 'amplifier': 0},
                    {'name': 'resistance', 'chance': 1.0, 'duration': 10, 'amplifier': 0},
                ],
            },
            'netease:customtips': {'value': '§7饮下：回复生命并获得抗性'},
        }
        dump(os.path.join(BP, 'netease_items_beh', ident + '.json'), item_beh(ident, comps))
        names[ident] = cn

    # 资源包物品定义
    all_ids = (list(MATERIALS) + list(TOOLS) + list(AWAKENED_TOOLS) + list(ARMORS)
               + list(AWAKENED_ARMORS) + list(EGGS) + list(CONSUMABLES))
    for ident in all_ids:
        extra = {'minecraft:use_animation': 'drink'} if ident in CONSUMABLES else None
        dump(os.path.join(RP, 'netease_items_res', ident + '.json'), item_res(ident, extra))

    # 图集
    dump(os.path.join(RP, 'textures', 'item_texture.json'), {
        'resource_pack_name': 'fycqDrasnea',
        'texture_name': 'atlas.items',
        'texture_data': {
            fid(ident): {'textures': f'textures/items/{ident}'}
            for ident in all_ids
        },
    })

    # 创造栏分页与分组：只由 gen_creative_layout.py 写，避免两处定义顺序

    # 配方
    S, F, T = fid('dragon_scale'), fid('dragon_fang'), 'minecraft:stick'
    recipes = {
        # 牙=刃材、鳞=结构材：剑是纯刃（2 牙），工具头是「鳞 + 牙」
        'dragon_fang_sword': shaped('dragon_fang_sword', ['F', 'F', 'T'], {'F': F, 'T': T}),
        'dragon_scale_pickaxe': shaped('dragon_scale_pickaxe', ['SFS', ' T ', ' T '],
                                       {'S': S, 'F': F, 'T': T}),
        'dragon_scale_axe': shaped('dragon_scale_axe', ['SF ', 'ST ', ' T '],
                                   {'S': S, 'F': F, 'T': T}),
        'dragon_scale_shovel': shaped('dragon_scale_shovel', ['S', 'F', 'T'],
                                      {'S': S, 'F': F, 'T': T}),
        'dragon_scale_hoe': shaped('dragon_scale_hoe', ['SF', ' T', ' T'],
                                   {'S': S, 'F': F, 'T': T}),
        'dragon_scale_helmet': shaped('dragon_scale_helmet', ['SSS', 'S S'], {'S': S}),
        'dragon_scale_chestplate': shaped('dragon_scale_chestplate', ['S S', 'SSS', 'SSS'], {'S': S}),
        'dragon_scale_leggings': shaped('dragon_scale_leggings', ['SSS', 'S S', 'S S'], {'S': S}),
        'dragon_scale_boots': shaped('dragon_scale_boots', ['S S', 'S S'], {'S': S}),
        'dragon_blood_crystal': shapeless('dragon_blood_crystal',
                                          [fid('dragon_heart'), S, S], 3),
        'dragon_blood_dew': shapeless('dragon_blood_dew',
                                      [fid('dragon_blood_crystal'), 'minecraft:glass_bottle'], 1),
    }
    # 觉醒：原装备 + 1 龙魂 + 龙鳞
    recipes['upgrade_dragon_fang_sword'] = shapeless(
        'upgrade_dragon_fang_sword',
        [fid('dragon_fang_sword'), fid('dragon_soul'), S, S, S, S], 1,
        result=fid('dragon_fang_sword_awakened'))
    for stem in AWAKENED_ARMORS:
        base = stem[:-len('_awakened')]
        recipes['upgrade_' + stem] = shapeless(
            'upgrade_' + stem, [fid(base), fid('dragon_soul'), S, S], 1, result=fid(stem))
    # 重铸（铁砧修复若不生效时的保底）：同一件 + 2 龙鳞 → 全新一件
    for stem in (list(TOOLS) + list(AWAKENED_TOOLS) + list(ARMORS) + list(AWAKENED_ARMORS)):
        recipes['repair_' + stem] = shapeless('repair_' + stem, [fid(stem), S_SCALE, S_SCALE],
                                                1, result=fid(stem))
    for ident, body in recipes.items():
        dump(os.path.join(BP, 'netease_recipes', ident + '.json'), body)

    # BOSS 掉落：改掉专属材料
    dump(os.path.join(BP, 'loot_tables', 'fycq', 'drasnea.json'), {
        'pools': [
            {
                'rolls': 1,
                'entries': [{
                    'type': 'item',
                    'name': fid('dragon_scale'),
                    'weight': 1,
                    'functions': [
                        {'function': 'set_count', 'count': {'min': 6, 'max': 10}},
                        {'function': 'looting_enchant', 'count': {'min': 0, 'max': 4}},
                    ],
                }],
            },
            {
                'rolls': 1,
                'entries': [{
                    'type': 'item',
                    'name': fid('dragon_fang'),
                    'weight': 1,
                    'functions': [
                        {'function': 'set_count', 'count': {'min': 2, 'max': 4}},
                        {'function': 'looting_enchant', 'count': {'min': 0, 'max': 2}},
                    ],
                }],
            },
            {
                'rolls': 1,
                'entries': [{
                    'type': 'item',
                    'name': fid('dragon_heart'),
                    'weight': 1,
                    'functions': [{'function': 'set_count', 'count': {'min': 1, 'max': 1}}],
                }],
                'conditions': [{'condition': 'killed_by_player'}],
            },
            {
                'rolls': 1,
                'entries': [{
                    'type': 'item',
                    'name': fid('dragon_soul'),
                    'weight': 1,
                    'functions': [{'function': 'set_count', 'count': {'min': 1, 'max': 1}}],
                }],
                'conditions': [{'condition': 'killed_by_player'}],
            },
            {
                'rolls': 1,
                'entries': [{
                    'type': 'item',
                    'name': 'minecraft:dragon_egg',
                    'weight': 1,
                    'functions': [{'function': 'set_count', 'count': {'min': 1, 'max': 1}}],
                }],
                'conditions': [{'condition': 'killed_by_player'}],
            },
            {
                'conditions': [{'condition': 'killed_by_player'},
                               {'condition': 'random_chance_with_looting', 'chance': 0.35,
                                'looting_multiplier': 0.02}],
                'rolls': 1,
                'entries': [{'type': 'item', 'name': fid('dragon_blood_crystal'), 'weight': 1,
                             'functions': [{'function': 'set_count',
                                            'count': {'min': 1, 'max': 2}}]}],
            },
        ],
    })

    # lang 由 gen_lang.py 统一生成，避免多波互相覆盖

    print(f'items: {len(names)} | recipes: {len(recipes)}')


if __name__ == '__main__':
    main()
