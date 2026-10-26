"""创造栏布局唯一真源：分页（netease_tab）+ 分组（netease_group）。

2026-10-26 实测过的三条路，最后选分组：
  · sort_by_identifier=false + 平铺  → 方块段哈希序、物品段字典序，不可控
  · 序号 identifier + 平铺          → 可控但 ID 被编号污染（作者否掉）
  · 分组 + sort_by_identifier=false → 组间顺序也是哈希序，不可控

可用的机制（官方《13-自定义物品分页》《12-自定义物品分组》）：
  sort_by_identifier: true 时，**分组之间按每组 list 首件的 identifier 字典序排**，
  **组内按 list 数组序排**。所以只要挑好每组的首件，组间与组内顺序都可控，
  identifier 保持语义名。

官方硬约束：分组 list 少于 2 件注册失败；一件物品只能进一个分组；
分组 icon 必须是本组内的 identifier。

2026-10-26 作者定稿：**只有武器与盔甲成组**（这两类组内顺序有语义、需要固定），
材料 4 件与方块 7 件留在组外按 identifier 排，刷怪蛋同样在组外靠 zz_ 排最后。
未分组的件与「每组首件」混在一起排序（官方《13-自定义物品分页》第三条规则）。

GROUPS 里每组的 list[0] 就是该组的排序键，改动会破坏组间顺序——
check_pack.py 的 check_tab 会断言「按首件排序后仍等于本数组顺序」。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ids import fid

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BP = os.path.join(ROOT, 'awesome_behavior_packs')
CATEGORY = 'drasnea'
TAB_ICON = 'textures/items/dragon_scale'

# 只给武器/盔甲成组（组内顺序有意义且需要固定）；材料与方块留在组外按 identifier 排。
# 每组首件（= 排序键）必须升序：dragon_fang_sword < dragon_scale_helmet
GROUPS = [
    {
        'name': 'drasnea_tool',
        'label': '龙裔工具',
        'icon': 'dragon_fang_sword',
        'list': ['dragon_fang_sword', 'dragon_scale_pickaxe', 'dragon_scale_axe',
                 'dragon_scale_shovel', 'dragon_scale_hoe'],
    },
    {
        'name': 'drasnea_armor',
        'label': '龙裔盔甲',
        'icon': 'dragon_scale_helmet',
        'list': ['dragon_scale_helmet', 'dragon_scale_chestplate',
                 'dragon_scale_leggings', 'dragon_scale_boots'],
    },
]

MATERIALS = ['dragon_scale', 'dragon_fang', 'dragon_heart', 'dragon_blood_crystal']
BLOCKS = ['dragon_scale_block', 'dragon_scale_bricks', 'dragon_scale_pillar',
          'dragon_bone_block', 'dragon_crystal_block', 'dragon_crystal_lamp', 'dragon_nest']

# 不入组的件：与「每组首件」一起按 identifier 混排（官方《13-自定义物品分页》第三条规则）
UNGROUPED = MATERIALS + BLOCKS + ['dragon_blood_dew', 'zz_drasnea_egg', 'zz_dragon_whelp_egg',
               'zz_dragon_priest_egg', 'zz_dragon_guard_egg']


def dump(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, ensure_ascii=False, indent=4)
        f.write('\n')


def labels():
    return {f'itemGroup.name.{g["name"]}': g['label'] for g in GROUPS}


def main():
    dump(os.path.join(BP, 'netease_tab', CATEGORY + '.json'), {
        'category': [{
            'name': CATEGORY,
            'labelText': f'itemCategory.name.{CATEGORY}',
            'icon': TAB_ICON,
            'sort_by_identifier': True,
        }],
    })
    dump(os.path.join(BP, 'netease_group', 'drasnea.json'), {
        'groups': [{
            'group_name': f'itemGroup.name.{g["name"]}',
            'icon': fid(g['icon']),
            'list': [fid(stem) for stem in g['list']],
        } for g in GROUPS],
    })
    keys = [fid(g['list'][0]) for g in GROUPS]
    assert keys == sorted(keys), f'组间顺序会乱：首件排序键不是升序 {keys}'
    print(f'tab: {CATEGORY} | 分组 {len(GROUPS)} 组 + 未分组 {len(UNGROUPED)} 件 | 组间排序键 {keys}')


if __name__ == '__main__':
    main()
