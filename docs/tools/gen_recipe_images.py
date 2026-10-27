# -*- coding: utf-8 -*-
"""生成原版工作台风格的 3x3 配方合成图（从星轨工坊移植，改成本包的 awesome_* 目录与 fycq 命名空间）。

用法:
  python docs/tools/gen_recipe_images.py --recipe dragon_fang_sword
  python docs/tools/gen_recipe_images.py --recipe steam_boiler,steam_firebox --out docs/预览/配方图
  python docs/tools/gen_recipe_images.py --theme dragon --out docs/宣传图/配方
  python docs/tools/gen_recipe_images.py --all --out docs/预览/配方图

背景与槽位按原版 GUI 调色板绘制，不截图、不依赖客户端：
  底色 #C6C6C6 / 槽面 #8B8B8B / 上左 #373737 / 下右 #FFFFFF。
方块优先用资源包里现成的 64x64 `_item.png`；原版方块用 blocks.json 的六面贴图
拼一个等轴方块图标；物品用 item_texture.json 的 16/32x32 图标。
"""
import argparse
import glob
import json
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PACK = os.path.join(ROOT, "awesome_behavior_packs")
RP = os.path.join(ROOT, "awesome_resource_packs")

BG = (198, 198, 198, 255)
SLOT = (139, 139, 139, 255)
DARK = (55, 55, 55, 255)
LIGHT = (255, 255, 255, 255)

DIGITS = {
    "0": ("111", "101", "101", "101", "111"),
    "1": ("010", "110", "010", "010", "111"),
    "2": ("111", "001", "111", "100", "111"),
    "3": ("111", "001", "111", "001", "111"),
    "4": ("101", "101", "111", "001", "001"),
    "5": ("111", "100", "111", "001", "111"),
    "6": ("111", "100", "111", "101", "111"),
    "7": ("111", "001", "010", "010", "010"),
    "8": ("111", "101", "111", "101", "111"),
    "9": ("111", "101", "111", "001", "111"),
}

# blocks.json 里没有、但配方会用到的旧 ID
ITEM_ALIASES = {
    "glass_bottle": "potion_bottle_empty",
    "redstone": "redstone_dust",
    "slime_ball": "slimeball",
    "nether_brick": "netherbrick",
    "white_dye": "dye_powder_white_new",
    "black_dye": "dye_powder_black_new",
    "blue_dye": "dye_powder_blue_new",
    "brown_dye": "dye_powder_brown_new",
    "light_blue_dye": "dye_powder_light_blue",
    "light_gray_dye": "dye_powder_silver",
    "lime_dye": "dye_powder_lime",
    "magenta_dye": "dye_powder_magenta",
    "orange_dye": "dye_powder_orange",
    "pink_dye": "dye_powder_pink",
    "purple_dye": "dye_powder_purple",
    "red_dye": "dye_powder_red",
    "yellow_dye": "dye_powder_yellow",
    "green_dye": "dye_powder_green",
    "cyan_dye": "dye_powder_cyan",
    "gray_dye": "dye_powder_gray",
}

FLAT_BLOCKS = {
    "glass_pane", "iron_bars", "rail", "golden_rail", "detector_rail",
    "activator_rail", "torch", "soul_torch", "redstone_torch", "lantern",
    "flower_pot", "vine", "ladder", "lever", "stone_button", "wooden_button",
    "stone_pressure_plate", "wooden_pressure_plate", "cobweb", "chain",
    "candle", "end_rod", "lightning_rod",
}


def newest_vanilla():
    pats = glob.glob(r"D:\MCStudioDownload\game\MinecraftPE_Netease\*\data\resource_packs\vanilla")
    if not pats:
        return None
    def version(path):
        import re
        m = re.search(r"MinecraftPE_Netease[\\/](\d+)\.(\d+)\.(\d+)", path)
        return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)
    return max(pats, key=version)


