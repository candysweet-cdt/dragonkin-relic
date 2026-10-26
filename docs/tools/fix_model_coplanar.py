"""给实体模型里的零厚度方块补一点厚度，消除 z-fighting（材质闪烁）。

零厚度 cube 的正面和背面完全重合，同一个方块自己跟自己抢深度 —— 龙蛇的两翼
三段膜（leftwind/leftwind2/leftwind3 与 rightwind* 各 3 块）都是 size[0]=0。
厚度必须 ≥1 个纹素（1 单位）：0.05 那种亚像素厚度会让边缘面渲染成 1px 细线，
而且边缘面的 UV 落在亚像素上会采到随机颜色（2026-10-27 实机截图确认）。
顺带要把边缘带在贴图上补色（只补「透明且未被其它部件占用」的像素）。

用法：python docs/tools/fix_model_coplanar.py [模型相对路径] [--write]
不带 --write 只报告。
"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DEFAULT = os.path.join(ROOT, 'awesome_resource_packs', 'models', 'entity', 'drasnea.json')
THICK = 1.0


def detect_style(raw):
    crlf = b'\r\n' in raw
    lines = raw.decode('utf-8-sig').split('\n')
    indent = '  '
    for line in lines[1:]:
        if line.strip():
            indent = ' ' * (len(line) - len(line.lstrip(' ')))
            break
    return indent, crlf


def main():
    args = [a for a in sys.argv[1:] if a != '--write']
    write = '--write' in sys.argv
    path = args[0] if args else DEFAULT
    raw = open(path, 'rb').read()
    indent, crlf = detect_style(raw)
    d = json.loads(raw.decode('utf-8-sig'))
    key = 'geometry.drasnea' if 'geometry.drasnea' in d else 'minecraft:geometry'
    g = d[key] if key == 'geometry.drasnea' else d[key][0]

    fixed = []
    for b in g['bones']:
        for c in b.get('cubes', []):
            for axis, v in enumerate(c['size']):
                if abs(v) < 1e-6:
                    c['size'][axis] = THICK
                    c['origin'][axis] = round(c['origin'][axis] - THICK / 2.0, 6)
                    fixed.append((b['name'], 'XYZ'[axis], c['origin'], c['size']))
                    break
    print(f'零厚度方块: {len(fixed)} 个')
    for name, axis, o, s in fixed:
        print(f'  {name:12s} axis={axis} -> origin={o} size={s}')

    if not write:
        print('（只报告，未写入；加 --write 生效）')
        return
    out = json.dumps(d, ensure_ascii=False, indent=indent)
    if crlf:
        out = out.replace('\n', '\r\n')
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(out + ('\r\n' if crlf else '\n'))
    print('已写入', path)


if __name__ == '__main__':
    main()
