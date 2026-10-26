# -*- coding: utf-8 -*-
"""清掉翅膀加厚后露出的 1px 侧面黑条（实机会显示成悬浮矩形框）。

翅膀膜块 size.x 从 0 补到 1 纹素后，±Z / ±Y 四个侧面各占 1px 宽的 UV 条带。
条带若采到不透明黑，就会沿整个 cube 矩形描出一圈黑边——翅膀轮廓之外的
透明区也会被描上，看起来就是"悬浮方框"。

清掉「没有被其它非侧面 UV 覆盖」的侧面纹素（黑框和绿色边缘都清）：
  · 侧面条带与爪子/角/相邻翅膀的宽面有少量重叠（如 x=18、x=86/87），
    这些像素保留，避免在别的部件上打洞。

用法：python docs/tools/fix_wing_edge_strips.py [--write]
"""
import io
import json
import os
import sys

from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
MODEL = os.path.join(ROOT, 'awesome_resource_packs', 'models', 'entity', 'drasnea.json')
TEX = os.path.join(ROOT, 'awesome_resource_packs', 'textures', 'entity', 'fycq', 'drasnea.png')
SIDES = ('north', 'south', 'up', 'down')


def ir(v):
    return int(round(v))


def faces(uv, size):
    u, v = ir(uv[0]), ir(uv[1])
    w, h, d = ir(size[0]), ir(size[1]), ir(size[2])
    return {
        'west': (u, v + d, d, h),
        'north': (u + d, v + d, w, h),
        'east': (u + d + w, v + d, d, h),
        'south': (u + d + w + d, v + d, w, h),
        'up': (u + d, v, w, d),
        'down': (u + d + w, v, w, d),
    }


def is_wing(bone, cube):
    return 'wind' in bone and isinstance(cube.get('uv'), list) and abs(cube['size'][0] - 1.0) < 1e-6


def main():
    write = '--write' in sys.argv
    geo = json.load(io.open(MODEL, encoding='utf-8'))['geometry.drasnea']
    img = Image.open(TEX).convert('RGBA')
    px = img.load()

    protected = set()
    strips = set()
    for bone in geo['bones']:
        for cube in bone.get('cubes') or []:
            if not isinstance(cube.get('uv'), list):
                continue
            fr = faces(cube['uv'], cube['size'])
            wing = is_wing(bone['name'], cube)
            for name, (x, y, w, h) in fr.items():
                cells = [(xx, yy) for yy in range(y, y + h) for xx in range(x, x + w)]
                if wing and name in SIDES:
                    strips.update(cells)
                else:
                    protected.update(cells)

    targets = []
    blacks = 0
    for (x, y) in sorted(strips - protected):
        r, g, b, a = px[x, y]
        if a > 0:
            if a > 200 and max(r, g, b) < 24:
                blacks += 1
            targets.append((x, y))
    print('翅膀侧面条带:', len(strips), '| 与其它面共用:', len(strips & protected),
          '| 待清像素:', len(targets), '（其中纯黑 %d）' % blacks)
    for x, y in targets:
        print('  (%d,%d)' % (x, y))
    if not write:
        print('（只报告，未写入；加 --write 生效）')
        return
    for x, y in targets:
        px[x, y] = (0, 0, 0, 0)
    img.save(TEX)
    print('已写入', TEX)


if __name__ == '__main__':
    main()