VANILLA = newest_vanilla()


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def texture_path(value):
    if isinstance(value, dict):
        value = value.get("textures") or value.get("path")
    if isinstance(value, list):
        value = value[0] if value else None
    if not value or not isinstance(value, str):
        return None
    return value if value.endswith(".png") else value + ".png"


def load_texture_map(path):
    data = (load_json(path, {}) or {}).get("texture_data") or {}
    out = {}
    for key, value in data.items():
        p = texture_path(value)
        if p:
            out[key] = p
    return out


def load_maps():
    custom_items = load_texture_map(os.path.join(RP, "textures", "item_texture.json"))
    custom_blocks = load_texture_map(os.path.join(RP, "textures", "terrain_texture.json"))
    vanilla_items = {}
    vanilla_blocks = {}
    vanilla_faces = {}
    if VANILLA:
        vanilla_items = load_texture_map(os.path.join(VANILLA, "textures", "item_texture.json"))
        vanilla_blocks = load_texture_map(os.path.join(VANILLA, "textures", "terrain_texture.json"))
        vanilla_faces = load_json(os.path.join(VANILLA, "blocks.json"), {}) or {}
    return custom_items, custom_blocks, vanilla_items, vanilla_blocks, vanilla_faces


CUSTOM_ITEMS, CUSTOM_BLOCKS, VANILLA_ITEMS, VANILLA_BLOCKS, VANILLA_FACES = load_maps()
CUSTOM_FACES = load_json(os.path.join(RP, "blocks.json"), {}) or {}


def rgba(path):
    try:
        return Image.open(path).convert("RGBA")
    except Exception:
        return None


def draw_face(canvas, tex, corners, factor):
    """把 16x16 贴图映射到平行四边形 corners=(p0,p1,p2,p3)。"""
    p0, p1, p2, p3 = corners
    ux, uy = p1[0] - p0[0], p1[1] - p0[1]
    vx, vy = p3[0] - p0[0], p3[1] - p0[1]
    det = ux * vy - vx * uy
    if det == 0:
        return
    src = tex.convert("RGBA")
    sw, sh = src.size
    pix = src.load()
    out = canvas.load()
    min_x = max(0, int(min(p0[0], p1[0], p2[0], p3[0])))
    max_x = min(canvas.width - 1, int(max(p0[0], p1[0], p2[0], p3[0])) + 1)
    min_y = max(0, int(min(p0[1], p1[1], p2[1], p3[1])))
    max_y = min(canvas.height - 1, int(max(p0[1], p1[1], p2[1], p3[1])) + 1)
    for y in range(min_y, max_y + 1):
        for x in range(min_x, max_x + 1):
            dx, dy = x - p0[0], y - p0[1]
            u = (dx * vy - dy * vx) / det
            v = (dy * ux - dx * uy) / det
            if u < 0 or u >= 1 or v < 0 or v >= 1:
                continue
            sx = min(sw - 1, max(0, int(u * sw)))
            sy = min(sh - 1, max(0, int(v * sh)))
            r, g, b, a = pix[sx, sy]
            if a <= 0:
                continue
            out[x, y] = (int(r * factor), int(g * factor), int(b * factor), a)


def iso_block(top, left=None, right=None):
    top = top.convert("RGBA")
    left = (left or top).convert("RGBA")
    right = (right or top).convert("RGBA")
    canvas = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw_face(canvas, top, ((32, 0), (64, 16), (32, 32), (0, 16)), 1.0)
    draw_face(canvas, left, ((0, 16), (32, 32), (32, 64), (0, 48)), 0.80)
    draw_face(canvas, right, ((32, 32), (64, 16), (64, 48), (32, 64)), 0.60)
    return canvas


