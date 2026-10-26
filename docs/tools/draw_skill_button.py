# -*- coding: utf-8 -*-
"""龙息斩技能按钮贴图（64×64，默认 / 按下两张）。

画的是「龙口喷息」：暗底圆盘 + 鎏金外圈 + 青鳞龙息锥 + 两颗牙，
按下版本整体提亮并让龙息更白，保证在亮背景 HUD 上也看得清。
"""
import math
import os

from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'awesome_resource_packs', 'textures', 'ui')
PREVIEW = os.path.join(os.path.dirname(__file__), 'preview')

SIZE = 64
CENTER = SIZE / 2.0
OUTLINE = (16, 13, 11, 255)
BASE_DARK = (26, 21, 17, 255)
BASE_MID = (38, 31, 25, 255)
GOLD = [(78, 58, 10, 255), (170, 134, 28, 255), (246, 220, 130, 255)]
BREATH = [(24, 74, 67, 255), (58, 152, 134, 255), (168, 234, 212, 255), (240, 252, 246, 255)]
BONE = (240, 236, 216, 255)


def disc(im, radius, colors):
    px = im.load()
    for y in range(SIZE):
        for x in range(SIZE):
            r = math.hypot(x + 0.5 - CENTER, y + 0.5 - CENTER)
            if r <= radius:
                t = r / radius
                px[x, y] = colors[2] if t > 0.92 else (colors[1] if t > 0.72 else colors[0])
            elif r <= radius + 1.6:
                px[x, y] = OUTLINE


def ring(px, r_in, r_out, cols):
    for y in range(SIZE):
        for x in range(SIZE):
            r = math.hypot(x + 0.5 - CENTER, y + 0.5 - CENTER)
            if r_in <= r <= r_out:
                a = (math.atan2(y + 0.5 - CENTER, x + 0.5 - CENTER) + math.pi) / (2 * math.pi)
                px[x, y] = cols[int(a * (len(cols) - 1) * 2) % len(cols)]


def breath(px, bright):
    """龙息锥：从左侧龙口向右展开，越远越淡；边缘做波动。"""
    for y in range(SIZE):
        for x in range(18, 52):
            t = (x - 18) / 34.0
            half = 3.0 + t * 11.0
            wave = 1.6 * math.sin((y + x * 0.6) * 0.55)
            dy = abs(y + 0.5 - (CENTER + wave * 0.6))
            if dy <= half:
                k = 1.0 - (dy / half)
                idx = min(3, int(k * 3.4))
                col = BREATH[idx if not bright else min(3, idx + 1)]
                px[x, y] = col


def draw(pressed):
    im = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    px = im.load()
    disc(im, 29.0, [BASE_MID if pressed else BASE_DARK, BASE_DARK, OUTLINE])
    ring(px, 24.5, 27.6, GOLD)
    breath(px, pressed)
    # 龙口与两颗牙（左侧）
    d = ImageDraw.Draw(im)
    d.polygon([(13, 26), (22, 30), (13, 34)], fill=BONE)
    d.polygon([(14, 34), (21, 36), (14, 41)], fill=BONE)
    d.ellipse([8, 24, 20, 42], outline=OUTLINE, width=2)
    # 四颗铆点
    for ang in (45, 135, 225, 315):
        a = math.radians(ang)
        cx = CENTER + math.cos(a) * 26.0
        cy = CENTER + math.sin(a) * 26.0
        d.ellipse([cx - 1.6, cy - 1.6, cx + 1.6, cy + 1.6], fill=GOLD[2])
    return im


def main():
    os.makedirs(OUT, exist_ok=True)
    draw(False).save(os.path.join(OUT, 'dragon_skill_btn.png'))
    draw(True).save(os.path.join(OUT, 'dragon_skill_btn_click.png'))
    os.makedirs(PREVIEW, exist_ok=True)
    sheet = Image.new('RGBA', (SIZE * 4 * 2 + 24, SIZE * 4), (90, 90, 90, 255))
    for i, pressed in enumerate((False, True)):
        im = draw(pressed).resize((SIZE * 4, SIZE * 4), Image.NEAREST)
        sheet.alpha_composite(im, (i * (SIZE * 4 + 24), 0))
    sheet.save(os.path.join(PREVIEW, 'skill_button_4x.png'))
    print('skill button textures saved')


if __name__ == '__main__':
    main()
