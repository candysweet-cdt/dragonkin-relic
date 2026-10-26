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
}

# 工具/武器：netease:weapon 的 type 选项是 sword / shovel / pickaxe / hatchet / hoe
TOOLS = {
    'dragon_fang_sword': ('龙牙剑', 'sword', 8, 1561, 15),
    'dragon_scale_pickaxe': ('龙鳞镐', 'pickaxe', 5, 1561, 10),
    'dragon_scale_axe': ('龙鳞斧', 'hatchet', 9, 1561, 10),
    'dragon_scale_shovel': ('龙鳞锹', 'shovel', 5, 1561, 10),
    'dragon_scale_hoe': ('龙鳞锄', 'hoe', 1, 1561, 10),
}

# 盔甲：armor_slot 0头 1胸 2腿 3靴；defense 取下界与钻石同档
ARMORS = {
    'dragon_scale_helmet': ('龙鳞头盔', 0, 3, 407, 'helmet', 'helmet_layer_visible', 1),
    'dragon_scale_chestplate': ('龙鳞胸甲', 1, 8, 592, 'chestplate', 'chest_layer_visible', 1),
    'dragon_scale_leggings': ('龙鳞护腿', 2, 6, 555, 'leggings', 'leg_layer_visible', 2),
    'dragon_scale_boots': ('龙鳞靴', 3, 3, 481, 'boots', 'boot_layer_visible', 1),
}


# 刷怪蛋：官方规范要求 custom_item_type=egg + netease:egg；zz_ 前缀让它在分页内排最后
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


def item_res(ident):
    return {
        'format_version': '1.10',
        'minecraft:item': {
            'description': {
                'identifier': fid(ident),
                'category': CATEGORY,
                'register_to_create_menu': True,
            },
            'components': {'minecraft:icon': fid(ident)},
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


def shapeless(ident, ingredients, count=1):
    return {
        'format_version': '1.12',
        'minecraft:recipe_shapeless': {
            'description': {'identifier': f'fycq:{ident}'},
            'tags': ['crafting_table'],
            'ingredients': [{'item': i} for i in ingredients],
            'result': [{'item': fid(ident), 'count': count}],
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
        dump(os.path.join(BP, 'netease_items_beh', ident + '.json'), item_beh(ident, comps))
        names[ident] = cn

    # 工具与武器
    for ident, (cn, wtype, dmg, dura, ench) in TOOLS.items():
        comps = {
            'minecraft:max_stack_size': 1,
            'minecraft:max_damage': dura,
            'minecraft:hand_equipped': True,
            'netease:weapon': {
                'type': wtype,
                'level': 3,
                'speed': 8,
                'attack_damage': dmg,
                'enchantment': ench,
            },
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
                'toughness': 2,
                'knockback_resistance': 0,
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

    # 刷怪蛋（右键生成实体，支持刷怪笼与发射器）
    for ident, entity in EGGS.items():
        comps = {
            'minecraft:max_stack_size': 64,
            'netease:egg': {'entity': entity},
        }
        dump(os.path.join(BP, 'netease_items_beh', ident + '.json'), item_beh(ident, comps, 'egg'))
        names[ident] = EGG_NAMES[ident]

    # 资源包物品定义
    all_ids = list(MATERIALS) + list(TOOLS) + list(ARMORS) + list(EGGS)
    for ident in all_ids:
        dump(os.path.join(RP, 'netease_items_res', ident + '.json'), item_res(ident))

    # 图集
    dump(os.path.join(RP, 'textures', 'item_texture.json'), {
        'resource_pack_name': 'fycqDrasnea',
        'texture_name': 'atlas.items',
        'texture_data': {
            fid(ident): {'textures': f'textures/items/{ident}'}
            for ident in list(MATERIALS) + list(TOOLS) + list(ARMORS) + list(EGGS)
        },
    })

    # 创造栏分页与分组：只由 gen_creative_layout.py 写，避免两处定义顺序

    # 配方
    S, F, T = fid('dragon_scale'), fid('dragon_fang'), 'minecraft:stick'
    recipes = {
        'dragon_fang_sword': shaped('dragon_fang_sword', ['F', 'F', 'T'], {'F': F, 'T': T}),
        'dragon_scale_pickaxe': shaped('dragon_scale_pickaxe', ['SSS', ' T ', ' T '], {'S': S, 'T': T}),
        'dragon_scale_axe': shaped('dragon_scale_axe', ['SS ', 'ST ', ' T '], {'S': S, 'T': T}),
        'dragon_scale_shovel': shaped('dragon_scale_shovel', ['S', 'T', 'T'], {'S': S, 'T': T}),
        'dragon_scale_hoe': shaped('dragon_scale_hoe', ['SS', ' T', ' T'], {'S': S, 'T': T}),
        'dragon_scale_helmet': shaped('dragon_scale_helmet', ['SSS', 'S S'], {'S': S}),
        'dragon_scale_chestplate': shaped('dragon_scale_chestplate', ['S S', 'SSS', 'SSS'], {'S': S}),
        'dragon_scale_leggings': shaped('dragon_scale_leggings', ['SSS', 'S S', 'S S'], {'S': S}),
        'dragon_scale_boots': shaped('dragon_scale_boots', ['S S', 'S S'], {'S': S}),
        'dragon_blood_crystal': shapeless('dragon_blood_crystal',
                                          [fid('dragon_heart'), S, S], 3),
    }
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
                        {'function': 'set_count', 'count': {'min': 4, 'max': 8}},
                        {'function': 'looting_enchant', 'count': {'min': 0, 'max': 3}},
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
                    'name': 'minecraft:dragon_egg',
                    'weight': 1,
                    'functions': [{'function': 'set_count', 'count': {'min': 1, 'max': 1}}],
                }],
                'conditions': [{'condition': 'killed_by_player'}],
            },
        ],
    })

    # lang 由 gen_lang.py 统一生成，避免多波互相覆盖

    print(f'items: {len(names)} | recipes: {len(recipes)}')


if __name__ == '__main__':
    main()
