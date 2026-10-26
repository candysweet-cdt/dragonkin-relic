# -*- coding: utf-8 -*-
"""A 批美术：龙魂图标 + 龙牙剑/四件甲的觉醒图标与甲片。

觉醒件以原图标/原甲片为底，只做「金边 + 金/紫魂点」：保持原剪影与明度，
不重画；龙魂是新画的紫色魂珠（金环 + 青芯）。
"""
import os

from PIL import Image

from palette import OUTLINE, GOLD, METAL, ROBE, ramp

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
RP = os.path.join(ROOT, 'awesome_resource_packs')
ITEMS = os.path.join(RP, 'textures', 'items')
ARMOR = os.path.join(RP, 'textures', 'models', 'armor')
PREVIEW = os.path.join(os.path.dirname(__file__), 'preview')

SOUL_MAP = [
    '................',
    '................',
    '.......##.......',
    '......#ww#......',
    '.....#wWWw#.....',
    '....#wWHHWw#....',
    '...#wWHHHHWw#...',
    '...#wWHHHHWw#...',
    '...#wWWHHWWw#...',
    '....#wWWWWw#....',
    '.....#wWWw#.....',
    '......#ww#......',
    '.....##gg##.....',
    '....#gGGGGg#....',
    '.....#gggg#.....',
    '......####......',
]
SOUL_COLORS = {
    '#': OUTLINE,
    'w': ramp(ROBE, 0.35),
    'W': ramp(ROBE, 0.65),
    'H': ramp(METAL, 0.85),
    'g': ramp(GOLD, 0.30),
    'G': ramp(GOLD, 0.75),
}

FILES = ['dragon_fang_sword', 'dragon_scale_helmet', 'dragon_scale_chestplate',
         'dragon_scale_leggings', 'dragon_scale_boots']


def soul_icon():
    im = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    px = im.load()
    for y, row in enumerate(SOUL_MAP):
        for x, ch in enumerate(row):
            if ch in SOUL_COLORS:
                px[x, y] = SOUL_COLORS[ch]
    im.save(os.path.join(ITEMS, 'dragon_soul.png'))


def blend(a, b, t):
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3)) + (a[3],)


def awaken_icon(src, dst, gem=True):
    im = Image.open(src).convert('RGBA')
    px = im.load()
    # 金边：不透明且四邻有透明的像素，往金色靠 60%
    gold = ramp(GOLD, 0.55)
    edge = []
    for y in range(16):
        for x in range(16):
            if px[x, y][3] == 0:
                continue
            nb = [(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)]
            if any(0 <= nx < 16 and 0 <= ny < 16 and px[nx, ny][3] == 0 for nx, ny in nb):
                edge.append((x, y))
    for x, y in edge:
        px[x, y] = blend(px[x, y], gold, 0.60)
    # 魂点：顶部 2 px 紫、中心 2 px 亮金
    opaque = [(x, y) for y in range(16) for x in range(16) if px[x, y][3] > 0]
    if opaque:
        top = min(opaque, key=lambda p: (p[1], p[0]))
        for dx, dy, color in ((0, 0, ramp(ROBE, 0.9)), (1, 0, ramp(ROBE, 0.7))):
            x, y = top[0] + dx, top[1] + dy
            if 0 <= x < 16 and 0 <= y < 16 and px[x, y][3] > 0:
                px[x, y] = color
        if gem:
            cx = sum(p[0] for p in opaque) // len(opaque)
            cy = sum(p[1] for p in opaque) // len(opaque)
            for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
                x, y = cx + dx, cy + dy
                if 0 <= x < 16 and 0 <= y < 16 and px[x, y][3] > 0:
                    px[x, y] = ramp(GOLD, 0.9)
    im.save(dst)


def awaken_layer(src, dst, chest=False):
    im = Image.open(src).convert('RGBA')
    px = im.load()
    w, h = im.size
    gold = ramp(GOLD, 0.55)
    for y in range(h):
        for x in range(w):
            if px[x, y][3] == 0:
                continue
            nb = [(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)]
            if any(0 <= nx < w and 0 <= ny < h and px[nx, ny][3] == 0 for nx, ny in nb):
                px[x, y] = blend(px[x, y], gold, 0.55)
    if chest:
        # 胸甲正中一条 2px 金带 + 亮金扣
        for y in (23, 24):
            for x in range(20, 36):
                if px[x, y][3] > 0:
                    px[x, y] = ramp(GOLD, 0.7 if y == 23 else 0.45)
        for y in (22, 25):
            for x in (27, 28):
                if px[x, y][3] > 0:
                    px[x, y] = ramp(GOLD, 0.95)
    im.save(dst)


def main():
    soul_icon()
    for stem in FILES:
        awaken_icon(os.path.join(ITEMS, stem + '.png'),
                     os.path.join(ITEMS, stem + '_awakened.png'),
                     gem=stem.startswith('dragon_scale_'))
        print('icon', stem + '_awakened')
    awaken_layer(os.path.join(ARMOR, 'dragon_scale_1.png'),
                 os.path.join(ARMOR, 'dragon_scale_awakened_1.png'), chest=True)
    awaken_layer(os.path.join(ARMOR, 'dragon_scale_2.png'),
                 os.path.join(ARMOR, 'dragon_scale_awakened_2.png'))
    print('armor layers: 2')

    # 预览：图标 8x，甲片 4x
    icons = [Image.open(os.path.join(ITEMS, n + '.png')).convert('RGBA')
             for n in ['dragon_soul'] + [f + '_awakened' for f in FILES]]
    sheet = Image.new('RGBA', (16 * 8 * len(icons), 16 * 8), (20, 16, 14, 255))
    for i, im in enumerate(icons):
        sheet.alpha_composite(im.resize((128, 128), Image.NEAREST), (i * 128, 0))
    os.makedirs(PREVIEW, exist_ok=True)
    sheet.save(os.path.join(PREVIEW, 'wave4_icons_8x.png'))

    layers = [Image.open(os.path.join(ARMOR, n + '.png')).convert('RGBA')
              for n in ('dragon_scale_awakened_1', 'dragon_scale_awakened_2')]
    ls = Image.new('RGBA', (64 * 4 * 2, 32 * 4), (20, 16, 14, 255))
    for i, im in enumerate(layers):
        ls.alpha_composite(im.resize((256, 128), Image.NEAREST), (i * 256, 0))
    ls.save(os.path.join(PREVIEW, 'wave4_armor_4x.png'))
    print('preview saved')


if __name__ == '__main__':
    main()