def block_face_paths(name, face_map):
    """返回 (top, left, right) 贴图绝对路径；找不到返回 None。"""
    if not VANILLA:
        return None
    spec = face_map.get(name)
    if isinstance(spec, dict) and "textures" in spec:
        spec = spec["textures"]
    top = left = right = None
    if isinstance(spec, str):
        top = left = right = spec
    elif isinstance(spec, dict):
        top = spec.get("up") or spec.get("side")
        left = spec.get("west") or spec.get("north") or spec.get("side")
        right = spec.get("east") or spec.get("south") or spec.get("side")
    if not top:
        tex = VANILLA_BLOCKS.get(name) or ""
        tex = os.path.basename(tex).replace(".png", "") if tex else name
        top = left = right = tex
    def find(tex_name):
        if not tex_name:
            return None
        tex_name = os.path.basename(tex_name).replace(".png", "").replace(".tga", "")
        candidates = []
        mapped = VANILLA_BLOCKS.get(tex_name)
        if isinstance(mapped, list):
            candidates.extend(mapped)
        elif mapped:
            candidates.append(mapped)
        candidates.append("textures/blocks/" + tex_name)
        for candidate in candidates:
            candidate = candidate.strip().replace(".png", "").replace(".tga", "")
            for ext in (".png", ".tga"):
                p = candidate + ext
                if not os.path.isabs(p):
                    p = os.path.join(VANILLA, p)
                if os.path.exists(p):
                    return p
        return None
    tp = find(top)
    lp = find(left) or tp
    rp = find(right) or tp
    return (tp, lp, rp) if tp else None


def custom_block_icon(name):
    p = os.path.join(RP, "textures", "blocks", name + "_item.png")
    img = rgba(p) if os.path.exists(p) else None
    if img:
        return img
    spec = CUSTOM_FACES.get("fycq:" + name) or CUSTOM_FACES.get(name) or {}
    face = spec.get("textures") if isinstance(spec, dict) else None
    if isinstance(face, str):
        top = left = right = face
    elif isinstance(face, dict):
        top = face.get("up") or face.get("side")
        left = face.get("west") or face.get("north") or face.get("side")
        right = face.get("east") or face.get("south") or face.get("side")
    else:
        tex = CUSTOM_BLOCKS.get(name)
        top = left = right = os.path.basename(tex).replace(".png", "") if tex else name
    def load(tex_name):
        if not tex_name:
            return None
        tex_name = os.path.basename(tex_name).replace(".png", "")
        p = os.path.join(RP, "textures", "blocks", tex_name + ".png")
        if not os.path.exists(p):
            mapped = CUSTOM_BLOCKS.get(tex_name)
            p = os.path.join(RP, mapped) if mapped else p
        return rgba(p) if os.path.exists(p) else None
    top_img = load(top)
    if not top_img:
        return None
    return iso_block(top_img, load(left) or top_img, load(right) or top_img)


def item_texture(name):
    p = CUSTOM_ITEMS.get("fycq:" + name) or CUSTOM_ITEMS.get(name)
    if p:
        img = rgba(os.path.join(RP, p))
        if img:
            return img
    p = os.path.join(RP, "textures", "items", name + ".png")
    if os.path.exists(p):
        return rgba(p)
    return None


def vanilla_item(name):
    key = ITEM_ALIASES.get(name, name)
    p = VANILLA_ITEMS.get(key)
    if p:
        img = rgba(os.path.join(VANILLA, p))
        if img:
            return img
    p = os.path.join(VANILLA, "textures", "items", key + ".png") if VANILLA else None
    if p and os.path.exists(p):
        return rgba(p)
    p = os.path.join(VANILLA, "textures", "items", key + ".tga") if VANILLA else None
    if p and os.path.exists(p):
        return rgba(p)
    return None


