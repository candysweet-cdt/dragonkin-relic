"""统一生成 zh_CN.lang（物品 / 方块 / 实体 / 创造栏名）。

所有中文名只在这里维护，避免多波生成器互相覆盖。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ids import fid
from gen_creative_layout import labels as group_labels

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
RP = os.path.join(ROOT, 'awesome_resource_packs')

CATEGORY = 'drasnea'

ITEMS = {
    'dragon_scale': '龙鳞',
    'dragon_fang': '龙牙',
    'dragon_heart': '龙心',
    'dragon_blood_crystal': '龙血结晶',
    'dragon_fang_sword': '龙牙剑',
    'dragon_scale_pickaxe': '龙鳞镐',
    'dragon_scale_axe': '龙鳞斧',
    'dragon_scale_shovel': '龙鳞锹',
    'dragon_scale_hoe': '龙鳞锄',
    'dragon_scale_helmet': '龙鳞头盔',
    'dragon_scale_chestplate': '龙鳞胸甲',
    'dragon_scale_leggings': '龙鳞护腿',
    'dragon_scale_boots': '龙鳞靴',
    'zz_drasnea_egg': '龙蛇刷怪蛋',
    'zz_dragon_whelp_egg': '幼龙刷怪蛋',
    'zz_dragon_priest_egg': '龙祭司刷怪蛋',
    'zz_dragon_guard_egg': '龙卫刷怪蛋',
}

BLOCKS = {
    'dragon_scale_block': '龙鳞块',
    'dragon_bone_block': '龙骨块',
    'dragon_crystal_block': '龙晶块',
    'dragon_crystal_lamp': '龙晶灯',
    'dragon_scale_bricks': '龙鳞砖',
    'dragon_scale_pillar': '龙鳞柱',
    'dragon_nest': '龙巢',
}

ENTITIES = {
    'drasnea': '龙蛇',
    'dragon_whelp': '幼龙',
    'dragon_priest': '龙祭司',
    'dragon_guard': '龙卫',
}


def main():
    lines = [f'itemCategory.name.{CATEGORY}=龙裔遗骸']
    for ident, cn in ENTITIES.items():
        lines.append(f'entity.fycq:{ident}.name={cn}')
        lines.append(f'item.spawn_egg.entity.fycq:{ident}.name={cn}刷怪蛋')
    for ident, cn in ITEMS.items():
        lines.append(f'item.{fid(ident)}.name={cn}')
    for ident, cn in BLOCKS.items():
        lines.append(f'tile.{fid(ident)}.name={cn}')
    for key, cn in group_labels().items():
        lines.append(f'{key}={cn}')
    path = os.path.join(RP, 'texts', 'zh_CN.lang')
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print(f'lang lines: {len(lines)}')


if __name__ == '__main__':
    main()
