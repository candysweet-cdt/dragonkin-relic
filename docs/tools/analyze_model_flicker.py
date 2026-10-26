"""实体模型共面检测：找出同向共面且投影重叠的面（z-fighting / 材质闪烁的根因）。

做法：把每个 cube 的 6 个面按骨骼链（T(pivot)·R·T(-pivot)）变换到模型空间，
按「法线 + 平面偏移」分桶，桶内做 2D 投影重叠面积判定。

用法：python docs/tools/analyze_model_flicker.py [模型相对路径]
"""
import json
import math
import os
import sys
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DEFAULT = os.path.join(ROOT, 'awesome_resource_packs', 'models', 'entity', 'drasnea.json')
EPS = 1e-4          # 平面/法线判定容差（模型单位 = 1/16 格）
AREA_MIN = 0.02     # 忽略小于此投影面积的重叠（贴边接触不算）


def mat_mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def apply(m, v):
    x, y, z = v
    return [m[i][0] * x + m[i][1] * y + m[i][2] * z + m[i][3] for i in range(3)]


def bone_matrix(rot, pivot):
    px, py, pz = pivot
    rx, ry, rz = [math.radians(v) for v in rot]
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    Rx = [[1, 0, 0], [0, cx, -sx], [0, sx, cx]]
    Ry = [[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]
    Rz = [[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]
    R = [[sum(Rz[i][k] * Ry[k][1] * 0 for k in range(3)) for j in range(3)] for i in range(3)] if False else None
    # R = Rz @ Ry @ Rx
    def mm3(a, b):
        return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    R = mm3(Rz, mm3(Ry, Rx))
    T = [[1, 0, 0, px], [0, 1, 0, py], [0, 0, 1, pz], [0, 0, 0, 1]]
    Ti = [[1, 0, 0, -px], [0, 1, 0, -py], [0, 0, 1, -pz], [0, 0, 0, 1]]
    M4 = [[R[i][0], R[i][1], R[i][2], 0] for i in range(3)] + [[0, 0, 0, 1]]
    return mat_mul(mat_mul(T, M4), Ti)


def load(path):
    d = json.load(open(path, encoding='utf-8-sig'))
    g = d['geometry.drasnea'] if 'geometry.drasnea' in d else d['minecraft:geometry'][0]
    return g


def walk(bones, name, parent_m, out, by_name):
    b = by_name[name]
    M = mat_mul(parent_m, bone_matrix(b.get('rotation', [0, 0, 0]), b.get('pivot', [0, 0, 0])))
    for c in b.get('cubes', []):
        o, s = c['origin'], c['size']
        inf = c.get('inflate', 0)
        inf = [inf] * 3 if isinstance(inf, (int, float)) else inf
        lo = [min(o[i], o[i] + s[i]) - inf[i] for i in range(3)]
        hi = [max(o[i], o[i] + s[i]) + inf[i] for i in range(3)]
        corners = []
        for i in range(8):
            p = [lo[0] if i & 1 else hi[0], lo[1] if i & 2 else hi[1], lo[2] if i & 4 else hi[2]]
            corners.append(apply(M, p))
        out.append({'bone': name, 'origin': o, 'size': s, 'inflate': inf,
                    'corners': corners, 'mirror': bool(c.get('mirror')),
                    'uv': c.get('uv')})
    for ch in children.get(name, []):
        walk(bones, ch, M, out, by_name)


children = {}
EPS_FACE = 0.02


def faces_of(cube):
    c = cube['corners']
    # 8 顶点索引：bit0=x, bit1=y, bit2=z
    idx = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    normals = [(-1, 0, 0), (1, 0, 0), (0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1)]
    out = []
    for (i0, i1, i2, i3), n in zip(idx, normals):
        pts = [c[i0], c[i1], c[i2], c[i3]]
        off = sum(n[k] * pts[0][k] for k in range(3))
        out.append({'n': n, 'off': off, 'pts': pts})
    return out


def proj_overlap_area(f1, f2):
    """两共面凸四边形求交面积（Sutherland–Hodgman 裁剪）。

    AABB 近似会把斜置的大片误判成重叠，必须用真求交。
    """
    n = f1['n']
    ax = [abs(v) for v in n]
    t = [0, 1, 2][ax.index(min(ax))]
    e1 = [0.0, 0.0, 0.0]
    e1[t] = 1.0
    dot = sum(e1[k] * n[k] for k in range(3))
    e1 = [e1[k] - dot * n[k] for k in range(3)]
    ln = math.sqrt(sum(v * v for v in e1)) or 1.0
    e1 = [v / ln for v in e1]
    e2 = [n[1] * e1[2] - n[2] * e1[1], n[2] * e1[0] - n[0] * e1[2], n[0] * e1[1] - n[1] * e1[0]]

    def proj(pts):
        return [(sum(p[k] * e1[k] for k in range(3)), sum(p[k] * e2[k] for k in range(3)))
                for p in pts]

    subject = proj(f1['pts'])
    clip = proj(f2['pts'])
    # 保证裁剪多边形为逆时针
    def signed_area(poly):
        return 0.5 * sum(poly[i][0] * poly[(i + 1) % len(poly)][1] -
                         poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))
    if signed_area(clip) < 0:
        clip = clip[::-1]

    def inside(p, a, b):
        return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= -1e-9

    def intersect(p, q, a, b):
        x1, y1, x2, y2 = p[0], p[1], q[0], q[1]
        x3, y3, x4, y4 = a[0], a[1], b[0], b[1]
        den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(den) < 1e-12:
            return q
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))

    out = subject
    for i in range(len(clip)):
        a, b = clip[i], clip[(i + 1) % len(clip)]
        if not out:
            return 0.0
        new = []
        for j in range(len(out)):
            cur, prv = out[j], out[j - 1]
            if inside(cur, a, b):
                if not inside(prv, a, b):
                    new.append(intersect(prv, cur, a, b))
                new.append(cur)
            elif inside(prv, a, b):
                new.append(intersect(prv, cur, a, b))
        out = new
    return abs(signed_area(out)) if len(out) >= 3 else 0.0


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    g = load(path)
    bones = g['bones']
    by_name = {b['name']: b for b in bones}
    for b in bones:
        children.setdefault(b.get('parent'), []).append(b['name'])
    ident = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    cubes = []
    for root in children.get(None, []):
        walk(bones, root, ident, cubes, by_name)
    print(f'模型 {os.path.basename(path)}：骨骼 {len(bones)} / 方块 {len(cubes)}')

    buckets = defaultdict(list)
    for ci, cube in enumerate(cubes):
        for f in faces_of(cube):
            key = (tuple(round(v, 3) for v in f['n']), round(f['off'], 2))
            buckets[key].append((ci, f))

    pairs = []
    for key, items in buckets.items():
        if len(items) < 2:
            continue
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                ci, f1 = items[i]
                cj, f2 = items[j]
                if ci == cj:
                    continue
                a = proj_overlap_area(f1, f2)
                if a >= AREA_MIN:
                    pairs.append((a, cubes[ci]['bone'], cubes[cj]['bone'],
                                  cubes[ci]['origin'], cubes[cj]['origin'],
                                  cubes[ci]['inflate'], cubes[cj]['inflate'],
                                  cubes[ci]['mirror'], cubes[cj]['mirror'], key[0]))
    pairs.sort(reverse=True)
    print(f'同向共面且投影重叠的面对：{len(pairs)}')
    by_bone = defaultdict(int)
    for p in pairs:
        by_bone[p[1]] += 1
        by_bone[p[2]] += 1
    print('按骨骼聚合（前 12）：')
    for bone, n in sorted(by_bone.items(), key=lambda kv: -kv[1])[:12]:
        print(f'  {bone:12s} {n} 处')
    print('\n面积最大的 10 对：')
    for a, b1, b2, o1, o2, i1, i2, m1, m2, n in pairs[:10]:
        print(f'  面积 {a:7.2f}  {b1}/{b2}  origin {o1}~{o2}  inflate {i1}~{i2}  mirror {m1}/{m2}')


if __name__ == '__main__':
    main()
