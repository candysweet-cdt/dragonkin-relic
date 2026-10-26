"""波3（龙裔）三只生物的几何体、贴图、动画与实体定义。

  · dragon_whelp  幼龙   —— 小型飞龙，近战，掉龙鳞
  · dragon_priest 龙祭司 —— 人形施法者，火球远程，掉龙血结晶
  · dragon_guard  龙卫   —— 重甲近战精英，掉龙牙与龙鳞

每只的骨盒数据是逐个手写的（不是同一模板批量套壳）；UV 由装箱器统一分配，
模型与贴图共用同一份 uv，从根上避免贴图错位。贴图按面光照（顶亮底暗）
叠加鳞纹与 1px 描边，保证低模也有体积感。
"""
import json
import math
import os
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BP = os.path.join(ROOT, 'awesome_behavior_packs')
RP = os.path.join(ROOT, 'awesome_resource_packs')

BASE = {
    'scale': (46, 139, 126),      # 龙鳞青
    'scale_d': (24, 74, 67),      # 暗鳞
    'scale_l': (96, 200, 174),    # 亮鳞
    'belly': (168, 234, 212),
    'gold': (201, 162, 39),
    'gold_l': (246, 220, 130),
    'bone': (214, 208, 180),
    'robe': (72, 40, 86),
    'robe_l': (112, 66, 128),
    'hood': (26, 22, 34),
    'iron': (104, 112, 120),
    'iron_d': (62, 68, 74),
    'wood': (94, 66, 41),
    'eye': (252, 224, 120),
    'maw': (122, 18, 32),
}

FACE_FACTOR = {'top': 1.16, 'bottom': 0.70, 'ns': 0.94, 'ew': 1.06}


def cube_face_rects(u, v, w, h, d):
    """Bedrock 立方体展开的六个面矩形（与官方 unwrap 一致）。"""
    return {
        'top': (u + d, v, w, d),
        'bottom': (u + d + w, v, w, d),
        'right': (u, v + d, d, h),
        'front': (u + d, v + d, w, h),
        'left': (u + d + w, v + d, d, h),
        'back': (u + d + w + d, v + d, w, h),
    }


def pack_uvs(bones, tex_w):
    """按出现顺序给每个立方体分配不重叠的 uv，返回占用高度。"""
    x = y = 0
    shelf = 0
    for b in bones:
        for c in b.get('cubes', []):
            w, h, d = c['size']
            rw, rh = 4 * d + 2 * w, d + h
            if x + rw > tex_w:
                x = 0
                y += shelf + 1
                shelf = 0
            c['uv'] = [x, y]
            x += rw + 1
            shelf = max(shelf, rh)
    return y + shelf


