# -*- coding: utf-8 -*-
"""龙息斩粒子贴图（手绘 32×32 RGBA，两张）。

`fycq_dragon_breath` = 主喷射的软 puff：亮青核心 → 青绿外缘 → 透明边界，
带三颗小飞溅，边缘做抖动让它不像"圆贴纸上刷了一层"。
`fycq_dragon_breath_hit` = 命中溅射：六芒爆点 + 白热核心，尺寸小、寿命短。

调色与技能按钮同源（`draw_skill_button.py` 的 BREATH），保证 HUD 与世界特效一个语汇。
输出旁附 6x 接触表到 docs/tools/preview/（.gitignore 已排除，只本地看）。
"""
import os

from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'awesome_resource_packs', 'textures', 'particle')
PREVIEW = os.path.join(os.path.dirname(__file__), 'preview')

CORE = (238, 252, 244)
MID = (150, 226, 200)
OUTER = (56, 150, 132)
DEEP = (22, 74, 66)
S = 32


def px_set(px, x, y, color, alpha):
    if 0 <= x < S and 0 <= y < S and alpha > 0:
        r, g, b = color
        px[int(x), int(y)] = (r, g, b, max(0, min(255, int(alpha))))


def lerp(a, b, k):
    return tuple(int(round(a[i] + (b[i] - a[i]) * k)) for i in range(3))


def ramp(t):
    """连续颜色 + 连续 alpha：alpha = (1-t)^1.7，核心只留很小一点白热，
    避免出现"肥皂泡"式的硬圆边界（粒子是叠加混合，硬边会直接糊成白斑）。"""
    if t >= 1.0:
        return 0.0, None
    if t < 0.14:
        color = CORE
    elif t < 0.42:
        color = lerp(CORE, MID, (t - 0.14) / 0.28)
    elif t < 0.72:
        color = lerp(MID, OUTER, (t - 0.42) / 0.30)
    else:
        color = lerp(OUTER, DEEP, (t - 0.72) / 0.28)
    return (1.0 - t) ** 1.7, color


def blob(px, cx, cy, radius, strength=1.0, flare=0.0):
    """软边团。flare>0 时朝 +x 拉长（龙息喷出的方向感）。"""
    for y in range(S):
        for x in range(S):
            ex = (x + 0.5 - cx) / (1.0 + flare * max(0.0, x + 0.5 - cx) / radius)
            ey = y + 0.5 - cy
            t = ((ex * ex + ey * ey) ** 0.5) / radius
            alpha, color = ramp(t)
            if color:
                px_set(px, x, y, color, 255 * alpha * strength)


def draw_puff():
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    px = im.load()
    blob(px, 13.0, 16.0, 14.0, 1.0, flare=0.5)
    # 喷射远端的几缕拉丝（不再叠第二个圆，否则在透明底上会糊成一颗白斑）
    for x, y, n in [(28, 17, 3), (30, 20, 2), (27, 10, 2)]:
        for k in range(n):
            px_set(px, x, y + k, OUTER, 80 - k * 22)
    return im


def draw_hit():
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    px = im.load()
    blob(px, 16.0, 16.0, 7.5, 1.0)
    # 六芒：长短交替，末端渐隐
    spikes = [(1, 0, 13), (-1, 0, 13), (0, 1, 12), (0, -1, 12),
              (1, 1, 9), (-1, -1, 9), (1, -1, 9), (-1, 1, 9)]
    for dx, dz, length in spikes:
        for step in range(length):
            t = step / float(length)
            x = 16 + dx * (2 + step)
            y = 16 + dz * (2 + step)
            color = CORE if t < 0.3 else (MID if t < 0.65 else OUTER)
            px_set(px, x, y, color, 235 * (1.0 - t * 0.8))
            if length > 8:
                px_set(px, x + dx, y + dz, color, 120 * (1.0 - t * 0.8))
    return im


def contact_sheet(name, src):
    os.makedirs(PREVIEW, exist_ok=True)
    scales = (1, 3, 6)
    sheet = Image.new('RGBA', (sum(S * s for s in scales) + 16 * len(scales),
                               max(S * s for s in scales)), (24, 24, 28, 255))
    x = 8
    for s in scales:
        sheet.paste(src.resize((S * s, S * s), Image.NEAREST), (x, 0))
        x += S * s + 16
    path = os.path.join(PREVIEW, name + '_contact.png')
    sheet.save(path)
    return path


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, img in (('fycq_dragon_breath', draw_puff()),
                      ('fycq_dragon_breath_hit', draw_hit())):
        path = os.path.join(OUT, name + '.png')
        img.save(path)
        filled = sum(1 for p in img.getdata() if p[3] > 0)
        print('写入 %s  32x32  不透明纹素 %d (%.0f%%)' % (path, filled, 100.0 * filled / (S * S)))
        print('  接触表 %s' % contact_sheet(name, img))


if __name__ == '__main__':
    main()
