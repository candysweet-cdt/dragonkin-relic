"""波1（龙裔遗骸）像素资产：13 个物品图标 + 2 套盔甲甲片。

做法（对照 docs/tools/preview/ref_vanilla_8x.png 量出来的原版语汇：
斜柄 + 3~4 阶金属 + 深色描边 + 柄头绑金，明度跨度 149~227）：

  · 工具/武器/盔甲：取原版 diamond_* 的剪影与明度分布，按色相分材料，
    再映射到龙裔色阶（金属=龙鳞青、绑带=鎏金、柄=骨白），叠一层鳞纹
  · 龙血结晶：原版 diamond 本身就是刻面宝石，只换色相
  · 龙鳞 / 龙牙 / 龙心：无对应原版件，用已确认可辨认的轮廓 + 方向光与
    环境遮蔽渲染（不再是平涂）
  · 甲片：借原版 iron_1/iron_2 的 UV 轮廓当遮罩，图案与色阶自己画

参考基准图：docs/tools/preview/ref_vanilla_8x.png
"""
import os
from PIL import Image

from palette import OUTLINE, METAL, GOLD, BONE, BLOOD, ROBE, IRON, GLASS, RAMPS, ramp, lum

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
RP = os.path.join(ROOT, 'awesome_resource_packs')
OUT_ITEMS = os.path.join(RP, 'textures', 'items')
OUT_ARMOR = os.path.join(RP, 'textures', 'models', 'armor')
PREVIEW = os.path.join(os.path.dirname(__file__), 'preview')
VANILLA = r'D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.436581/data/resource_packs/vanilla/textures/items/'
VANILLA_ARMOR = r'D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.436581/data/resource_packs/vanilla/textures/models/armor/'

ORDER = ['dragon_scale', 'dragon_fang', 'dragon_heart', 'dragon_blood_crystal',
         'dragon_fang_sword', 'dragon_scale_pickaxe', 'dragon_scale_axe',
         'dragon_scale_shovel', 'dragon_scale_hoe', 'dragon_scale_helmet',
         'dragon_scale_chestplate', 'dragon_scale_leggings', 'dragon_scale_boots',
         'zz_drasnea_egg', 'zz_dragon_whelp_egg', 'zz_dragon_priest_egg', 'zz_dragon_guard_egg',
         'dragon_blood_dew']


def classify(c):
    r, g, b, a = c
    if a == 0:
        return None
    if lum(c) < 55:
        return 'outline'
    if r > 190 and g > 190 and b > 190:
        return 'spec'
    if b > r + 12 and g > r + 4:
        return 'metal'
    if r > b + 10:
        return 'grip'
    if g > r + 10 and g > b + 10:
        return 'metal'
    return 'metal'