def paint(bones, tex_w, tex_h, scale_pattern=True):
    im = Image.new('RGBA', (tex_w, tex_h), (0, 0, 0, 0))
    px = im.load()
    for b in bones:
        for c in b.get('cubes', []):
            w, h, d = c['size']
            u, v = c['uv']
            mats = c['mat']
            for face, (rx, ry, rw, rh) in cube_face_rects(u, v, w, h, d).items():
                key = {'top': 'top', 'bottom': 'bottom'}.get(face, 'side')
                base = mats.get(key, mats.get('all', BASE['scale']))
                f = FACE_FACTOR['top' if face == 'top' else 'bottom' if face == 'bottom'
                                else 'ns' if face in ('front', 'back') else 'ew']
                for yy in range(rh):
                    for xx in range(rw):
                        col = tuple(min(255, int(ch * f)) for ch in base)
                        if scale_pattern and (xx + (yy // 2) * 2) % 5 == 0:
                            col = tuple(max(0, int(ch * 0.82)) for ch in col)
                        if xx == 0 or yy == 0 or xx == rw - 1 or yy == rh - 1:
                            col = tuple(max(0, int(ch * 0.55)) for ch in col)
                        px[rx + xx, ry + yy] = col + (255,)
    return im


def geometry(name, bones, tex_w, tex_h, vb=(2, 3, 2)):
    out = []
    for b in bones:
        node = {'name': b['name'], 'pivot': b['pivot'],
                'cubes': [{'origin': c['origin'], 'size': c['size'], 'uv': c['uv'],
                           **({'inflate': c['inflate']} if 'inflate' in c else {})}
                          for c in b.get('cubes', [])]}
        if b.get('parent'):
            node['parent'] = b['parent']
        if b.get('rotation'):
            node['rotation'] = b['rotation']
        out.append(node)
    return {
        'format_version': '1.12.0',
        'minecraft:geometry': [{
            'description': {
                'identifier': f'geometry.{name}',
                'texture_width': tex_w, 'texture_height': tex_h,
                'visible_bounds_width': vb[0], 'visible_bounds_height': vb[1],
                'visible_bounds_offset': [0, 1, 0],
            },
            'bones': out,
        }],
    }


# ---------------------------------------------------------------- 幼龙
def whelp_bones():
    return [
        {'name': 'root', 'pivot': [0, 0, 0]},
        {'name': 'body', 'parent': 'root', 'pivot': [0, 11, 0], 'cubes': [
            {'origin': [-3, 9, -6], 'size': [6, 5, 12],
             'mat': {'top': BASE['scale'], 'side': BASE['scale'], 'bottom': BASE['belly']}}]},
        {'name': 'neck', 'parent': 'body', 'pivot': [0, 12, -6], 'cubes': [
            {'origin': [-1.5, 11, -9], 'size': [3, 3, 4], 'mat': {'all': BASE['scale_d']}}]},
        {'name': 'head', 'parent': 'neck', 'pivot': [0, 13, -9], 'cubes': [
            {'origin': [-2.5, 11, -13], 'size': [5, 4.5, 4.5], 'mat': {'all': BASE['scale']}},
            {'origin': [-1.5, 11, -16], 'size': [3, 2.5, 3.5],
             'mat': {'top': BASE['scale_l'], 'side': BASE['scale'], 'bottom': BASE['maw']}},
            {'origin': [-2.2, 14, -12.5], 'size': [1.2, 2.2, 1.2], 'mat': {'all': BASE['gold']}},
            {'origin': [1.0, 14, -12.5], 'size': [1.2, 2.2, 1.2], 'mat': {'all': BASE['gold']}},
            {'origin': [-2.6, 13.2, -12.2], 'size': [1, 1, 0.6], 'mat': {'all': BASE['eye']}},
            {'origin': [1.6, 13.2, -12.2], 'size': [1, 1, 0.6], 'mat': {'all': BASE['eye']}}]},
        {'name': 'jaw', 'parent': 'head', 'pivot': [0, 11, -13], 'cubes': [
            {'origin': [-1.2, 10, -15.5], 'size': [2.4, 1, 3], 'mat': {'all': BASE['maw']}}]},
        {'name': 'tail', 'parent': 'body', 'pivot': [0, 11.5, 6], 'cubes': [
            {'origin': [-1.6, 10, 6], 'size': [3.2, 3, 6], 'mat': {'all': BASE['scale']}}]},
        {'name': 'tail2', 'parent': 'tail', 'pivot': [0, 11.5, 12], 'cubes': [
            {'origin': [-1.1, 10.4, 12], 'size': [2.2, 2.2, 6], 'mat': {'all': BASE['scale_d']}}]},
        {'name': 'tail3', 'parent': 'tail2', 'pivot': [0, 11.5, 18], 'cubes': [
            {'origin': [-0.6, 10.9, 18], 'size': [1.2, 1.2, 5], 'mat': {'all': BASE['gold']}}]},
        {'name': 'wingL', 'parent': 'body', 'pivot': [2.5, 14, -2], 'cubes': [
            {'origin': [2.5, 13.5, -5], 'size': [9, 0.8, 8],
             'mat': {'top': BASE['gold'], 'side': BASE['scale_d'], 'bottom': BASE['gold_l']}},
            {'origin': [2.5, 14.5, -4], 'size': [9, 1, 1.2], 'mat': {'all': BASE['scale']}}]},
        {'name': 'wingR', 'parent': 'body', 'pivot': [-2.5, 14, -2], 'cubes': [
            {'origin': [-11.5, 13.5, -5], 'size': [9, 0.8, 8],
             'mat': {'top': BASE['gold'], 'side': BASE['scale_d'], 'bottom': BASE['gold_l']}},
            {'origin': [-11.5, 14.5, -4], 'size': [9, 1, 1.2], 'mat': {'all': BASE['scale']}}]},
        {'name': 'legFL', 'parent': 'body', 'pivot': [2, 9, -4], 'cubes': [
            {'origin': [1, 5, -4.8], 'size': [2, 4.5, 2.4], 'mat': {'all': BASE['scale_d']}}]},
        {'name': 'legFR', 'parent': 'body', 'pivot': [-2, 9, -4], 'cubes': [
            {'origin': [-3, 5, -4.8], 'size': [2, 4.5, 2.4], 'mat': {'all': BASE['scale_d']}}]},
        {'name': 'legBL', 'parent': 'body', 'pivot': [2, 9, 3], 'cubes': [
            {'origin': [1, 5, 2.2], 'size': [2, 4.5, 2.4], 'mat': {'all': BASE['scale_d']}}]},
        {'name': 'legBR', 'parent': 'body', 'pivot': [-2, 9, 3], 'cubes': [
            {'origin': [-3, 5, 2.2], 'size': [2, 4.5, 2.4], 'mat': {'all': BASE['scale_d']}}]},
    ]


# ---------------------------------------------------------------- 龙祭司
def priest_bones():
    return [
        {'name': 'root', 'pivot': [0, 0, 0]},
        {'name': 'body', 'parent': 'root', 'pivot': [0, 12, 0], 'cubes': [
            {'origin': [-4, 6, -2], 'size': [8, 12, 4],
             'mat': {'top': BASE['robe_l'], 'side': BASE['robe'], 'bottom': BASE['hood']}},
            {'origin': [-4.4, 15.5, -2.4], 'size': [8.8, 2.5, 4.8],
             'mat': {'all': BASE['gold']}}]},
        {'name': 'head', 'parent': 'body', 'pivot': [0, 18, 0], 'cubes': [
            {'origin': [-4, 18, -4], 'size': [8, 8, 8], 'mat': {'all': BASE['hood']}},
            {'origin': [-4.2, 24, -4.2], 'size': [8.4, 2.4, 8.4], 'mat': {'all': BASE['robe']}},
            {'origin': [-0.6, 25.6, -0.6], 'size': [1.2, 2.4, 1.2], 'mat': {'all': BASE['gold']}},
            {'origin': [-3, 21, -4.4], 'size': [2, 1.4, 0.6], 'mat': {'all': BASE['eye']}},
            {'origin': [1, 21, -4.4], 'size': [2, 1.4, 0.6], 'mat': {'all': BASE['eye']}}]},
        {'name': 'armL', 'parent': 'body', 'pivot': [5, 16, 0], 'cubes': [
            {'origin': [4, 6, -2], 'size': [4, 12, 4], 'mat': {'all': BASE['robe']}}]},
        {'name': 'armR', 'parent': 'body', 'pivot': [-5, 16, 0], 'cubes': [
            {'origin': [-8, 6, -2], 'size': [4, 12, 4], 'mat': {'all': BASE['robe']}}]},
        {'name': 'staff', 'parent': 'armR', 'pivot': [-6, 6, 0], 'cubes': [
            {'origin': [-6.6, 2, -0.6], 'size': [1.2, 20, 1.2], 'mat': {'all': BASE['wood']}},
            {'origin': [-7.4, 21.5, -1.4], 'size': [2.8, 2.8, 2.8], 'mat': {'all': BASE['gold']}},
            {'origin': [-7, 20, -1], 'size': [2, 2, 2], 'mat': {'all': BASE['maw']}}]},
        {'name': 'legL', 'parent': 'root', 'pivot': [2, 6, 0], 'cubes': [
            {'origin': [0.5, 0, -2], 'size': [3.5, 6.5, 4], 'mat': {'all': BASE['robe']}}]},
        {'name': 'legR', 'parent': 'root', 'pivot': [-2, 6, 0], 'cubes': [
            {'origin': [-4, 0, -2], 'size': [3.5, 6.5, 4], 'mat': {'all': BASE['robe']}}]},
    ]


# ---------------------------------------------------------------- 龙卫
def guard_bones():
    return [
        {'name': 'root', 'pivot': [0, 0, 0]},
        {'name': 'body', 'parent': 'root', 'pivot': [0, 13, 0], 'cubes': [
            {'origin': [-5, 7, -2.5], 'size': [10, 13, 5],
             'mat': {'top': BASE['scale_l'], 'side': BASE['scale'], 'bottom': BASE['scale_d']}},
            {'origin': [-5.4, 12, -2.9], 'size': [10.8, 3, 5.8], 'mat': {'all': BASE['gold']}}]},
        {'name': 'head', 'parent': 'body', 'pivot': [0, 20, 0], 'cubes': [
            {'origin': [-4, 20, -4], 'size': [8, 8, 8], 'mat': {'all': BASE['iron']}},
            {'origin': [-4.3, 25.5, -4.3], 'size': [8.6, 2.6, 8.6], 'mat': {'all': BASE['scale']}},
            {'origin': [-0.7, 27.5, -0.7], 'size': [1.4, 2.6, 1.4], 'mat': {'all': BASE['gold']}},
            {'origin': [-2.6, 23, -4.4], 'size': [1.6, 1.2, 0.6], 'mat': {'all': BASE['eye']}},
            {'origin': [1.0, 23, -4.4], 'size': [1.6, 1.2, 0.6], 'mat': {'all': BASE['eye']}}]},
        {'name': 'padL', 'parent': 'body', 'pivot': [5.5, 18.5, 0], 'cubes': [
            {'origin': [5, 15, -3.2], 'size': [3.2, 5, 6.4], 'mat': {'all': BASE['scale_l']}}]},
        {'name': 'padR', 'parent': 'body', 'pivot': [-5.5, 18.5, 0], 'cubes': [
            {'origin': [-8.2, 15, -3.2], 'size': [3.2, 5, 6.4], 'mat': {'all': BASE['scale_l']}}]},
        {'name': 'armL', 'parent': 'body', 'pivot': [6, 15, 0], 'cubes': [
            {'origin': [4.5, 3, -2.2], 'size': [4.4, 12.5, 4.4], 'mat': {'all': BASE['iron_d']}}]},
        {'name': 'armR', 'parent': 'body', 'pivot': [-6, 15, 0], 'cubes': [
            {'origin': [-8.9, 3, -2.2], 'size': [4.4, 12.5, 4.4], 'mat': {'all': BASE['iron_d']}}]},
        {'name': 'legL', 'parent': 'root', 'pivot': [2.4, 7, 0], 'cubes': [
            {'origin': [0.4, 0, -2.4], 'size': [4, 7.5, 4.8], 'mat': {'all': BASE['scale_d']}}]},
        {'name': 'legR', 'parent': 'root', 'pivot': [-2.4, 7, 0], 'cubes': [
            {'origin': [-4.4, 0, -2.4], 'size': [4, 7.5, 4.8], 'mat': {'all': BASE['scale_d']}}]},
    ]


MOBS = {
    'dragon_whelp': {
        'cn': '幼龙', 'bones': whelp_bones, 'tex': 64, 'vb': (2, 2, 2),
        'anim': {'bob': 0.9, 'flap': True, 'tail': ['tail', 'tail2', 'tail3'], 'len': 1.6},
        'beh': {
            'health': 30, 'movement': 0.28, 'damage': 4, 'kb': 0.1, 'box': (0.9, 1.1),
            'family': ['dragonkin', 'monster', 'mob', 'fycq'],
            'loot': [{'item': 'dragon_scale', 'min': 1, 'max': 2, 'loot_min': 0, 'loot_max': 1},
                     {'item': 'dragon_fang', 'min': 1, 'max': 1, 'chance': 0.15, 'loot_mult': 0.01}],
            'xp': 12, 'aggro': 12, 'fly': True,
            'skills': [],
            'sounds': {'roar': 'mob.ghast.warn', 'attack': 'mob.ghast.scream',
                       'hurt': 'mob.ghast.hurt', 'death': 'mob.ghast.death',
                       'flap': 'mob.enderdragon.flap'},
        },
    },
    'dragon_priest': {
        'cn': '龙祭司', 'bones': priest_bones, 'tex': 64, 'vb': (2, 3, 2),
        'anim': {'bob': 0.35, 'flap': False, 'tail': [], 'len': 2.0, 'arm': ['armR', 'staff']},
        'beh': {
            'health': 60, 'movement': 0.24, 'damage': 5, 'kb': 0.3, 'box': (0.7, 1.9),
            'family': ['dragonkin', 'monster', 'mob', 'fycq'],
            'loot': [{'item': 'dragon_scale', 'min': 1, 'max': 3, 'loot_min': 0, 'loot_max': 1},
                     {'item': 'dragon_blood_crystal', 'min': 1, 'max': 1, 'player_only': True},
                     {'item': 'dragon_heart', 'min': 1, 'max': 1, 'chance': 0.05,
                      'loot_mult': 0.005, 'player_only': True}],
            'xp': 40, 'ranged': True, 'aggro': 20,
            'skills': [{'type': 'summon_entity', 'priority': 2, 'entity': 'fycq:dragon_whelp',
                        'count': 1, 'cooldown': 16.0, 'cast': 1.2, 'max_range': 10.0}],
            'sounds': {'roar': 'mob.blaze.breathe', 'attack': 'mob.blaze.breathe',
                       'cast': 'mob.ghast.fireball', 'hurt': 'mob.blaze.hurt',
                       'death': 'mob.blaze.death'},
        },
    },
    'dragon_guard': {
        'cn': '龙卫', 'bones': guard_bones, 'tex': 64, 'vb': (3, 3, 2),
        'anim': {'bob': 0.25, 'flap': False, 'tail': [], 'len': 1.8, 'arm': ['armL', 'armR']},
        'beh': {
            'health': 120, 'movement': 0.26, 'damage': 9, 'kb': 0.6, 'box': (1.0, 2.1),
            'family': ['dragonkin', 'monster', 'mob', 'fycq'],
            'loot': [{'item': 'dragon_fang', 'min': 1, 'max': 3, 'loot_min': 0, 'loot_max': 1},
                     {'item': 'dragon_scale', 'min': 2, 'max': 4, 'loot_min': 0, 'loot_max': 2},
                     {'item': 'dragon_blood_crystal', 'min': 1, 'max': 1, 'chance': 0.12,
                      'loot_mult': 0.01}],
            'xp': 80, 'aggro': 16,
            'skills': [{'type': 'knockback_roar', 'priority': 2, 'duration': 1.0,
                        'attack_time': 0.4, 'damage': 6, 'strength': 3, 'range': 5.0,
                        'cooldown': 9.0},
                       {'type': 'area_attack', 'priority': 6, 'damage_per_tick': 1,
                        'range': 1.8}],
            'sounds': {'roar': 'mob.ghast.moan', 'attack': 'mob.iron_golem.attack',
                       'hurt': 'mob.iron_golem.hurt', 'death': 'mob.iron_golem.death'},
        },
    },
}


def build_animations(stem, spec):
    """idle / move / death。关键帧必须铺满 animation_length，否则播完卡在最后一帧。"""
    a = spec['anim']
    L = a['len']
    bones = {b['name'] for b in spec['bones']()}
    anims = {}

    def keys(points):
        """points: [(t, [x,y,z]), ...] -> Bedrock 关键帧字典"""
        return {f'{round(t, 4)}': v for t, v in points}

    # ---- idle：慢呼吸 + 尾摆 +（幼龙）扇翅 +（人形）手臂轻晃
    idle_bones = {'body': {'rotation': keys([
        (0.0, [0, 0, 0]), (L / 2, [a['bob'], 0, 0]), (L, [0, 0, 0])])}}
    for i, t in enumerate(a['tail']):
        amp = 6 + 4 * i
        idle_bones[t] = {'rotation': keys([
            (0.0, [0, 0, 0]), (L * 0.3, [0, amp * 0.5, 0]),
            (L * 0.7, [0, -amp * 0.5, 0]), (L, [0, 0, 0])])}
    if a.get('flap'):
        idle_bones['wingL'] = {'rotation': keys([
            (0.0, [0, 0, 14]), (L / 2, [0, 0, -22]), (L, [0, 0, 14])])}
        idle_bones['wingR'] = {'rotation': keys([
            (0.0, [0, 0, -14]), (L / 2, [0, 0, 22]), (L, [0, 0, -14])])}
    for arm, sign in (('armL', -1), ('armR', 1)):
        if arm in bones:
            idle_bones[arm] = {'rotation': keys([
                (0.0, [0, 0, 0]), (L / 2, [4 * sign, 0, 0]), (L, [0, 0, 0])])}
    anims[f'animation.{stem}.idle'] = {
        'loop': True, 'animation_length': L, 'bones': idle_bones}

    # ---- move：腿摆 + 身体起伏 +（幼龙）快速扇翅；关键帧铺满整个循环
    M = round(L / 2.0, 4)
    q = [0.0, M / 4, M / 2, M * 3 / 4, M]
    move_bones = {'body': {'rotation': keys([
        (q[0], [0, 0, 0]), (q[1], [a['bob'] * 1.8, 0, 0]),
        (q[2], [0, 0, 0]), (q[3], [a['bob'] * 1.8, 0, 0]), (q[4], [0, 0, 0])])}}
    legs = [n for n in ('legL', 'legR', 'legFL', 'legFR', 'legBL', 'legBR') if n in bones]
    for i, leg in enumerate(legs):
        ph = 0.25 if i % 2 else 0.0          # 对角步态
        swing = [(q[0], [0, 0, 0]),
                 (round(q[1] + ph * M / 4, 4), [26, 0, 0]),
                 (q[2], [0, 0, 0]),
                 (round(q[3] + ph * M / 4, 4), [-26, 0, 0]),
                 (q[4], [0, 0, 0])]
        move_bones[leg] = {'rotation': keys(swing)}
    if a.get('flap'):
        move_bones['wingL'] = {'rotation': keys([
            (q[0], [0, 0, 30]), (q[2], [0, 0, -34]), (q[4], [0, 0, 30])])}
        move_bones['wingR'] = {'rotation': keys([
            (q[0], [0, 0, -30]), (q[2], [0, 0, 34]), (q[4], [0, 0, -30])])}
    for i, t in enumerate(a['tail']):
        amp = 5 + 3 * i
        move_bones[t] = {'rotation': keys([
            (q[0], [0, 0, 0]), (q[2], [0, amp, 0]), (q[4], [0, 0, 0])])}
    anims[f'animation.{stem}.move'] = {
        'loop': True, 'animation_length': M, 'bones': move_bones}

    # ---- death：侧倒 + 下沉，一次性
    anims[f'animation.{stem}.death'] = {
        'loop': False, 'animation_length': 1.2, 'bones': {
            'root': {'rotation': {'0.0': [0, 0, 0], '0.45': [0, 0, 32], '1.2': [0, 0, 82]},
                     'position': {'0.0': [0, 0, 0], '1.2': [0, -3, 0]}},
            'body': {'rotation': {'0.0': [0, 0, 0], '1.2': [12, 0, 0]}}}}

    # ---- attack：蓄力 → 出击 → 回位（由延迟攻击的 is_delayed_attacking 驱动）
    # 幼龙咬击 / 人形挥臂（有 armR+staff 的祭司用持杖手）
    atk_bone = 'armR' if 'staff' in bones else ('armR' if 'armR' in bones else 'head')
    atk = {'body': {'rotation': keys([
        (0.0, [0, 0, 0]), (0.18, [-10, 0, 0]), (0.32, [8, 0, 0]), (0.5, [0, 0, 0])])},
        atk_bone: {'rotation': keys([
            (0.0, [0, 0, 0]), (0.18, [-55, 0, 0]), (0.32, [35, 0, 0]), (0.5, [0, 0, 0])])}}
    if 'jaw' in bones:
        atk['jaw'] = {'rotation': keys([
            (0.0, [0, 0, 0]), (0.18, [0, 0, 0]), (0.32, [28, 0, 0]), (0.5, [0, 0, 0])])}
    anims[f'animation.{stem}.attack'] = {
        'loop': False, 'animation_length': 0.5, 'bones': atk,
        'sound_effects': {'0.3': {'effect': 'attack'}}}

    # ---- hurt：短促后仰（由 is_sheared 标记驱动 0.45s）
    anims[f'animation.{stem}.hurt'] = {
        'loop': False, 'animation_length': 0.45, 'bones': {
            'body': {'rotation': keys([
                (0.0, [0, 0, 0]), (0.12, [-16, 0, 6]), (0.45, [0, 0, 0])])}}}

    return anims


def dump(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, ensure_ascii=False, indent=4)
        f.write('\n')


def build_loot(stem, beh):
    from ids import fid
    pools = []
    for e in beh['loot']:
        funcs = [{'function': 'set_count', 'count': {'min': e['min'], 'max': e['max']}}]
        if e.get('loot_max'):
            funcs.append({'function': 'looting_enchant',
                          'count': {'min': e.get('loot_min', 0), 'max': e['loot_max']}})
        pool = {'rolls': 1, 'entries': [{'type': 'item', 'name': fid(e['item']),
                                         'weight': 1, 'functions': funcs}]}
        conds = []
        if e.get('chance') is not None:
            conds.append({'condition': 'random_chance_with_looting',
                          'chance': e['chance'],
                          'looting_multiplier': e.get('loot_mult', 0.0)})
        if e.get('player_only'):
            conds.append({'condition': 'killed_by_player'})
        if conds:
            pool['conditions'] = conds
        pools.append(pool)
    return {'pools': pools}


def build_beh(stem, spec):
    b = spec['beh']
    comps = {
        'minecraft:experience_reward': {'on_death': f"query.last_hit_by_player ? {b['xp']} : 0"},
        'minecraft:nameable': {},
        'minecraft:type_family': {'family': b['family']},
        'minecraft:loot': {'table': f'loot_tables/fycq/{stem}.json'},
        'minecraft:health': {'value': b['health'], 'max': b['health']},
        'minecraft:attack': {'damage': b['damage']},
        'minecraft:collision_box': {'width': b['box'][0], 'height': b['box'][1]},
        'minecraft:movement': {'value': b['movement']},
        'minecraft:knockback_resistance': {'value': b['kb']},
        'minecraft:physics': {'has_gravity': True, 'has_collision': True},
        'minecraft:pushable': {'is_pushable': True, 'is_pushable_by_piston': False},
        'minecraft:breathable': {'total_supply': 30, 'suffocate_time': 0},
        'minecraft:navigation.walk': {'can_path_over_water': True, 'avoid_water': False},
        'minecraft:movement.basic': {},
        'minecraft:jump.static': {},
        'minecraft:behavior.float': {'priority': 0},
        # 不写 hurt_by_target：龙息云/咆哮擦到同族时会立刻反击，引发内讧；
        # 玩家目标由下面的 nearest_attackable_target 负责。
        # 仇恨范围：必须看得见（must_see）+ 有限距离，避免隔墙全图追人
        'minecraft:behavior.nearest_attackable_target': {
            'priority': 2, 'must_see': True, 'reselect_targets': True,
            'entity_types': [{'filters': {'test': 'is_family', 'subject': 'other',
                                          'value': 'player'},
                              'max_dist': b.get('aggro', 16)}]},
        # 近战改用延迟攻击：蓄力→出击，配合 query.is_delayed_attacking 驱动攻击动画
        'minecraft:behavior.delayed_attack': {
            'priority': 5 if b.get('ranged') else 3,
            'reach_multiplier': 2.0, 'attack_duration': 0.5,
            'hit_delay_pct': 0.6, 'track_target': True, 'sound_event': 'attack.strong'},
        'minecraft:behavior.random_stroll': {'priority': 7, 'xz_dist': 10, 'y_dist': 3,
                                             'speed_multiplier': 0.7},
        'minecraft:behavior.look_at_player': {'priority': 8, 'look_distance': 8.0,
                                              'probability': 0.05},
        'minecraft:behavior.random_look_around': {'priority': 9},
        'minecraft:ambient_sound_interval': {'value': 12.0, 'range': 12.0,
                                             'event_name': 'ambient'},
        # 自然刷出来的怪要能按距离消失，避免越积越多
        'minecraft:despawn': {'despawn_from_distance': {}},
    }
    if b.get('fly'):
        # 幼龙真飞：照蜜蜂/悦灵用 hover 导航 + 无重力，关掉走路导航与扑咬
        comps['minecraft:physics'] = {'has_gravity': False, 'has_collision': True}
        for key in ('minecraft:navigation.walk', 'minecraft:movement.basic',
                    'minecraft:behavior.random_stroll'):
            comps.pop(key, None)
        comps['minecraft:navigation.hover'] = {
            'can_path_over_water': True, 'can_sink': False, 'can_pass_doors': False,
            'can_path_from_air': True, 'avoid_water': True,
            'avoid_damage_blocks': True, 'avoid_sun': False}
        comps['minecraft:movement.hover'] = {}
        comps['minecraft:can_fly'] = {}
        comps['minecraft:behavior.random_hover'] = {
            'priority': 7, 'xz_dist': 8, 'y_dist': 8, 'y_offset': -1,
            'interval': 1, 'hover_height': [1, 4]}
    if b.get('ranged'):
        comps['minecraft:shooter'] = {'def': 'minecraft:fireball'}
        comps['minecraft:behavior.ranged_attack'] = {
            'priority': 3, 'burst_shoot_count': 1, 'burst_interval': 0.5,
            'attack_interval_min': 3.0, 'attack_interval_max': 5.0,
            'attack_radius': 18.0, 'speed_multiplier': 1.0}
    # 受击标记：damage_sensor 抛事件 → 加 is_sheared + 0.45s timer → 自动解除
    # （参考天启之境 melee_soldier 的纯 JSON 写法，不需要脚本）
    # 友伤免疫必须排在第一位：龙裔家族互相打不掉血
    # 第二条挡龙息云（magic）：原版 dragon_fireball 的 AoE 云会伤到同族
    comps['minecraft:damage_sensor'] = {'triggers': [
        {'on_damage': {'filters': {'test': 'is_family', 'subject': 'other',
                                   'value': 'dragonkin'},
                       'deals_damage': False}},
        {'cause': 'magic', 'deals_damage': False},
        {'on_damage': {'event': f'fycq:{stem}_hurt'}, 'deals_damage': True}]}

    for sk in b.get('skills', []):
        kind = sk['type']
        if kind == 'leap_at_target':
            comps['minecraft:behavior.leap_at_target'] = {
                'priority': sk['priority'], 'target_dist': sk['target_dist']}
        elif kind == 'knockback_roar':
            # 必须限定玩家：默认会对范围内所有实体生效，会把同族卷进内讧
            comps['minecraft:behavior.knockback_roar'] = {
                'priority': sk['priority'], 'duration': sk['duration'],
                'attack_time': sk['attack_time'], 'knockback_damage': sk['damage'],
                'knockback_strength': sk['strength'], 'knockback_range': sk['range'],
                'cooldown_time': sk['cooldown'],
                'damage_filters': {'test': 'is_family', 'subject': 'other', 'value': 'player'},
                'knockback_filters': {'test': 'is_family', 'subject': 'other', 'value': 'player'}}
        elif kind == 'area_attack':
            comps['minecraft:area_attack'] = {
                'priority': sk['priority'], 'cause': 'entity_attack',
                'damage_per_tick': sk['damage_per_tick'], 'damage_range': sk['range'],
                'entity_filter': {'test': 'is_family', 'subject': 'other', 'value': 'player'}}
        elif kind == 'summon_entity':
            comps['minecraft:behavior.summon_entity'] = {
                'priority': sk['priority'], 'summon_choices': [{
                    'min_activation_range': 0.0, 'max_activation_range': sk['max_range'],
                    'weight': 1, 'cooldown_time': sk['cooldown'], 'cast_duration': sk['cast'],
                    'sequence': [{'shape': 'circle', 'target': 'self',
                                  'base_delay': sk['cast'],
                                  'num_entities_spawned': sk['count'],
                                  'entity_type': sk['entity'], 'size': 0.0}]}]}

    flag = f'fycq:{stem}_hurt_flag'
    return {
        'format_version': '1.13.0',
        'minecraft:entity': {
            'description': {'identifier': f'fycq:{stem}', 'is_spawnable': True,
                            'is_summonable': True, 'is_experimental': False},
            'component_groups': {
                flag: {'minecraft:is_sheared': {},
                       'minecraft:timer': {'time': 0.45, 'looping': False,
                                           'time_down_event': {'event': f'fycq:{stem}_hurt_end'}}}},
            'components': comps,
            'events': {
                f'fycq:{stem}_hurt': {'add': {'component_groups': [flag]}},
                f'fycq:{stem}_hurt_end': {'remove': {'component_groups': [flag]}},
            },
        },
    }


def main():
    for stem, spec in MOBS.items():
        bones = spec['bones']()
        # 尺寸统一归整：UV 展开矩形必须是整数，模型与贴图共用同一份整数尺寸
        for b in bones:
            for c in b.get('cubes', []):
                c['size'] = [max(1, int(round(v))) for v in c['size']]
        used = pack_uvs(bones, spec['tex'])
        tex_h = 64 if used <= 64 else 128
        dump(os.path.join(RP, 'models', 'entity', f'{stem}.json'),
             geometry(stem, bones, spec['tex'], tex_h, spec['vb']))
        paint(bones, spec['tex'], tex_h).save(
            os.path.join(RP, 'textures', 'entity', 'fycq', f'{stem}.png'))
        dump(os.path.join(RP, 'animations', f'{stem}.json'),
             {'format_version': '1.8.0', 'animations': build_animations(stem, spec)})
        ctrl = 'controller.animation.' + stem
        ctrl_states = {
            'default': {
                'animations': ['idle'], 'blend_transition': 0.2,
                'transitions': [
                    {'death': 'query.is_alive == 0.0'},
                    {'hurt': 'query.is_sheared'},
                    {'attack': 'query.is_delayed_attacking == 1'},
                    {'move': 'query.modified_move_speed > 0.05'}]},
            'move': {
                'animations': ['move'], 'blend_transition': 0.2,
                'transitions': [
                    {'death': 'query.is_alive == 0.0'},
                    {'hurt': 'query.is_sheared'},
                    {'attack': 'query.is_delayed_attacking == 1'},
                    {'default': 'query.modified_move_speed <= 0.05'}]},
            'attack': {
                # 必须叠加 idle：idle 驱动了身体起伏，单播 attack 会把没动的骨头清零（瞬移/抽帧感）
                'animations': ['idle', 'attack'], 'blend_transition': 0.1,
                'transitions': [
                    {'death': 'query.is_alive == 0.0'},
                    {'default': 'query.is_delayed_attacking != 1'}]},
            'hurt': {
                'animations': ['idle', 'hurt'], 'blend_transition': 0.1,
                'transitions': [
                    {'death': 'query.is_alive == 0.0'},
                    {'default': '!query.is_sheared'}]},
            'death': {'animations': ['death'], 'transitions': []},
        }
        dump(os.path.join(RP, 'animation_controllers', f'{stem}.json'), {
            'format_version': '1.10.0',
            'animation_controllers': {ctrl: {
                'initial_state': 'default', 'states': ctrl_states}}})
        dump(os.path.join(RP, 'render_controllers', f'{stem}.json'), {
            'format_version': '1.8.0',
            'render_controllers': {f'controller.render.{stem}': {
                'geometry': 'Geometry.default',
                'materials': [{'*': 'Material.default'}],
                'textures': ['Texture.default']}}})
        dump(os.path.join(RP, 'entity', f'{stem}.json'), {
            'format_version': '1.8.0',
            'minecraft:client_entity': {'description': {
                'identifier': f'fycq:{stem}',
                'materials': {'default': 'entity_alphatest'},
                'textures': {'default': f'textures/entity/fycq/{stem}'},
                'geometry': {'default': f'geometry.{stem}'},
                'animations': {'idle': f'animation.{stem}.idle',
                               'move': f'animation.{stem}.move',
                               'attack': f'animation.{stem}.attack',
                               'hurt': f'animation.{stem}.hurt',
                               'death': f'animation.{stem}.death'},
                'sound_effects': spec['beh']['sounds'],
                'animation_controllers': [{'main': ctrl}],
                'render_controllers': [f'controller.render.{stem}'],
                'spawn_egg': {'base_color': '#2E8B7E', 'overlay_color': '#C9A227'}}}})
        dump(os.path.join(BP, 'entities', f'{stem}.json'), build_beh(stem, spec))
        dump(os.path.join(BP, 'loot_tables', 'fycq', f'{stem}.json'), build_loot(stem, spec['beh']))
        print(f'{stem}: bones {len(bones)} uv高 {used} 贴图 {spec["tex"]}x{tex_h}'
              f' 组件 {len(build_beh(stem, spec)["minecraft:entity"]["components"])}')


if __name__ == '__main__':
    main()