def vanilla_block(name):
    key = ITEM_ALIASES.get(name, name)
    if key in FLAT_BLOCKS:
        p = os.path.join(VANILLA, "textures", "blocks", key + "_top.png") if VANILLA else None
        if p and os.path.exists(p):
            return rgba(p)
    paths = block_face_paths(key, VANILLA_FACES)
    if paths:
        top, left, right = [rgba(x) for x in paths]
        if top:
            return iso_block(top, left, right)
    p = os.path.join(VANILLA, "textures", "blocks", key + ".png") if VANILLA else None
    if p and os.path.exists(p):
        return rgba(p)
    p = os.path.join(VANILLA, "textures", "blocks", key + ".tga") if VANILLA else None
    if p and os.path.exists(p):
        return rgba(p)
    return None


def icon_for(item):
    if not item:
        return None
    name = item.get("item") if isinstance(item, dict) else item
    if not name:
        return None
    ns, short = name.split(":", 1) if ":" in name else ("minecraft", name)
    if ns == "fycq":
        img = item_texture(short)
        if img:
            return img
        img = custom_block_icon(short)
        if img:
            return img
    else:
        img = vanilla_item(short)
        if img:
            return img
        img = vanilla_block(short)
        if img:
            return img
    return None


def scale_icon(img, box):
    """按整数倍放大到不超过 box；大图不缩小像素画。"""
    if img is None:
        return None, False
    factor = max(1, box // max(img.width, img.height))
    if factor == 1:
        out = img
    else:
        out = img.resize((img.width * factor, img.height * factor), Image.NEAREST)
    return out, True


def draw_slot(draw, x, y, size, edge=None):
    edge = edge or max(1, size // 18)
    draw.rectangle([x, y, x + size - 1, y + size - 1], fill=SLOT)
    draw.rectangle([x, y, x + size - 1, y + edge - 1], fill=DARK)
    draw.rectangle([x, y, x + edge - 1, y + size - 1], fill=DARK)
    draw.rectangle([x, y + size - edge, x + size - 1, y + size - 1], fill=LIGHT)
    draw.rectangle([x + size - edge, y, x + size - 1, y + size - 1], fill=LIGHT)


def paste_icon(canvas, img, x, y, size):
    scaled, _ok = scale_icon(img, size - 10)
    if scaled is None:
        return False
    px = x + (size - scaled.width) // 2
    py = y + (size - scaled.height) // 2
    canvas.alpha_composite(scaled, (px, py))
    return True


def draw_digits(draw, text, right, bottom, scale):
    s = max(1, scale - 1)
    w = len(text) * 4 * s - s
    h = 5 * s
    x = right - w - 3 * scale
    y = bottom - h - 3 * scale
    for ch in text:
        rows = DIGITS.get(ch)
        if rows:
            for ry, row in enumerate(rows):
                for rx, bit in enumerate(row):
                    if bit == "1":
                        draw.rectangle([x + rx * s, y + ry * s,
                                        x + rx * s + s - 1, y + ry * s + s - 1],
                                       fill=(55, 55, 55, 255))
        x += 4 * s
    x = right - w - 3 * scale - s
    y = bottom - h - 3 * scale - s
    for ch in text:
        rows = DIGITS.get(ch)
        if rows:
            for ry, row in enumerate(rows):
                for rx, bit in enumerate(row):
                    if bit == "1":
                        draw.rectangle([x + rx * s, y + ry * s,
                                        x + rx * s + s - 1, y + ry * s + s - 1],
                                       fill=(255, 255, 255, 255))
        x += 4 * s


def draw_arrow(draw, x0, y0, x1, y1, scale):
    cy = (y0 + y1) // 2
    shaft_h = max(2, int(2.5 * scale))
    head_h = max(3, int(5.0 * scale))
    head_w = max(3, int(8.0 * scale))
    draw.rectangle([x0, cy - shaft_h, x1 - head_w, cy + shaft_h], fill=SLOT)
    draw.polygon([(x1 - head_w, cy - head_h), (x1, cy), (x1 - head_w, cy + head_h)],
                 fill=SLOT)


def draw_flame(draw, cx, cy, scale):
    s = scale
    draw.polygon([(cx, cy - 5 * s), (cx + 3 * s, cy),
                  (cx + 2 * s, cy + 4 * s), (cx - 2 * s, cy + 4 * s),
                  (cx - 3 * s, cy)], fill=(230, 126, 34, 255))
    draw.polygon([(cx, cy - 2 * s), (cx + 1.5 * s, cy + 1 * s),
                  (cx + 1 * s, cy + 3 * s), (cx - 1 * s, cy + 3 * s),
                  (cx - 1.5 * s, cy + 1 * s)], fill=(241, 196, 15, 255))


def render_crafting(grid, result, scale):
    # 坐标以参考图的 5x 版为基准，再整体按 scale/5 缩放。
    unit = scale / 5.0
    w, h = int(round(607 * unit)), int(round(285 * unit))
    canvas = Image.new("RGBA", (w, h), BG)
    draw = ImageDraw.Draw(canvas)
    gx = gy = int(round(6 * unit))
    cell = int(round(90 * unit))
    edge = max(1, int(round(scale)))
    for r in range(3):
        for c in range(3):
            x, y = gx + c * cell, gy + r * cell
            draw_slot(draw, x, y, cell, edge)
            if grid[r][c]:
                paste_icon(canvas, grid[r][c], x, y, cell)
    draw_arrow(draw, int(round(350 * unit)), int(round(130 * unit)),
               int(round(450 * unit)), int(round(158 * unit)), scale)
    ox, oy = int(round(476 * unit)), int(round(79 * unit))
    osz = int(round(130 * unit))
    draw_slot(draw, ox, oy, osz, edge)
    paste_icon(canvas, result[0], ox, oy, osz)
    if result[1] > 1:
        draw_digits(draw, str(result[1]), ox + osz, oy + osz, scale)
    return canvas


def render_furnace(inp, result, scale):
    unit = scale / 5.0
    w, h = int(round(446 * unit)), int(round(285 * unit))
    canvas = Image.new("RGBA", (w, h), BG)
    draw = ImageDraw.Draw(canvas)
    edge = max(1, int(round(scale)))
    ix, iy, cell = int(round(6 * unit)), int(round(97 * unit)), int(round(90 * unit))
    draw_slot(draw, ix, iy, cell, edge)
    paste_icon(canvas, inp, ix, iy, cell)
    draw_flame(draw, int(round(155 * unit)), int(round(144 * unit)), scale)
    draw_arrow(draw, int(round(195 * unit)), int(round(130 * unit)),
               int(round(280 * unit)), int(round(158 * unit)), scale)
    ox, oy, osz = (int(round(310 * unit)), int(round(79 * unit)),
                   int(round(130 * unit)))
    draw_slot(draw, ox, oy, osz, edge)
    paste_icon(canvas, result[0], ox, oy, osz)
    if result[1] > 1:
        draw_digits(draw, str(result[1]), ox + osz, oy + osz, scale)
    return canvas


def recipe_body(data):
    for key in ("minecraft:recipe_shaped", "minecraft:recipe_shapeless",
                "minecraft:recipe_furnace"):
        if key in data:
            return key, data[key]
    return None, None


def as_result(body):
    res = body.get("result")
    if isinstance(res, list):
        res = res[0] if res else {}
    if not isinstance(res, dict):
        return None, 1
    return res.get("item"), int(res.get("count", 1) or 1)


def build_grid(kind, body):
    grid = [[None] * 3 for _ in range(3)]
    if kind == "minecraft:recipe_shaped":
        key = body.get("key") or {}
        for r, row in enumerate((body.get("pattern") or [])[:3]):
            for c, ch in enumerate(row[:3]):
                if ch in (" ", ""):
                    continue
                if ch in key:
                    grid[r][c] = key[ch]
        return grid
    if kind == "minecraft:recipe_shapeless":
        ings = body.get("ingredients") or []
        if len(ings) == 1:
            grid[1][1] = ings[0]
        else:
            for i, ing in enumerate(ings[:9]):
                grid[i // 3][i % 3] = ing
        return grid
    return grid


def load_recipes():
    out = {}
    for path in sorted(glob.glob(os.path.join(PACK, "netease_recipes", "*.json"))):
        data = load_json(path, {})
        kind, body = recipe_body(data)
        if not kind or not body:
            continue
        ident = ((body.get("description") or {}).get("identifier")
                 or os.path.basename(path)[:-5])
        out[ident] = (path, kind, body)
    return out


def resolve_recipe(name, recipes):
    if name in recipes:
        return name
    short = name.split(":", 1)[-1]
    candidates = [short]
    if short.endswith("_block"):
        candidates.append(short[:-6])
    for candidate in candidates:
        for key in (candidate, "fycq:" + candidate):
            if key in recipes:
                return key
    return None


def main():
    ap = argparse.ArgumentParser(description="生成原版工作台风格的 3x3 配方图")
    ap.add_argument("--recipe", default="", help="配方 ID，可逗号分隔")
    ap.add_argument("--theme", default="", help="按 ID 前缀筛，如 power / me")
    ap.add_argument("--all", action="store_true", help="生成全部配方")
    ap.add_argument("--out", default=os.path.join(ROOT, "docs", "预览", "配方图"))
    ap.add_argument("--scale", type=int, default=5)
    ap.add_argument("--no-count", action="store_true", help="不画产物数量")
    args = ap.parse_args()

    recipes = load_recipes()
    if args.recipe:
        wanted = [x.strip() for x in args.recipe.split(",") if x.strip()]
    elif args.theme:
        theme = args.theme.split(":", 1)[-1]
        wanted = [k for k in recipes if k.split(":", 1)[-1].startswith(theme)]
    elif args.all:
        wanted = list(recipes)
    else:
        ap.error("需要 --recipe / --theme / --all 之一")

    os.makedirs(args.out, exist_ok=True)
    missing = set()
    made = 0
    for ident in wanted:
        resolved = resolve_recipe(ident, recipes)
        if resolved is None:
            print("[skip] recipe not found: %s" % ident)
            continue
        ident = resolved
        path, kind, body = recipes[ident]
        item, count = as_result(body)
        if args.no_count:
            count = 1
        if kind == "minecraft:recipe_furnace":
            inp = body.get("input")
            item = body.get("output") or item
            count = 1
            img = icon_for(inp)
            if img is None:
                missing.add(str(inp))
                img = placeholder()
            res = icon_for(item)
            if res is None:
                missing.add(str(item))
                res = placeholder()
            canvas = render_furnace(img, (res, count), args.scale)
        else:
            grid = build_grid(kind, body)
            res = icon_for(item)
            if res is None:
                missing.add(str(item))
                res = placeholder()
            for r in range(3):
                for c in range(3):
                    if grid[r][c] is None:
                        continue
                    icon = icon_for(grid[r][c])
                    if icon is None:
                        missing.add(str(grid[r][c].get("item")))
                        icon = placeholder()
                    grid[r][c] = icon
            canvas = render_crafting(grid, (res, count), args.scale)
        if args.no_count:
            canvas = canvas
        name = ident.split(":", 1)[-1] + ".png"
        canvas.convert("RGB").save(os.path.join(args.out, name))
        made += 1
        print("[ok] %s -> %s" % (ident, name))

    print("[done] %d images / %d missing icon types" % (made, len(missing)))
    for name in sorted(missing):
        print("[missing] %s" % name)


def placeholder():
    img = Image.new("RGBA", (16, 16), (255, 0, 255, 255))
    draw = ImageDraw.Draw(img)
    for y in range(0, 16, 4):
        for x in range(0, 16, 4):
            if (x // 4 + y // 4) % 2:
                draw.rectangle([x, y, x + 3, y + 3], fill=(0, 0, 0, 255))
    return img


if __name__ == "__main__":
    main()