def remap(src, metal=METAL, grip=BONE, scale_texture=True, gold_trim=False, spec_t=1.0):
    """按色相把原版图标分成 描边/金属/握柄 三类，再映射到龙裔色阶。"""
    im = Image.open(src).convert('RGBA')
    px = im.load()
    kinds = {(x, y): classify(px[x, y]) for y in range(16) for x in range(16)}
    out = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    op = out.load()
    for y in range(16):
        for x in range(16):
            k = kinds[(x, y)]
            if k is None:
                continue
            if k == 'outline':
                op[x, y] = OUTLINE
                continue
            t = (lum(px[x, y]) - 55) / 200.0
            if k == 'spec':
                op[x, y] = ramp(metal, spec_t)
                continue
            if k == 'grip':
                near_metal = any(kinds.get((x + dx, y + dy)) == 'metal'
                                 for dx in (-1, 0, 1) for dy in (-1, 0, 1))
                op[x, y] = ramp(GOLD if (gold_trim and near_metal) else grip, t)
                continue
            if scale_texture and (x + (y // 2) * 2) % 5 == 0:
                t -= 0.18
            if gold_trim and y <= 2:
                op[x, y] = ramp(GOLD, min(1.0, t + 0.15))
            else:
                op[x, y] = ramp(metal, t)
    return out


SHAPES = {
    'dragon_blood_dew': ("""
................
......oooo......
......oGGo......
......oGGo......
.....ooIwoo.....
.....oIwwIo.....
....oIwwwwIo....
....oIBBwwIo....
....oIBBBBIo....
....oIBrBBIo....
....oIBrBBIo....
....oIBBBBIo....
.....oIbBIo.....
......oooo......
................
................
""", {'o': ('outline', 0), 'G': ('gold', .6), 'I': ('glass', .45),
      'w': ('glass', .85), 'B': ('blood', .42), 'b': ('blood', .28),
      'r': ('blood', .62)}),
    'dragon_scale': ("""
................
.......oo.......
.....ooGGoo.....
....oGyyyyGo....
...oGylllltGo...
...oGyllttltGo..
...oGylttttlGo..
...oGylttttGo...
....oGylttGo....
....oGytttGo....
.....oGGtGo.....
......oooo......
................
................
................
................
""", {'o': ('outline', 0), 'G': ('gold', .35), 'y': ('gold', .78),
      'l': ('metal', .74), 't': ('metal', .40)}),
    'dragon_fang': ("""
................
........oooo....
.......oIIIIo...
......oIwwIIo...
......oIwwIIo...
.....oIwwwIIo...
.....oIwwIIo....
....oIwwIIo.....
....oIwIIo......
...oIwIIo.......
...oIIio........
...oIio.........
....oo..........
................
................
................
""", {'o': ('outline', 0), 'I': ('bone', .55), 'w': ('bone', .92), 'i': ('bone', .22)}),
    'dragon_heart': ("""
................
...ooo....ooo...
..oBrro..orrBo..
.oBrrrBooBrrrBo.
oBrrrrbbbbrrrrBo
oBrrrbbbbbbrrrBo
oBrrbbbbbbbbrrBo
.oBrrbbbbbbrrBo.
..oBrrbbbbrrBo..
...oBrrbbrrBo...
....oBrrrrBo....
.....oBrrBo.....
......oBBo......
.......oo.......
................
................
""", {'o': ('blood', .04), 'B': ('blood', .20), 'r': ('blood', .36), 'b': ('blood', .52)}),
}


def shade_ascii(text, charmap):
    rows = [r for r in text.strip('\n').split('\n')]
    assert len(rows) == 16, f'行数 {len(rows)}'
    grid = {}
    for y, row in enumerate(rows):
        assert len(row) == 16, f'第 {y} 行长度 {len(row)}: {row!r}'
        for x, ch in enumerate(row):
            grid[(x, y)] = None if ch == '.' else charmap[ch]
    out = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    op = out.load()
    for y in range(16):
        for x in range(16):
            cell = grid.get((x, y))
            if cell is None:
                continue
            name, base = cell
            if name == 'outline':
                op[x, y] = OUTLINE
                continue
            t = base + 0.20 * (1 - y / 15.0) - 0.10 * (x / 15.0)
            if any(grid.get((x + dx, y + dy)) is None
                   for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1))):
                t -= 0.22
            if (x + y) % 7 == 0:
                t += 0.05
            op[x, y] = ramp(RAMPS[name], t)
    return out


def armor_layer(src, dst):
    """借原版甲片的 UV 遮罩，画自己的鳞甲：色调场 + 左上倒角（只在遮罩内比较）。"""
    base_im = Image.open(src).convert('RGBA')
    bp = base_im.load()
    mask = {(x, y): bp[x, y][3] > 0 for y in range(32) for x in range(64)}
    tone = {}
    for y in range(32):
        for x in range(64):
            if not mask[(x, y)]:
                continue
            band = y % 16
            row = y // 3
            sx = (x + (row % 2) * 4) % 8
            if band in (0, 1):
                tone[(x, y)] = (0.85 if band == 0 else 0.55, 'gold')
            elif band == 15:
                tone[(x, y)] = (0.10, 'metal')
            elif sx in (0, 7):
                tone[(x, y)] = (0.12, 'metal')
            else:
                t = 0.70 - 0.36 * abs(sx - 3.5) / 4.0 - 0.11 * (y % 3)
                if (x * 3 + y * 5) % 31 == 0:
                    tone[(x, y)] = (0.90, 'gold')
                else:
                    tone[(x, y)] = (t, 'metal')
    out = Image.new('RGBA', (64, 32), (0, 0, 0, 0))
    op = out.load()
    for y in range(32):
        for x in range(64):
            if not mask[(x, y)]:
                continue
            t, kind = tone[(x, y)]
            up = tone[((x, y - 1) if mask.get((x, y - 1)) else (x, y))][0]
            left = tone[((x - 1, y) if mask.get((x - 1, y)) else (x, y))][0]
            op[x, y] = ramp(RAMPS[kind], t + 0.40 * (2 * t - up - left))
    out.save(dst)


