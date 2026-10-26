"""identifier 唯一真源：语义名 → identifier（不含命名空间）。

2026-10-26 现状：**语义名原样用作 identifier**（不加序号）。
之前试过 `dragon_10_scale` 这种序号前缀来在平铺页里定序，作者认为
「ID 全被污染了」，已撤回。序号方案保留在下面 NUMBERED 里，要启用就把
NUMBERED 赋给 IDS。

顺序实验：分页 sort_by_identifier 关掉（见 gen_creative_layout.py），
试引擎默认的注册序到底长什么样——官方从未承诺 false 时的排序规则。
"""

# 语义名 -> identifier。当前为恒等映射（ID 干净，顺序不可控）。
IDS = {
    'dragon_scale': 'dragon_scale',
    'dragon_fang': 'dragon_fang',
    'dragon_heart': 'dragon_heart',
    'dragon_blood_crystal': 'dragon_blood_crystal',
    'dragon_fang_sword': 'dragon_fang_sword',
    'dragon_scale_pickaxe': 'dragon_scale_pickaxe',
    'dragon_scale_axe': 'dragon_scale_axe',
    'dragon_scale_shovel': 'dragon_scale_shovel',
    'dragon_scale_hoe': 'dragon_scale_hoe',
    'dragon_scale_helmet': 'dragon_scale_helmet',
    'dragon_scale_chestplate': 'dragon_scale_chestplate',
    'dragon_scale_leggings': 'dragon_scale_leggings',
    'dragon_scale_boots': 'dragon_scale_boots',
    'dragon_soul': 'dragon_soul',
    'dragon_fang_sword_awakened': 'dragon_fang_sword_awakened',
    'dragon_scale_helmet_awakened': 'dragon_scale_helmet_awakened',
    'dragon_scale_chestplate_awakened': 'dragon_scale_chestplate_awakened',
    'dragon_scale_leggings_awakened': 'dragon_scale_leggings_awakened',
    'dragon_scale_boots_awakened': 'dragon_scale_boots_awakened',
    'dragon_scale_block': 'dragon_scale_block',
    'dragon_scale_bricks': 'dragon_scale_bricks',
    'dragon_scale_pillar': 'dragon_scale_pillar',
    'dragon_bone_block': 'dragon_bone_block',
    'dragon_crystal_block': 'dragon_crystal_block',
    'dragon_crystal_lamp': 'dragon_crystal_lamp',
    'dragon_nest': 'dragon_nest',
    'dragon_blood_dew': 'dragon_blood_dew',
    'zz_drasnea_egg': 'zz_drasnea_egg',
    'zz_dragon_whelp_egg': 'zz_dragon_whelp_egg',
    'zz_dragon_priest_egg': 'zz_dragon_priest_egg',
    'zz_dragon_guard_egg': 'zz_dragon_guard_egg',
}

# 备用：序号方案（平铺页顺序可控，但 ID 带编号）
NUMBERED = {
    'dragon_scale': 'dragon_10_scale',
    'dragon_fang': 'dragon_11_fang',
    'dragon_heart': 'dragon_12_heart',
    'dragon_blood_crystal': 'dragon_13_blood_crystal',
    'dragon_fang_sword': 'dragon_20_fang_sword',
    'dragon_scale_pickaxe': 'dragon_21_scale_pickaxe',
    'dragon_scale_axe': 'dragon_22_scale_axe',
    'dragon_scale_shovel': 'dragon_23_scale_shovel',
    'dragon_scale_hoe': 'dragon_24_scale_hoe',
    'dragon_scale_helmet': 'dragon_30_scale_helmet',
    'dragon_scale_chestplate': 'dragon_31_scale_chestplate',
    'dragon_scale_leggings': 'dragon_32_scale_leggings',
    'dragon_scale_boots': 'dragon_33_scale_boots',
    'dragon_scale_block': 'dragon_40_scale_block',
    'dragon_scale_bricks': 'dragon_41_scale_bricks',
    'dragon_scale_pillar': 'dragon_42_scale_pillar',
    'dragon_bone_block': 'dragon_43_bone_block',
    'dragon_crystal_block': 'dragon_44_crystal_block',
    'dragon_crystal_lamp': 'dragon_45_crystal_lamp',
    'dragon_nest': 'dragon_46_nest',
    'dragon_blood_dew': 'dragon_blood_dew',
    'zz_drasnea_egg': 'zz_drasnea_egg',
    'zz_dragon_whelp_egg': 'zz_dragon_whelp_egg',
    'zz_dragon_priest_egg': 'zz_dragon_priest_egg',
    'zz_dragon_guard_egg': 'zz_dragon_guard_egg',
}

NAMESPACE = 'fycq'


def pid(stem):
    """语义名 -> identifier（不含命名空间）。"""
    return IDS[stem]


def fid(stem):
    """语义名 -> 完整 identifier。"""
    return f'{NAMESPACE}:{IDS[stem]}'
