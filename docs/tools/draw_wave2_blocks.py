"""波2（龙祭坛）方块贴图：8 张 16x16。

每张先给「色调场」（0~1 的浮点 + 材料），再统一过一遍左上倒角光照
（与左上邻居比较，环绕取样保证平铺无缝），避免平涂色块感。
逐块手写色调场；输出 2x2 平铺预览检查接缝。
"""
import os
from PIL import Image

from palette import METAL, GOLD, BONE, BLOOD, WOOD, RAMPS, ramp

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'awesome_resource_packs', 'textures', 'blocks')
PREVIEW = os.path.join(os.path.dirname(__file__), 'preview')


def tone_scale_block(x, y):
    row = y // 4
    sx = (x + (row % 2) * 4) % 8
    sy = y % 4
    if sy == 0 or sx in (0, 7):
        return 0.10, 'metal'
    t = 0.74 - 0.40 * abs(sx - 3.5) / 4.0 - 0.12 * sy
    if (x * 3 + y * 5) % 29 == 0:
        return 0.90, 'gold'
    return t, 'metal'


def tone_bone_block(x, y):
    # 骨段堆叠：以竖向骨纹为主，不用砖缝网格（砖缝是它读成砂岩砖的根因）
    stripe = (x + (y // 4) * 2) % 8
    if stripe == 0:
        return 0.20, 'bone'
    if (x * 3 + y * 7) % 16 == 0 and y % 4 == 1:
        return 0.90, 'bone'
    return 0.60 + 0.22 * (1 - stripe / 8.0) + 0.06 * ((y * 3 + x * 5) % 16) / 15.0, 'bone'


def tone_crystal_block(x, y):
    cx, cy = x // 5, y // 5
    if x % 5 == 0 or (y + cx * 2) % 5 == 0:
        return 0.07, 'blood'
    if x % 5 == 1 and y % 5 == 1:
        return 0.66, 'blood'
    return [0.30, 0.16, 0.62, 0.34, 0.18][(cx * 7 + cy * 13) % 5], 'blood'


def tone_crystal_lamp(x, y):
    if x in (0, 15) or y in (0, 15) or x in (7, 8) or y in (7, 8):
        return 0.52, 'gold'
    d = max(abs(x - 7.5), abs(y - 7.5))
    if d < 2.2:
        return 0.88, 'blood'
    if d < 4.2:
        return 0.60, 'blood'
    return 0.26, 'blood'


def tone_scale_bricks(x, y):
    row = y // 4
    bx = (x + (row % 2) * 4) % 8
    if y % 4 == 0 or bx == 0:
        return 0.12, 'metal'
    if (x * 5 + y * 3) % 19 == 0:
        return 0.90, 'gold'
    return 0.66 - 0.14 * (y % 4) / 3.0 + 0.10 * (1 - bx / 7.0), 'metal'


def tone_pillar_side(x, y):
    if x in (0, 15):
        return 0.10, 'metal'
    t = {0: 0.12, 1: 0.62, 2: 0.42, 3: 0.18}[x % 4]
    if x % 4 == 1 and y % 8 == 4:
        return 0.88, 'gold'
    return t, 'metal'


def tone_pillar_top(x, y):
    r = max(abs(x - 7.5), abs(y - 7.5))
    if r > 6.6:
        return 0.12, 'metal'
    if r > 5.2:
        return 0.56, 'metal'
    if r > 3.6:
        return 0.82, 'gold'
    if r > 2.2:
        return 0.28, 'gold'
    return 0.72, 'metal'


def tone_nest(x, y):
    for ex, ey in ((5, 6), (10, 9)):
        dx, dy = x - ex, (y - ey) * 1.3
        r2 = dx * dx + dy * dy
        if r2 <= 5.2:
            return (0.14, 'bone') if r2 >= 3.0 else (0.84 if (x + y) % 3 else 0.62, 'bone')
    band = (x + y) % 8
    if band < 3:
        return 0.56, 'wood'
    if band < 5:
        return 0.22, 'wood'
    return (0.46, 'wood') if (x - y) % 8 < 4 else (0.18, 'wood')


TILES = {
    'dragon_scale_block': tone_scale_block,
    'dragon_bone_block': tone_bone_block,
    'dragon_crystal_block': tone_crystal_block,
    'dragon_crystal_lamp': tone_crystal_lamp,
    'dragon_scale_bricks': tone_scale_bricks,
    'dragon_scale_pillar_side': tone_pillar_side,
    'dragon_scale_pillar_top': tone_pillar_top,
    'dragon_nest': tone_nest,
}


def render(tone_fn):
    base = [[0.0] * 16 for _ in range(16)]
    kind = [['metal'] * 16 for _ in range(16)]
    for y in range(16):
        for x in range(16):
            base[y][x], kind[y][x] = tone_fn(x, y)
    im = Image.new('RGBA', (16, 16))
    px = im.load()
    for y in range(16):
        for x in range(16):
            t = base[y][x]
            # 左上打光的倒角：环绕取样，平铺不裂
            bevel = 0.40 * (2 * t - base[(y - 1) % 16][x] - base[y][(x - 1) % 16])
            px[x, y] = ramp(RAMPS[kind[y][x]], t + bevel)
    return im


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(PREVIEW, exist_ok=True)
    tiles = []
    for name, fn in TILES.items():
        im = render(fn)
        im.save(os.path.join(OUT, name + '.png'))
        tiles.append(im)

    cols = 4
    cell = 16 * 2 * 5
    pad = 8
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new('RGBA', (cols * (cell + pad) + pad, rows * (cell + pad) + pad), (40, 40, 46, 255))
    for i, im in enumerate(tiles):
        big = im.resize((cell // 2, cell // 2), Image.NEAREST)
        tile = Image.new('RGBA', (cell, cell))
        for tx in range(2):
            for ty in range(2):
                tile.paste(big, (tx * cell // 2, ty * cell // 2))
        sheet.paste(tile, (pad + (i % cols) * (cell + pad), pad + (i // cols) * (cell + pad)))
    sheet.save(os.path.join(PREVIEW, 'wave2_blocks_2x2_5x.png'))
    print('blocks:', len(tiles), '->', OUT)


if __name__ == '__main__':
    main()
