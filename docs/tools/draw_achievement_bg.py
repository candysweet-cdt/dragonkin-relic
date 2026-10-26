# -*- coding: utf-8 -*-
"""成就页背景：64×64 无缝龙鳞瓦片（引擎按背景板大小平铺）。

不能引用官方教程示例里的 textures/ui/background/sign_warped —— 本版本没有这张图，
会显示紫黑格。这里自己出图，并保证四边可无缝平铺。
"""
import os
import random

from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'awesome_resource_packs', 'textures', 'ui', 'dragonkin_achievement_bg.png')

SIZE = 64
ROW_H = 16
SCALE_W = 16
BASE = (26, 20, 16)
SCALE = (38, 29, 23)
EDGE = (54, 41, 31)
HILITE = (72, 54, 39)

random.seed(7)
img = Image.new('RGB', (SIZE, SIZE), BASE)
draw = ImageDraw.Draw(img)


def arc(x, y, color, width=1):
    draw.arc([x, y, x + SCALE_W, y + ROW_H * 2], 200, 340, fill=color, width=width)


for row, y in enumerate(range(-ROW_H, SIZE + ROW_H, ROW_H)):
    offset = (row % 2) * (SCALE_W // 2)
    for x in range(-SCALE_W, SIZE + SCALE_W, SCALE_W):
        left = x + offset
        for dx in (-SIZE, 0, SIZE):
            for dy in (-SIZE, 0, SIZE):
                arc(left + dx, y + dy, EDGE)
                arc(left + dx, y + 1 + dy, SCALE)
        if row % 3 == 0:
            for dx in (-SIZE, 0, SIZE):
                for dy in (-SIZE, 0, SIZE):
                    draw.point((left + dx + SCALE_W // 2, y + dy + 7), fill=HILITE)

# 极轻的暗角/斑驳，避免平铺后看起来太干净；随机点也做四边镜像保证无缝
for _ in range(90):
    x = random.randrange(SIZE)
    y = random.randrange(SIZE)
    shade = random.choice(((22, 17, 14), (30, 23, 18)))
    for dx in (-SIZE, 0, SIZE):
        for dy in (-SIZE, 0, SIZE):
            px = x + dx
            py = y + dy
            if 0 <= px < SIZE and 0 <= py < SIZE:
                img.putpixel((px, py), shade)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
img.save(OUT)
print('saved', OUT, img.size)