def draw_egg(shell=METAL, speck=GOLD):
    """刷怪蛋：蛋形轮廓（顶窄、最宽在下三分之一）+ 青鳞壳渐变 + 金色鳞斑 + 描边。"""
    import math
    im = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    px = im.load()
    rx, ry, cy = 6.2, 7.6, 8.2
    for y in range(16):
        dy = (y + 0.5 - cy) / ry
        if abs(dy) >= 1.0:
            continue
        taper = 0.60 + 0.40 * (y / 15.0)          # 上窄下宽，成蛋不成人头
        w = rx * math.sqrt(1 - dy * dy) * taper
        for x in range(16):
            d = abs(x + 0.5 - 7.5)
            if d > w:
                continue
            t = 0.64 - 0.24 * (d / max(w, 0.001)) + 0.07 * (1 - y / 15.0)
            if d > w - 0.8:
                t = 0.12
            px[x, y] = ramp(shell, t)
    for sx, sy in ((6, 5), (10, 8), (5, 10), (9, 12)):
        for dx, dy2 in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            x, y = sx + dx, sy + dy2
            if 0 <= x < 16 and 0 <= y < 16 and px[x, y][3]:
                px[x, y] = ramp(speck, 0.80 if dx == 0 and dy2 == 0 else 0.45)
    for y in range(16):
        for x in range(16):
            if px[x, y][3] == 0:
                continue
            if any(not px[min(max(x + dx, 0), 15), min(max(y + dy2, 0), 15)][3]
                   for dx, dy2 in ((-1, 0), (1, 0), (0, -1), (0, 1))):
                px[x, y] = OUTLINE
    return im


EGG_STYLES = {
    'zz_drasnea_egg': (METAL, GOLD),
    'zz_dragon_whelp_egg': (METAL, BONE),
    'zz_dragon_priest_egg': (ROBE, GOLD),
    'zz_dragon_guard_egg': (IRON, METAL),
}


TEMPLATES = {
    'dragon_fang_sword': ('diamond_sword', False),
    'dragon_scale_pickaxe': ('diamond_pickaxe', False),
    'dragon_scale_axe': ('diamond_axe', False),
    'dragon_scale_shovel': ('diamond_shovel', False),
    'dragon_scale_hoe': ('diamond_hoe', False),
    'dragon_scale_helmet': ('diamond_helmet', True),
    'dragon_scale_chestplate': ('diamond_chestplate', True),
    'dragon_scale_leggings': ('diamond_leggings', True),
    'dragon_scale_boots': ('diamond_boots', True),
}


def sheet(images, scale, cols, path, pad=3):
    cell = 16 * scale
    rows = (len(images) + cols - 1) // cols
    s = Image.new('RGBA', (cols * (cell + pad) + pad, rows * (cell + pad) + pad), (40, 40, 46, 255))
    for i, im in enumerate(images):
        big = im.resize((cell, cell), Image.NEAREST)
        s.paste(big, (pad + (i % cols) * (cell + pad), pad + (i // cols) * (cell + pad)), big)
    s.save(path)


def main():
    for d in (OUT_ITEMS, OUT_ARMOR, PREVIEW):
        os.makedirs(d, exist_ok=True)

    icons = {}
    for ident, (tmpl, armor) in TEMPLATES.items():
        icons[ident] = remap(VANILLA + tmpl + '.png', grip=BONE, gold_trim=armor)
    icons['dragon_blood_crystal'] = remap(VANILLA + 'diamond.png', metal=BLOOD, grip=BLOOD,
                                          scale_texture=False, spec_t=0.62)
    for ident, (art, cmap) in SHAPES.items():
        icons[ident] = shade_ascii(art, cmap)
    for stem, (sh, sp) in EGG_STYLES.items():
        icons[stem] = draw_egg(sh, sp)

    for ident in ORDER:
        icons[ident].save(os.path.join(OUT_ITEMS, ident + '.png'))

    armor_layer(VANILLA_ARMOR + 'iron_1.png', os.path.join(OUT_ARMOR, 'dragon_scale_1.png'))
    armor_layer(VANILLA_ARMOR + 'iron_2.png', os.path.join(OUT_ARMOR, 'dragon_scale_2.png'))

    ordered = [icons[i] for i in ORDER]
    for scale in (5, 8):
        sheet(ordered, scale, 7, os.path.join(PREVIEW, f'wave1_icons_{scale}x.png'))
    for n in ('dragon_scale_1', 'dragon_scale_2'):
        im = Image.open(os.path.join(OUT_ARMOR, n + '.png'))
        im.resize((64 * 5, 32 * 5), Image.NEAREST).save(os.path.join(PREVIEW, f'{n}_5x.png'))
    print(f'icons: {len(ORDER)} | armor: 2')


if __name__ == '__main__':
    main()
