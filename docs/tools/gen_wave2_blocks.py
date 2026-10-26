"""波2（龙祭坛）JSON：7 个方块定义、掉落、配方、资源包注册。"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ids import fid

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BP = os.path.join(ROOT, 'awesome_behavior_packs')
RP = os.path.join(ROOT, 'awesome_resource_packs')
CATEGORY = 'drasnea'

# id: (destroy_time, explosion, tier(level|None), light, map_color, sound, textures)
BLOCKS = {
    'dragon_scale_block': (4.0, 6, 2, 0, '#2E8B7E', 'metal', 'dragon_scale_block'),
    'dragon_bone_block': (3.0, 6, 2, 0, '#C9BE9E', 'stone', 'dragon_bone_block'),
    'dragon_crystal_block': (5.0, 9, 2, 0, '#B3202F', 'stone', 'dragon_crystal_block'),
    'dragon_crystal_lamp': (3.0, 6, 2, 1, '#E0555F', 'stone', 'dragon_crystal_lamp'),
    'dragon_scale_bricks': (4.0, 6, 2, 0, '#2E8B7E', 'metal', 'dragon_scale_bricks'),
    'dragon_scale_pillar': (4.0, 6, 2, 0, '#2E8B7E', 'metal',
                            {'up': 'dragon_scale_pillar_top', 'down': 'dragon_scale_pillar_top',
                             'side': 'dragon_scale_pillar_side'}),
    'dragon_nest': (2.0, 3, None, 0, '#3D2A1B', 'grass', 'dragon_nest'),
}


def dump(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, ensure_ascii=False, indent=4)
        f.write('\n')


def shaped(rid, pattern, key, result, count=1):
    return {
        'format_version': '1.12',
        'minecraft:recipe_shaped': {
            'description': {'identifier': f'fycq:{rid}'},
            'tags': ['crafting_table'],
            'pattern': pattern,
            'key': {k: {'item': v} for k, v in key.items()},
            'result': {'item': result, 'count': count},
        },
    }


def shapeless(rid, ingredients, result, count=1):
    return {
        'format_version': '1.12',
        'minecraft:recipe_shapeless': {
            'description': {'identifier': f'fycq:{rid}'},
            'tags': ['crafting_table'],
            'ingredients': [{'item': i} for i in ingredients],
            'result': [{'item': result, 'count': count}],
        },
    }


def main():
    blocks_json = {'format_version': [1, 12, 0]}
    terrain = {}
    for ident, (dt, er, tier, light, color, sound, tex) in BLOCKS.items():
        comps = {
            'minecraft:destroy_time': {'value': dt},
            'minecraft:explosion_resistance': {'value': er},
            'minecraft:loot': {'table': f'loot_tables/blocks/{ident}.json'},
            'minecraft:map_color': {'color': color},
        }
        if tier is not None:
            comps['netease:tier'] = {'digger': 'pickaxe', 'destroy_special': True, 'level': tier}
        if light:
            # emission 是 0~1 的浮点（引擎会按 1.19.10 升级），1 = 满亮度；写 15 会让整个方块定义升级失败
            comps['minecraft:block_light_absorption'] = {'value': 0}
            comps['minecraft:block_light_emission'] = {'emission': light}
        dump(os.path.join(BP, 'netease_blocks', ident + '.json'), {
            'format_version': '1.10.0',
            'minecraft:block': {
                'description': {'identifier': fid(ident), 'category': CATEGORY},
                'components': comps,
            },
        })
        dump(os.path.join(BP, 'loot_tables', 'blocks', ident + '.json'), {
            'pools': [{
                'rolls': 1,
                'entries': [{'type': 'item', 'name': fid(ident), 'weight': 1}],
            }],
        })
        blocks_json[fid(ident)] = {'textures': tex, 'sound': sound}
        if isinstance(tex, dict):
            for face_tex in set(tex.values()):
                terrain[face_tex] = {'textures': [f'textures/blocks/{face_tex}']}
        else:
            terrain[tex] = {'textures': [f'textures/blocks/{tex}']}

    dump(os.path.join(RP, 'blocks.json'), blocks_json)
    dump(os.path.join(RP, 'textures', 'terrain_texture.json'), {
        'resource_pack_name': 'fycqDrasnea',
        'texture_name': 'atlas.terrain',
        'padding': 8,
        'num_mip_levels': 4,
        'texture_data': terrain,
    })

    S = fid('dragon_scale')
    F = fid('dragon_fang')
    C = fid('dragon_blood_crystal')
    G = 'minecraft:gold_ingot'
    T = 'minecraft:stick'
    recipes = {
        'dragon_scale_block': shaped('dragon_scale_block', ['SSS', 'SSS', 'SSS'], {'S': S},
                                     fid('dragon_scale_block')),
        'dragon_scale_block_uncraft': shapeless('dragon_scale_block_uncraft', [fid('dragon_scale_block')], S, 9),
        'dragon_bone_block': shaped('dragon_bone_block', ['FFF', 'FFF', 'FFF'], {'F': F},
                                    fid('dragon_bone_block')),
        'dragon_bone_block_uncraft': shapeless('dragon_bone_block_uncraft', [fid('dragon_bone_block')], F, 9),
        'dragon_crystal_block': shaped('dragon_crystal_block', ['CC', 'CC'], {'C': C},
                                       fid('dragon_crystal_block')),
        'dragon_crystal_block_uncraft': shapeless('dragon_crystal_block_uncraft',
                                                  [fid('dragon_crystal_block')], C, 4),
        'dragon_crystal_lamp': shaped('dragon_crystal_lamp', [' G ', 'GCG', ' G '],
                                      {'G': G, 'C': fid('dragon_crystal_block')}, fid('dragon_crystal_lamp')),
        'dragon_scale_bricks': shaped('dragon_scale_bricks', ['SS', 'SS'],
                                      {'S': fid('dragon_scale_block')}, fid('dragon_scale_bricks'), 4),
        'dragon_scale_pillar': shaped('dragon_scale_pillar', ['S', 'S'],
                                      {'S': fid('dragon_scale_block')}, fid('dragon_scale_pillar'), 2),
        'dragon_nest': shapeless('dragon_nest', [S, S, T, T], fid('dragon_nest')),
    }
    for rid, body in recipes.items():
        dump(os.path.join(BP, 'netease_recipes', rid + '.json'), body)

    print(f'blocks: {len(BLOCKS)} | recipes: {len(recipes)} | terrain tiles: {len(terrain)}')


if __name__ == '__main__':
    main()
