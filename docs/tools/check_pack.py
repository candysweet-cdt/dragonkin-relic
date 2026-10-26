"""Drasnea BOSS 包体检：结构、引用完整性、注册一致性。

用法：python docs/tools/check_pack.py
任何 FAIL 都会以非零退出。
"""
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_creative_layout import UNGROUPED  # 故意不入组的件，唯一真源在布局脚本

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BP = os.path.join(ROOT, 'awesome_behavior_packs')
RP = os.path.join(ROOT, 'awesome_resource_packs')

fails = []


def bad(msg):
    fails.append(msg)
    print('  FAIL', msg)


def load(path):
    with open(path, encoding='utf-8-sig') as f:
        return json.load(f)


def rel(*parts):
    return os.path.join(*parts)


def check_json():
    paths = glob.glob(rel(BP, '**', '*.json'), recursive=True) + glob.glob(rel(RP, '**', '*.json'), recursive=True)
    data = {}
    for p in paths:
        try:
            data[os.path.normpath(p)] = load(p)
        except Exception as e:
            bad(f'JSON 解析失败 {os.path.relpath(p, ROOT)}: {e}')
    print(f'JSON 解析: {len(paths)} 个文件')
    return data


def collect_items(data):
    beh = {}
    for p, d in data.items():
        if os.sep + 'netease_items_beh' + os.sep in p:
            beh[d['minecraft:item']['description']['identifier']] = (p, d)
    res = {}
    for p, d in data.items():
        if os.sep + 'netease_items_res' + os.sep in p:
            res[d['minecraft:item']['description']['identifier']] = (p, d)
    return beh, res


def check_items(data, beh, res):
    print(f'自定义物品: beh {len(beh)} / res {len(res)}')
    for ident in beh:
        if ident not in res:
            bad(f'{ident} 缺 netease_items_res 定义')
        if not ident.startswith('fycq:'):
            bad(f'{ident} 命名空间不是 fycq')
    for ident, (_, d) in beh.items():
        desc = d['minecraft:item']['description']
        if not desc.get('category'):
            bad(f'{ident} 缺 category（会掉进默认分页）')
        if d['minecraft:item']['format_version'] if False else False:
            pass
        if not d['minecraft:item'].get('components'):
            bad(f'{ident} 没有 components')

    # 图标
    atlas = data.get(rel(RP, 'textures', 'item_texture.json'))
    if not atlas:
        bad('缺 textures/item_texture.json')
        return
    tdata = atlas['texture_data']
    for ident in beh:
        if ident not in tdata:
            bad(f'{ident} 未在 item_texture.json 注册图标')
            continue
        tex = tdata[ident]['textures']
        if isinstance(tex, list):
            tex = tex[0]
        if not os.path.exists(os.path.join(RP, tex + '.png')):
            bad(f'{ident} 图标文件不存在: {tex}.png')
        icon = res.get(ident, (None, None))[1]
        if icon and icon['minecraft:item']['components'].get('minecraft:icon') != ident:
            bad(f'{ident} 的 res 里 minecraft:icon 与图集键不一致')

    # lang
    lang_path = rel(RP, 'texts', 'zh_CN.lang')
    lang = open(lang_path, encoding='utf-8').read()
    for ident in beh:
        if f'item.{ident}.name=' not in lang:
            bad(f'lang 缺中文名 item.{ident}.name')
    # 创造栏
    tabs = [load(p) for p in glob.glob(rel(BP, 'netease_tab', '*.json'))]
    tab_names = {c['name'] for t in tabs for c in t.get('category', [])}
    for ident, (_, d) in beh.items():
        cat = d['minecraft:item']['description'].get('category')
        if cat and cat not in ('construction', 'equipment', 'items', 'nature', 'commands', 'none') and cat not in tab_names:
            bad(f'{ident} 的 category {cat} 没有对应的 netease_tab 定义')
    for name in tab_names:
        if f'itemCategory.name.{name}=' not in lang:
            bad(f'创造栏 {name} 缺 lang 键 itemCategory.name.{name}')


def check_attachables(data, beh):
    for p, d in data.items():
        if os.sep + 'attachables' + os.sep not in p:
            continue
        ident = d['minecraft:attachable']['description']['identifier']
        if ident not in beh:
            bad(f'attachable {ident} 没有对应物品')
        tex = d['minecraft:attachable']['description']['textures']['default']
        if not os.path.exists(os.path.join(RP, tex + '.png')):
            bad(f'attachable {ident} 贴图不存在: {tex}.png')
    armors = [i for i, (_, d) in beh.items()
              if d['minecraft:item']['description'].get('custom_item_type') == 'armor']
    attach_ids = {d['minecraft:attachable']['description']['identifier']
                  for p, d in data.items() if os.sep + 'attachables' + os.sep in p}
    for a in armors:
        if a not in attach_ids:
            bad(f'盔甲 {a} 缺 attachables（穿上看不见）')


def known_ids(data):
    ids = set()
    for p, d in data.items():
        if os.sep + 'netease_items_beh' + os.sep in p:
            ids.add(d['minecraft:item']['description']['identifier'])
        if os.sep + 'netease_blocks' + os.sep in p:
            ids.add(d['minecraft:block']['description']['identifier'])
    return ids


def check_recipes(data, ids):
    n = 0
    for p, d in data.items():
        if os.sep + 'netease_recipes' + os.sep not in p:
            continue
        n += 1
        body = d.get('minecraft:recipe_shaped') or d.get('minecraft:recipe_shapeless')
        if not body:
            bad(f'配方 {os.path.basename(p)} 既不是 shaped 也不是 shapeless')
            continue
        body = body
        refs = []
        if 'key' in body:
            refs += [v['item'] for v in body['key'].values()]
        if 'ingredients' in body:
            refs += [v['item'] for v in body['ingredients']]
        result = body['result']
        results = result if isinstance(result, list) else [result]
        refs += [r['item'] for r in results]
        for r in refs:
            if r.startswith('fycq:') and r not in ids:
                bad(f'配方 {os.path.basename(p)} 引用了不存在的 fycq 物品/方块: {r}')
    print(f'自定义配方: {n} 条')


def check_loot(data, ids):
    for p, d in data.items():
        if os.sep + 'loot_tables' + os.sep not in p:
            continue
        for pool in d.get('pools', []):
            for e in pool.get('entries', []):
                name = e.get('name', '')
                if name.startswith('fycq:') and name not in ids:
                    bad(f'掉落表 {os.path.basename(p)} 引用不存在的物品: {name}')


def check_entities(data):
    """逐个实体校验 BP↔RP 配对与全部交叉引用（几何体/贴图/动画/控制器/掉落/蛋/lang）。"""
    def bucket(sep, key=None):
        out = {}
        for path, d in data.items():
            if sep + os.sep not in path and sep not in path:
                continue
            if sep not in path:
                continue
            out[path] = d
        return out

    bp_entities = {}
    for path, d in data.items():
        if os.sep + 'entities' + os.sep in path:
            ent = (d.get('minecraft:entity') or {})
            if ent.get('description'):
                bp_entities[ent['description']['identifier']] = (path, ent)
    rp_entities = {}
    for path, d in data.items():
        if os.sep + 'entity' + os.sep in path and 'minecraft:client_entity' in d:
            de = d['minecraft:client_entity']['description']
            rp_entities[de['identifier']] = (path, de)
    anims, controllers, renders, geos = {}, {}, {}, set()
    for path, d in data.items():
        if os.sep + 'animations' + os.sep in path:
            anims.update(d.get('animations', {}))
        if os.sep + 'animation_controllers' + os.sep in path:
            controllers.update(d.get('animation_controllers', {}))
        if os.sep + 'render_controllers' + os.sep in path:
            renders.update(d.get('render_controllers', {}))
        if os.sep + 'models' + os.sep in path:
            for g in d.get('minecraft:geometry') or []:
                geos.add(g['description']['identifier'])
            geos.update(k for k in d if k.startswith('geometry.'))
    lang = open(os.path.join(RP, 'texts', 'zh_CN.lang'), encoding='utf-8').read()

    print(f'实体: BP {len(bp_entities)} / RP {len(rp_entities)}')
    for ident, (path, ent) in sorted(bp_entities.items()):
        for k in ent:
            if k not in ('description', 'components', 'component_groups', 'events'):
                bad(f'{ident} 顶层非法键 {k}（组件必须写在 components 内）')
        comps = ent['components']
        if 'minecraft:physics' not in comps:
            bad(f'{ident} 缺 minecraft:physics（引擎不落地）')
        if 'minecraft:equipment' in comps:
            bad(f'{ident} 用 equipment 挂掉落表（应为 minecraft:loot）')
        loot = comps.get('minecraft:loot')
        if not loot:
            bad(f'{ident} 缺 minecraft:loot')
        elif not os.path.exists(os.path.join(BP, loot['table'])):
            bad(f'{ident} 掉落表不存在: {loot["table"]}')
        if f'entity.{ident}.name=' not in lang:
            bad(f'lang 缺实体名 entity.{ident}.name')
        if ident not in rp_entities:
            bad(f'{ident} 缺资源包 client_entity')
            continue
        _, de = rp_entities[ident]
        tex = de['textures']['default']
        if not os.path.exists(os.path.join(RP, tex + '.png')):
            bad(f'{ident} 贴图不存在: {tex}.png')
        if de['geometry']['default'] not in geos:
            bad(f'{ident} 几何体未定义: {de["geometry"]["default"]}')
        for short, full in de.get('animations', {}).items():
            if full not in anims:
                bad(f'{ident} 动画 {short} -> {full} 未定义')
        for entry in de.get('animation_controllers', []):
            for short, ctrl in entry.items():
                if ctrl not in controllers:
                    bad(f'{ident} 动画控制器未定义: {ctrl}')
                    continue
                ctrl_body = controllers[ctrl]
                states = ctrl_body.get('states', {})
                if 'initial_state' not in ctrl_body:
                    bad(f'{ident} 控制器 {ctrl} 缺 initial_state（缺了整条控制器不进入任何状态，动画不播）')
                init = ctrl_body.get('initial_state')
                if init and init not in states:
                    bad(f'{ident} 控制器 {ctrl} 的 initial_state={init} 不在 states 里')
                if init and init != 'default':
                    bad(f'{ident} 控制器 {ctrl} 的 initial_state 应为 default（基岩惯例，参考包一致）')
                for st, body in states.items():
                    for act in body.get('animations', []):
                        names = act.keys() if isinstance(act, dict) else [act]
                        for name in names:
                            if name not in de.get('animations', {}):
                                bad(f'{ident} 控制器 {ctrl}/{st} 引用未注册短名 {name}')
                    for tr in body.get('transitions', []):
                        for tgt in tr:
                            if tgt not in states:
                                bad(f'{ident} 控制器 {ctrl}/{st} 转到不存在的状态 {tgt}')
        for rc in de.get('render_controllers', []):
            if rc not in renders:
                bad(f'{ident} 渲染控制器未定义: {rc}')
        if ent['description'].get('is_spawnable') and                 f'item.spawn_egg.entity.{ident}.name=' not in lang:
            bad(f'lang 缺刷怪蛋名 item.spawn_egg.entity.{ident}.name')

    for name, a in anims.items():
        L = a.get('animation_length')
        if not L or not a.get('loop'):
            continue
        times = []
        for bone in a.get('bones', {}).values():
            for prop in ('rotation', 'position', 'scale'):
                v = bone.get(prop)
                if isinstance(v, dict):
                    times += [float(t) for t in v.keys()]
                elif isinstance(v, list):
                    times.append(0.0)
        if not times:
            bad(f'动画 {name} 没有任何关键帧')
            continue
        span = max(times)
        if span < L * 0.75:
            bad(f'动画 {name} 关键帧只到 {span}s / 循环长 {L}s'
                '（铺不满会播完卡在最后一帧再跳回）')
        if span > L + 0.05:   # 允许 1/20 秒内越界（原作者数据里有 1.9667/1.96）
            bad(f'动画 {name} 关键帧 {span}s 超出循环长 {L}s')

    for path, d in data.items():
        if os.sep + 'netease_items_beh' + os.sep not in path:
            continue
        comps = d['minecraft:item']['components']
        egg = comps.get('netease:egg')
        if not egg:
            continue
        if egg['entity'] not in bp_entities:
            bad(f'{os.path.basename(path)} 的 netease:egg 指向不存在的实体 {egg["entity"]}')
        if d['minecraft:item']['description'].get('custom_item_type') != 'egg':
            bad(f'{os.path.basename(path)} 有 netease:egg 但 custom_item_type 不是 egg')


def check_manifests(data):
    for relp in ('awesome_behavior_packs/manifest.json', 'awesome_resource_packs/manifest.json'):
        d = data.get(os.path.normpath(os.path.join(ROOT, relp)))
        if not d:
            bad(f'缺 {relp}')
            continue
        mev = d['header'].get('min_engine_version')
        if not mev or mev < [1, 18, 0]:
            bad(f'{relp} min_engine_version={mev}（审核错误码 37）')
        if not d['modules'][0].get('uuid'):
            bad(f'{relp} module 缺 uuid')


def check_blocks(data):
    blocks = {}
    for p, d in data.items():
        if os.sep + 'netease_blocks' + os.sep in p:
            blocks[d['minecraft:block']['description']['identifier']] = (p, d)
    if not blocks:
        return
    print(f'自定义方块: {len(blocks)}')
    blocks_json = data.get(os.path.normpath(os.path.join(RP, 'blocks.json')))
    terrain = data.get(os.path.normpath(os.path.join(RP, 'textures', 'terrain_texture.json')))
    if not blocks_json:
        bad('缺资源包 blocks.json')
        return
    if not terrain:
        bad('缺资源包 textures/terrain_texture.json')
        return
    tdata = terrain['texture_data']
    lang = open(os.path.join(RP, 'texts', 'zh_CN.lang'), encoding='utf-8').read()
    for ident, (p, d) in blocks.items():
        if ident not in blocks_json:
            bad(f'blocks.json 缺 {ident}（方块会丢贴图/音效）')
            continue
        tex = blocks_json[ident]['textures']
        names = list(tex.values()) if isinstance(tex, dict) else [tex]
        for n in names:
            if n not in tdata:
                bad(f'{ident} 的贴图 {n} 未在 terrain_texture.json 注册')
                continue
            path = tdata[n]['textures']
            if isinstance(path, list):
                path = path[0]
            if not os.path.exists(os.path.join(RP, path + '.png')):
                bad(f'{ident} 的贴图文件不存在: {path}.png')
        if f'tile.{ident}.name=' not in lang:
            bad(f'lang 缺方块名 tile.{ident}.name')
        loot = d['minecraft:block']['components'].get('minecraft:loot')
        if not loot:
            bad(f'{ident} 缺 minecraft:loot（挖掉可能不掉落）')
        elif not os.path.exists(os.path.join(BP, loot['table'])):
            bad(f'{ident} 掉落表不存在: {loot["table"]}')
        emission = d['minecraft:block']['components'].get('minecraft:block_light_emission')
        if emission is not None:
            v = emission.get('emission')
            if not isinstance(v, (int, float)) or not (0 <= v <= 1):
                bad(f'{ident} 的 block_light_emission.emission={v} 越界（引擎要求 0~1 浮点，越界会导致方块定义升级失败并让配方断言崩溃）')


def check_recipe_rules(data, beh):
    """红线 §2.17 与 §1.5：shaped 行数≤3 / 各行等长 / key 全用到；产物数 ≤ 最大堆叠。"""
    stacks = {}
    for ident, (_, d) in beh.items():
        comps = d['minecraft:item']['components']
        stacks[ident] = comps.get('minecraft:max_stack_size', 1)
    for p, d in data.items():
        if os.sep + 'netease_recipes' + os.sep not in p:
            continue
        name = os.path.basename(p)
        shaped = d.get('minecraft:recipe_shaped')
        body = shaped or d.get('minecraft:recipe_shapeless')
        if not body:
            continue
        results = body['result']
        results = results if isinstance(results, list) else [results]
        for r in results:
            cnt = r.get('count', 1)
            ident = r['item']
            if ident in stacks and cnt > max(stacks[ident], 1):
                bad(f'配方 {name} 产物 {ident} 数量 {cnt} 超过最大堆叠 {stacks[ident]}（红线 §1.5 会断言）')
        if shaped:
            pattern = shaped.get('pattern', [])
            if len(pattern) > 3:
                bad(f'配方 {name} 图案 {len(pattern)} 行，超过 3 行（红线 §2.17）')
            lens = {len(row) for row in pattern}
            if len(lens) > 1:
                bad(f'配方 {name} 各行长度不一致 {sorted(lens)}（红线 §2.17）')
            used = {ch for row in pattern for ch in row if ch != ' '}
            keys = set(shaped.get('key', {}))
            if used - keys:
                bad(f'配方 {name} 图案用到未定义的 key: {sorted(used - keys)}')
            if keys - used:
                bad(f'配方 {name} 定义了没用到的 key: {sorted(keys - used)}')


def check_skills(data):
    """技能与状态机联动：攻击态↔delayed_attack、受击标记↔timer、召唤目标、触发事件。"""
    bp_entities = {}
    for path, d in data.items():
        if os.sep + 'entities' + os.sep in path:
            ent = d.get('minecraft:entity') or {}
            if ent.get('description'):
                bp_entities[ent['description']['identifier']] = ent
    controllers = {}
    for path, d in data.items():
        if os.sep + 'animation_controllers' + os.sep in path:
            controllers.update(d.get('animation_controllers', {}))

    for ident, ent in sorted(bp_entities.items()):
        stem = ident.split(':', 1)[1]
        comps = ent['components']
        groups = ent.get('component_groups', {})
        events = ent.get('events', {})
        has_attack_state = any('attack' in (c.get('states') or {})
                              for c in controllers.values())
        if has_attack_state and 'minecraft:behavior.delayed_attack' not in comps:
            bad(f'{ident} 动画有 attack 态，但实体没有 behavior.delayed_attack'
                '（query.is_delayed_attacking 永远不会为 1，攻击动画不播）')
        if 'minecraft:behavior.delayed_attack' in comps and not has_attack_state:
            bad(f'{ident} 配了 delayed_attack 却没有 attack 动画态')

        ds = comps.get('minecraft:damage_sensor')
        if ds:
            for trg in ds.get('triggers', []):
                ev = (trg.get('on_damage') or {}).get('event')
                if ev and ev not in events:
                    bad(f'{ident} damage_sensor 触发的 {ev} 不在 events 里')
        hurt_groups = [g for g, body in groups.items() if 'minecraft:is_sheared' in body]
        if hurt_groups:
            for g in hurt_groups:
                timer = groups[g].get('minecraft:timer')
                if not timer:
                    bad(f'{ident} 受击组 {g} 有 is_sheared 但没有 timer，标记永远解不掉')
                else:
                    down = (timer.get('time_down_event') or {}).get('event')
                    if down and down not in events:
                        bad(f'{ident} 受击组的 time_down_event={down} 不在 events 里')
                    elif down:
                        rm = events[down].get('remove', {}).get('component_groups', [])
                        if g not in rm:
                            bad(f'{ident} 事件 {down} 没有移除受击组 {g}（会永远处于受击态）')

        su = comps.get('minecraft:behavior.summon_entity')
        if su:
            for ch in su.get('summon_choices', []):
                for seq in ch.get('sequence', []) or []:
                    tgt = seq.get('entity_type')
                    if tgt and tgt not in bp_entities:
                        bad(f'{ident} summon_entity 召唤的 {tgt} 不是本包实体'
                            '（跨包/原版请用 runtime_identifier 方案）')

    print(f'技能联动: {len(bp_entities)} 个实体检查完毕')


def check_anim_overlay(data):
    """idle 驱动了 root 位置时，其它状态必须叠加 idle，否则切态瞬间 root 归零 = 整只弹回原位。"""
    anims = {}
    for path, d in data.items():
        if os.sep + 'animations' + os.sep in path:
            anims.update(d.get('animations', {}))
    controllers = {}
    for path, d in data.items():
        if os.sep + 'animation_controllers' + os.sep in path:
            controllers.update(d.get('animation_controllers', {}))
    for path, d in data.items():
        if os.sep + 'entity' + os.sep not in path or 'minecraft:client_entity' not in d:
            continue
        de = d['minecraft:client_entity']['description']
        ident = de['identifier']
        short2full = de.get('animations', {})
        idle = anims.get(short2full.get('idle', ''), {})
        idle_root = (idle.get('bones') or {}).get('root') or {}
        if 'position' not in idle_root:
            continue
        for entry in de.get('animation_controllers', []):
            for ctrl in entry.values():
                for state_name, st in (controllers.get(ctrl, {}).get('states') or {}).items():
                    clips = [a if isinstance(a, str) else list(a.keys())[0]
                             for a in st.get('animations', [])]
                    if 'idle' in clips:
                        continue
                    for clip in clips:
                        full = short2full.get(clip, '')
                        bones = (anims.get(full) or {}).get('bones') or {}
                        if 'root' not in bones:
                            bad(f'{ident} 控制器 {ctrl}/{state_name} 只播 {clip}，'
                                '而 idle 驱动了 root 位置 —— 切态会把整只弹回绑定姿势'
                                '（该状态需叠加 idle，或给该动画补 root 关键帧）')
    print('动画叠加: 已检查 idle 动 root 的实体')


def check_weapon_balance(data):
    """基岩版没有攻击冷却：斧的伤害必须低于剑，否则斧在同等耐久下全面压过剑。"""
    dmg = {}
    for path, d in data.items():
        if os.sep + 'netease_items_beh' + os.sep not in path:
            continue
        item = d['minecraft:item']
        weapon = item.get('components', {}).get('netease:weapon')
        if not weapon:
            continue
        ident = item['description']['identifier']
        dmg[ident] = (weapon.get('type'), weapon.get('attack_damage', 0))
    swords = [v for t, v in dmg.values() if t == 'sword']
    axes = [(k, v) for k, (t, v) in dmg.items() if t == 'hatchet']
    if swords:
        top = max(swords)
        for ident, value in axes:
            if value >= top:
                bad(f'{ident} 伤害 {value} ≥ 剑 {top} —— 基岩版无攻击冷却，斧不该压过剑')
    print(f'武器数值: {len(dmg)} 件武器已核对（斧伤害 < 剑）')


def check_repair_paths(data):
    """每件有耐久的龙裔装备，都必须有重铸配方（铁砧不认自定义材料）。"""
    recipes = set()
    for path, d in data.items():
        if os.sep + 'netease_recipes' + os.sep in path:
            body = d.get('minecraft:recipe_shaped') or d.get('minecraft:recipe_shapeless') or {}
            recipes.add((body.get('description') or {}).get('identifier', ''))
    durable = []
    for path, d in data.items():
        if os.sep + 'netease_items_beh' + os.sep not in path:
            continue
        item = d['minecraft:item']
        ident = item['description']['identifier']
        comps = item['components']
        if 'minecraft:max_damage' not in comps:
            continue
        durable.append(ident)
        stem = ident.split(':', 1)[1]
        has_repairable = 'minecraft:repairable' in comps
        has_rebuild = ('fycq:repair_' + stem) in recipes
        if not has_rebuild:
            bad(f'{ident} 有耐久但没有重铸配方 repair_{stem}（坏了只能靠钻石修，不主题）')
        if has_repairable:
            bad(f'{ident} 又写了 minecraft:repairable —— 实测无效（铁砧只认 netease:weapon.level），删掉')
    script = os.path.join(BP, 'DrasneaScripts', 'repairStation.py')
    if not os.path.isfile(script):
        bad('缺 DrasneaScripts/repairStation.py —— 铁砧修不了自定义盔甲，龙巢修复是唯一龙鳞路线')
    else:
        src = open(script, encoding='utf-8').read()
        for const in ('fycq:dragon_nest', 'fycq:dragon_scale'):
            if "'" + const + "'" not in src:
                bad(f'repairStation.py 缺常量 {const}')
        missing = [g for g in durable if "'" + g + "'" not in src]
        if missing:
            bad(f'repairStation.py 的 GEAR 漏了: {", ".join(missing)}')
        main_src = open(os.path.join(BP, 'DrasneaScripts', 'modMain.py'), encoding='utf-8').read()
        if 'RepairStationServer' not in main_src:
            bad('modMain.py 没有注册 RepairStationServer，龙巢修复不会加载')
    print(f'修复路径: {len(durable)} 件有耐久装备已核对（重铸配方 + 龙巢修复覆盖）')


def check_wing_edges():
    """翅膀加厚后，1px 侧面条带必须透明：否则整块膜的矩形轮廓会描成悬浮方框。"""
    from PIL import Image
    model_path = os.path.join(RP, 'models', 'entity', 'drasnea.json')
    tex_path = os.path.join(RP, 'textures', 'entity', 'fycq', 'drasnea.png')
    geo = load(model_path)['geometry.drasnea']
    px = Image.open(tex_path).convert('RGBA').load()

    def ir(v):
        return int(round(v))

    def faces(uv, size):
        u, v = ir(uv[0]), ir(uv[1])
        w, h, d = ir(size[0]), ir(size[1]), ir(size[2])
        return {
            'west': (u, v + d, d, h), 'north': (u + d, v + d, w, h),
            'east': (u + d + w, v + d, d, h), 'south': (u + d + w + d, v + d, w, h),
            'up': (u + d, v, w, d), 'down': (u + d + w, v, w, d),
        }

    protected, strips, wings = set(), set(), 0
    for bone in geo['bones']:
        for cube in bone.get('cubes') or []:
            if not isinstance(cube.get('uv'), list):
                continue
            wing = ('wind' in bone['name'] and abs(cube['size'][0] - 1.0) < 1e-6)
            wings += 1 if wing else 0
            for name, (x, y, w, h) in faces(cube['uv'], cube['size']).items():
                cells = [(xx, yy) for yy in range(y, y + h) for xx in range(x, x + w)]
                if wing and name in ('north', 'south', 'up', 'down'):
                    strips.update(cells)
                else:
                    protected.update(cells)
    dirty = [(x, y) for (x, y) in sorted(strips - protected) if px[x, y][3] > 0]
    if dirty:
        bad(f'翅膀侧面有 {len(dirty)} 个不透明纹素（例 {dirty[:4]}）—— 实机会描出悬浮矩形框；'
            '跑 docs/tools/fix_wing_edge_strips.py --write')
    print(f'翅膀侧面: {wings} 块膜 / {len(strips)} 个侧面纹素（{len(strips & protected)} 个与其它面共用）已核对')


def check_spawn_rules(data):
    """三只小怪要有自然刷怪规则；BOSS 不许自然刷。"""
    rules = {}
    for path, d in data.items():
        if os.sep + 'spawn_rules' + os.sep in path:
            body = (d.get('minecraft:spawn_rules') or {})
            ident = (body.get('description') or {}).get('identifier')
            if ident:
                rules[ident] = body
    for ident in ('fycq:dragon_whelp', 'fycq:dragon_priest', 'fycq:dragon_guard'):
        body = rules.get(ident)
        name = ident.split(':', 1)[1] + '.json'
        if not body:
            bad(f'缺 spawn_rules/{name} —— {ident} 不会自然刷')
            continue
        desc = body.get('description') or {}
        if desc.get('population_control') != 'monster':
            bad(f'{name} 的 population_control 不是 monster')
        conds = body.get('conditions') or []
        if not conds:
            bad(f'{name} 没有 conditions')
        for cond in conds:
            for key in ('minecraft:brightness_filter', 'minecraft:difficulty_filter',
                        'minecraft:weight', 'minecraft:herd', 'minecraft:biome_filter'):
                if key not in cond:
                    bad(f'{name} 的条件缺 {key}')
            if 'minecraft:spawns_on_surface' not in cond:
                bad(f'{name} 没有 spawns_on_surface')
    if 'fycq:drasnea' in rules:
        bad('BOSS fycq:drasnea 不应有自然刷怪规则')
    print(f'自然刷怪: {len(rules)} 条规则已核对（BOSS 不自然刷）')


def check_whelp_flight(data):
    """幼龙真飞：fly 导航 + random_fly + 无重力；hover 那套只会原地打转，走路/扑咬也不能留。"""
    target = None
    for path, d in data.items():
        if os.sep + 'entities' + os.sep not in path:
            continue
        ent = d.get('minecraft:entity') or {}
        if (ent.get('description') or {}).get('identifier') == 'fycq:dragon_whelp':
            target = ent
    if not target:
        bad('找不到 fycq:dragon_whelp')
        return
    comps = target.get('components') or {}
    for key in ('minecraft:navigation.fly', 'minecraft:movement.fly',
                'minecraft:can_fly', 'minecraft:behavior.random_fly'):
        if key not in comps:
            bad(f'幼龙缺 {key}（不会真飞）')
    if (comps.get('minecraft:physics') or {}).get('has_gravity') is not False:
        bad('幼龙的 physics.has_gravity 不是 false')
    for key in ('minecraft:navigation.walk', 'minecraft:movement.basic',
                'minecraft:behavior.leap_at_target', 'minecraft:behavior.random_stroll',
                'minecraft:navigation.hover', 'minecraft:movement.hover',
                'minecraft:behavior.random_hover'):
        if key in comps:
            bad(f'幼龙还留着 {key}（hover 会原地悬停打转 / 走路导航会和 fly 打架）')
    print('幼龙飞行: fly 导航已核对')


def check_skill_hud(data):
    """技能按钮 HUD：UI 文件注册、命名与贴图齐全，客户端/服务端脚本对得上。"""
    defs_path = os.path.join(RP, 'ui', '_ui_defs.json')
    hud_path = os.path.join(RP, 'ui', 'dragonskillhud.json')
    if not os.path.isfile(defs_path):
        bad('缺 resource/ui/_ui_defs.json —— 引擎不会加载任何自定义 UI')
    else:
        defs = load(defs_path).get('ui_defs') or []
        if 'ui/dragonskillhud.json' not in defs:
            bad('_ui_defs.json 没登记 ui/dragonskillhud.json')
    if not os.path.isfile(hud_path):
        bad('缺 resource/ui/dragonskillhud.json —— 技能按钮不会出现')
        return
    hud = load(hud_path)
    if hud.get('namespace') != 'dragonskillhud':
        bad(f"UI namespace 是 {hud.get('namespace')}，必须与文件名一致（RegisterUI 用 dragonskillhud.main）")
    if 'main@common.base_screen' not in hud:
        bad('dragonskillhud.json 缺 main@common.base_screen 根画布')
    btn = hud.get('skillButton@common.button') or {}
    if not btn:
        bad('dragonskillhud.json 缺 skillButton 控件')
    else:
        if btn.get('button_mappings') != []:
            bad('skillButton 的 button_mappings 必须为 []，否则 Python 回调收不到点击')
        if not btn.get('is_handle_button_move_event'):
            bad('skillButton 缺 is_handle_button_move_event（拖动需要）')
        if btn.get('draggable') != 'both':
            bad(f"skillButton.draggable = {btn.get('draggable')}，应为 both")
        if btn.get('contained') is not True:
            bad('skillButton 缺 contained: true（拖动会被父控件限制，防止拖出屏幕）')
        if btn.get('visible') is not False:
            bad('skillButton 初始 visible 必须是 false（只有手持龙牙剑才显示）')
        size = btn.get('size')
        if not (isinstance(size, list) and len(size) == 2
                and all(isinstance(v, int) and 24 <= v <= 48 for v in size)):
            bad(f'skillButton.size = {size}，作者要求按钮缩小（整数边长 24–48，64 太大）')
        for ctrl in btn.get('controls') or []:
            for state, body in ctrl.items():
                if state in ('default', 'hover', 'pressed'):
                    tex = (body or {}).get('texture')
                    if tex and not os.path.isfile(os.path.join(RP, tex + '.png')):
                        bad(f'skillButton.{state} 贴图不存在: {tex}.png')
    client = os.path.join(BP, 'DrasneaScripts', 'dragonSkillClient.py')
    server = os.path.join(BP, 'DrasneaScripts', 'dragonSlash.py')
    if not os.path.isfile(client):
        bad('缺 DrasneaScripts/dragonSkillClient.py')
        return
    csrc = open(client, encoding='utf-8').read()
    ssrc = open(server, encoding='utf-8').read() if os.path.isfile(server) else ''
    for token in ('RegisterUI', "'isHud': 1", 'SetButtonTouchUpCallback',
                  'SetButtonTouchMoveCallback', 'RightClickBeforeClientEvent',
                  'OnCarriedNewItemChangedClientEvent', 'CreateConfigClient',
                  'NotifyToServer'):
        if token not in csrc:
            bad(f'dragonSkillClient.py 缺 {token}')
    for token in ('CAST_EVENT', 'CLIENT_SYSTEM', 'GetPlayerList', 'GetDirFromRot',
                  'CreateHurt', 'RESULT_EVENT', 'NotifyToClient', '__id__', 'reject'):
        if token not in ssrc:
            bad(f'dragonSlash.py 缺 {token}')
    if 'PlayerAttackEntityEvent' not in ssrc:
        bad('dragonSlash.py 缺服务端兜底触发（手持龙牙剑命中即放锥形斩）—— '
            'HUD 按钮依赖客户端→服务端跨端事件，那条路一旦不通技能就整个不可用；'
            '本包击杀归属已实机验证 PlayerAttackEntityEvent 会触发')
    if 'CreateEventData' in csrc:
        bad('dragonSkillClient.py 又用 CreateEventData 当 NotifyToServer 的载荷 —— '
            '参考模组一律传普通 dict；而且倒计时在发送之后才起算，'
            '否则发送抛错也会显示 12 秒倒计时、服务端毫不知情')
    for token in ('GetEntitiesAround', 'GetFootPos'):
        if token not in ssrc:
            bad(f'dragonSlash.py 缺 {token}（锥形判定要按脚部坐标算，与参考模组一致）')
    if 'ALLY' in ssrc:
        bad('dragonSlash.py 又按 ALLY 跳过龙裔 —— 世界里针对玩家的恰恰是幼龙/祭司/龙卫，'
            '技能按钮对它们必须能造成伤害')
    if 'ServerItemTryUseEvent' in ssrc:
        bad('dragonSlash.py 又用了 ServerItemTryUseEvent —— 对 netease:weapon 不触发，'
            '只能靠 HUD 按钮 / RightClickBeforeClientEvent 上报')
    for name in ('COOLDOWN', 'CAST_EVENT'):
        cval = re.search(name + r"\s*=\s*([^#\n]+)", csrc)
        sval = re.search(name + r"\s*=\s*([^#\n]+)", ssrc)
        if not (cval and sval and cval.group(1).strip() == sval.group(1).strip()):
            bad(f'客户端与服务端的 {name} 不一致（按钮冷却显示会和实际不符）')
    print('技能按钮 HUD: UI 注册/控件/贴图/脚本对账完毕')


def check_combat_scripts():
    """套装效果与龙息斩：脚本存在、关键常量齐全、modMain 已注册。"""
    main_src = open(os.path.join(BP, 'DrasneaScripts', 'modMain.py'), encoding='utf-8').read()
    slash = os.path.join(BP, 'DrasneaScripts', 'dragonSlash.py')
    bonus = os.path.join(BP, 'DrasneaScripts', 'dragonSetBonus.py')
    if not os.path.isfile(slash):
        bad('缺 DrasneaScripts/dragonSlash.py —— 龙息斩不生效')
    else:
        src = open(slash, encoding='utf-8').read()
        for const in ('fycq:dragon_fang_sword', 'fycq:dragon_fang_sword_awakened'):
            if "'" + const + "'" not in src:
                bad(f'dragonSlash.py 缺 {const}')
        for token in ('GetDirFromRot', 'CreateHurt', 'COOLDOWN'):
            if token not in src:
                bad(f'dragonSlash.py 缺 {token}')
        if 'DragonSlashServer' not in main_src:
            bad('modMain.py 没有注册 DragonSlashServer')
    if not os.path.isfile(bonus):
        bad('缺 DrasneaScripts/dragonSetBonus.py —— 套装效果不生效')
    else:
        src = open(bonus, encoding='utf-8').read()
        for const in ('fycq:dragon_scale_helmet', 'fycq:dragon_scale_boots_awakened'):
            if "'" + const + "'" not in src:
                bad(f'dragonSetBonus.py 缺 {const}')
        for token in ('fire_resistance', 'regeneration', 'ARMOR', 'GetAllEffects'):
            if token not in src:
                bad(f'dragonSetBonus.py 缺 {token}')
        if 'DragonSetBonusServer' not in main_src:
            bad('modMain.py 没有注册 DragonSetBonusServer')
    print('套装/龙息斩: 脚本与注册已核对')


def check_breath():
    """龙息云清理脚本：存在、注册、常量指向真实 ID。"""
    script = os.path.join(BP, 'DrasneaScripts', 'dragonBreath.py')
    if not os.path.isfile(script):
        bad('缺 DrasneaScripts/dragonBreath.py —— 原版龙息云会留 120 秒')
        return
    src = open(script, encoding='utf-8').read()
    for const in ('minecraft:dragon_fireball', 'minecraft:area_effect_cloud',
                  'fycq:drasnea'):
        if "'" + const + "'" not in src:
            bad(f'dragonBreath.py 缺常量 {const}')
    main_src = open(os.path.join(BP, 'DrasneaScripts', 'modMain.py'), encoding='utf-8').read()
    if 'DragonBreathServer' not in main_src:
        bad('modMain.py 没有注册 DragonBreathServer，龙息云不会按时消失')
    print('龙息云: 脚本与注册已核对')


def check_altar_summon():
    """龙巢召唤脚本与注册：常量指向真实 ID，modMain 确实注册了系统。"""
    script = os.path.join(BP, 'DrasneaScripts', 'altarSummon.py')
    if not os.path.isfile(script):
        bad('缺 DrasneaScripts/altarSummon.py —— 龙巢召唤不生效')
    else:
        src = open(script, encoding='utf-8').read()
        for const in ('fycq:dragon_nest', 'fycq:dragon_heart', 'fycq:dragon_scale', 'fycq:drasnea'):
            if "'" + const + "'" not in src:
                bad(f'altarSummon.py 缺常量 {const}')
        for name in ('FIRST_COST_SCALE', 'FIRST_SUMMON_NODE'):
            if name not in src:
                bad(f'altarSummon.py 缺 {name}（首召 8 龙鳞 + 首召成就）')
        main_src = open(os.path.join(BP, 'DrasneaScripts', 'modMain.py'), encoding='utf-8').read()
        if 'AltarSummonServer' not in main_src:
            bad('modMain.py 没有注册 AltarSummonServer，龙巢召唤不会加载')
    print('龙巢召唤: 脚本与注册已核对')


def check_achievements(data):
    """自定义成就节点：字段完整、图标存在、finish_tip 打开，且脚本确实会完成该节点。"""
    nodes = [(p, d) for p, d in data.items() if os.sep + 'customAchievements' + os.sep in p]
    if not nodes:
        bad('缺 customAchievements/ 节点 —— 首杀不会弹成就')
        return
    ids = set()
    for path, d in nodes:
        name = os.path.basename(path)
        node = d.get('node_ID')
        if not node:
            bad(f'{name} 缺 node_ID')
            continue
        if node in ids:
            bad(f'{name} 的 node_ID {node} 重复')
        ids.add(node)
        for key in ('title', 'unfinished_icon', 'finished_icon', 'node_description'):
            if not d.get(key):
                bad(f'{name} 缺 {key}')
        if not isinstance(d.get('goal_number'), int) or d.get('goal_number', 0) < 1:
            bad(f'{name} 的 goal_number 必须是正整数')
        if d.get('finish_tip') is not True:
            bad(f'{name} 的 finish_tip 不是 true —— 完成时不会弹成就')
        if 'parent_node' not in d and not d.get('window_background'):
            bad(f'{name} 是根节点但没有 window_background')
        bg = d.get('window_background')
        if bg and not os.path.isfile(os.path.join(RP, bg + '.png')):
            bad(f'{name} 的 window_background 指向不存在的贴图 {bg}.png（实机会显示紫黑格）')
        for key in ('unfinished_icon', 'finished_icon'):
            icon = d.get(key)
            if icon and not os.path.isfile(os.path.join(RP, icon + '.png')):
                bad(f'{name} 的 {key} 指向不存在的贴图 {icon}.png')
    details = {d.get('node_ID'): d for _, d in nodes}
    for node_id, d in details.items():
        parent = d.get('parent_node')
        if parent:
            if parent not in ids:
                bad(f'节点 {node_id} 的 parent_node {parent} 不存在')
            if parent == node_id:
                bad(f'节点 {node_id} 的 parent_node 指向自己')
    script = os.path.join(BP, 'DrasneaScripts', 'achievementServer.py')
    altar_script = os.path.join(BP, 'DrasneaScripts', 'altarSummon.py')
    if not os.path.isfile(script):
        bad('缺 DrasneaScripts/achievementServer.py —— 成就不会完成/发奖')
    else:
        src = open(script, encoding='utf-8').read()
        altar_src = open(altar_script, encoding='utf-8').read() if os.path.isfile(altar_script) else ''
        for node_id, d in details.items():
            goal = d.get('goal_details')
            if goal:
                if goal.get('goal_type') not in ('default_kill', 'default_get'):
                    bad(f'节点 {node_id} 的 goal_type 不支持: {goal.get("goal_type")}')
                if goal.get('goal_type') == 'default_kill' and not goal.get('entity_identifier'):
                    bad(f'节点 {node_id} 的 default_kill 缺 entity_identifier')
                continue
            if ("'" + node_id + "'") not in src and ("'" + node_id + "'") not in altar_src:
                bad(f'节点 {node_id} 既没有 goal_details，也没有脚本完成它')
        main_src = open(os.path.join(BP, 'DrasneaScripts', 'modMain.py'), encoding='utf-8').read()
        if 'AchievementServer' not in main_src:
            bad('modMain.py 没有注册 AchievementServer，首杀成就不会加载')
        if 'PlayerAttackEntityEvent' not in src:
            bad('achievementServer.py 没监听 PlayerAttackEntityEvent —— '
                'MobDieEvent.attacker 是占位 id，会认不出击杀者')
    print(f'自定义成就: {len(nodes)} 个节点（字段/父子/图标/弹窗/脚本覆盖）')


def check_summon_cap(data):
    """本包禁止 JSON 的 behavior.summon_entity：它没有数量上限，多只 BOSS/祭司会堆爆刷怪量。
    召唤统一走脚本 bossPhase.py（全场幼龙 ≤ 8）。"""
    for path, d in data.items():
        if os.sep + 'entities' + os.sep not in path:
            continue
        ent = d.get('minecraft:entity') or {}
        ident = (ent.get('description') or {}).get('identifier', '')
        groups = ent.get('component_groups') or {}
        if 'minecraft:behavior.summon_entity' in (ent.get('components') or {}):
            bad(f'{ident} 用了 JSON summon_entity —— 没有数量上限，召唤请走 bossPhase.py')
        for g, body in groups.items():
            if 'minecraft:behavior.summon_entity' in body:
                bad(f'{ident} 的组件组 {g} 用了 JSON summon_entity —— 同上，改脚本限量召唤')
    print('召唤限流: 已检查（JSON summon_entity 一律禁止）')


def check_entity_events(data):
    """事件引用的 component_groups 必须真实存在（阶段/受击组都靠这条）。"""
    n = 0
    for path, d in data.items():
        if os.sep + 'entities' + os.sep not in path:
            continue
        ent = d.get('minecraft:entity') or {}
        ident = (ent.get('description') or {}).get('identifier', '')
        groups = set(ent.get('component_groups') or {})
        for name, body in (ent.get('events') or {}).items():
            for op in ('add', 'remove'):
                for g in ((body.get(op) or {}).get('component_groups') or []):
                    n += 1
                    if g not in groups:
                        bad(f'{ident} 事件 {name} {op} 了不存在的组件组 {g}')
    print(f'实体事件: {n} 处组件组引用已核对')


def check_aggression(data):
    """仇恨与友伤：不许隔墙全图仇恨，不许同族互殴。"""
    for path, d in data.items():
        if os.sep + 'entities' + os.sep not in path:
            continue
        ent = d.get('minecraft:entity') or {}
        ident = (ent.get('description') or {}).get('identifier', '')
        if not ident.startswith('fycq:'):
            continue
        comps = ent.get('components') or {}
        fam = (comps.get('minecraft:type_family') or {}).get('family') or []
        if 'dragonkin' not in fam:
            bad(f'{ident} 的 type_family 缺 dragonkin —— 免伤过滤按攻击者家族判定，'
                '缺了就会互相误伤并触发内讧（BOSS 曾漏过）')
        nt = comps.get('minecraft:behavior.nearest_attackable_target')
        if nt:
            if nt.get('must_see') is not True:
                bad(f'{ident} 的 nearest_attackable_target 没开 must_see（会隔墙全图追人）')
            for et in nt.get('entity_types', []) or []:
                md = et.get('max_dist')
                if md is None:
                    bad(f'{ident} 的目标类型缺 max_dist（默认仇恨范围过大）')
                elif md > 32:
                    bad(f'{ident} 的 max_dist={md} 过大（>32 格，容易无脑长途追人）')
        triggers = (comps.get('minecraft:damage_sensor') or {}).get('triggers') or []
        if not triggers:
            bad(f'{ident} 缺 damage_sensor（同族技能会互相打到，触发内讧）')
        else:
            first = triggers[0].get('on_damage') or {}
            flt = first.get('filters') or {}
            if not (flt.get('test') == 'is_family' and flt.get('value') == 'dragonkin'
                    and first.get('deals_damage') is False):
                bad(f'{ident} 的 damage_sensor 第一条不是「dragonkin 家族免伤」'
                    '（必须排第一，否则同族技能会打伤自己人并触发反击）')
            if not any(t.get('cause') == 'magic' and t.get('deals_damage') is False
                       for t in triggers):
                bad(f'{ident} 的 damage_sensor 缺「cause: magic 免伤」'
                    '（原版龙息云会伤到 BOSS 自己和幼龙）')
        bodies = [('components', comps)] + list((ent.get('component_groups') or {}).items())
        for where, body in bodies:
            if 'minecraft:behavior.hurt_by_target' in body:
                bad(f'{ident} 的 {where} 仍写着 hurt_by_target —— 被同族擦到会立刻反击，'
                    '是内讧的根；玩家目标交给 nearest_attackable_target')
            roar = body.get('minecraft:behavior.knockback_roar')
            if roar:
                for key in ('damage_filters', 'knockback_filters'):
                    f = roar.get(key) or {}
                    if not (f.get('test') == 'is_family' and f.get('value') == 'player'):
                        bad(f'{ident} 的 {where} knockback_roar 缺 {key} 玩家过滤'
                            '（默认打范围内所有实体，会误伤幼龙）')
            aa = body.get('minecraft:area_attack')
            if aa:
                f = aa.get('entity_filter') or {}
                if not (f.get('test') == 'is_family' and f.get('value') == 'player'):
                    bad(f'{ident} 的 {where} area_attack 没有限定玩家')
    print(f'仇恨与友伤: {sum(1 for p in data if os.sep + "entities" + os.sep in p)} 个实体检查完毕')


def check_id_registry(data):
    """离线对账：包内每个标识符都要在 docs/tools/id_registry.json 的 dragonkin-relic 名下。"""
    path = os.path.join(ROOT, 'docs', 'tools', 'id_registry.json')
    if not os.path.isfile(path):
        bad('缺 docs/tools/id_registry.json（跑 idreg mirror --pack 生成）')
        return
    snap = json.load(open(path, encoding='utf-8'))
    have = {(e['type'], e['key']) for e in snap.get('entries', [])
            if e.get('mod') == 'dragonkin-relic'}
    need = set()
    for sub, type_ in (('netease_blocks', 'block'), ('netease_items_beh', 'item')):
        d = os.path.join(BP, sub)
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if not f.endswith('.json'):
                continue
            key = f[:-5]
            if type_ == 'item' and key.startswith('zz_') and key.endswith('_egg'):
                need.add(('spawn_egg', key))
            else:
                need.add((type_, key))
    ent = os.path.join(BP, 'entities')
    if os.path.isdir(ent):
        for f in os.listdir(ent):
            if f.endswith('.json'):
                need.add(('entity', f[:-5]))
    tab = os.path.join(BP, 'netease_tab')
    if os.path.isdir(tab):
        for f in os.listdir(tab):
            if f.endswith('.json'):
                d = json.load(open(os.path.join(tab, f), encoding='utf-8'))
                for c in d.get('category', []):
                    need.add(('tab', c.get('name', '')))
    ui = os.path.join(RP, 'ui')
    if os.path.isdir(ui):
        for f in os.listdir(ui):
            key = f[:-5] if f.endswith('.json') else ''
            if key and key.isalnum() and key.islower() and key not in ('_ui_defs', 'neteasecommonui'):
                need.add(('ui_screen', key))
    for t, k in sorted(need - have):
        bad(f'{t} {k} 未在 ID 注册表登记（跑 idreg batch --action claim 补登记）')
    for t, k in sorted(have - need):
        bad(f'注册表登记了 {t} {k}，但包里扫不到（文件被删或改名没退登记）')
    print(f'ID 注册对账: 包内 {len(need)} 条 / 镜像 {len(have)} 条')


def check_scripts():
    """脚本护栏：RegisterSystem 的模块路径必须能落到真实的 文件.类；包内不许留 __pycache__/.pyc。"""
    import re
    dirs = [d for d in glob.glob(os.path.join(BP, '*')) if os.path.isfile(os.path.join(d, 'modMain.py'))]
    total = 0
    for d in dirs:
        # 网易引擎跑 Python 2：目录没有 __init__.py 就不是包，
        # 引擎日志会报 ImportError: No module named <目录>.modMain
        if not os.path.isfile(os.path.join(d, '__init__.py')):
            bad(f'{os.path.basename(d)}/ 缺 __init__.py（Python 2 下不算包，'
                '引擎 ImportModMain 会报 No module named ...）')
        src = open(os.path.join(d, 'modMain.py'), encoding='utf-8').read()
        for py in glob.glob(os.path.join(d, '*.py')):
            if py.endswith('modMain.py'):
                continue
            body = open(py, encoding='utf-8').read()
            if 'self.AddTimer(' in body:
                bad(f'{os.path.basename(py)} 用了 self.AddTimer —— ServerSystem 没有这个接口'
                    '（实测 AttributeError）；改用 CreateGame(levelId).AddTimer')
        for mod_path in re.findall(r"RegisterSystem\(\s*['\"][^'\"]+['\"]\s*,\s*['\"][^'\"]+['\"]\s*,"
                                   r"\s*['\"]([^'\"]+)['\"]", src):
            total += 1
            parts = mod_path.split('.')
            if len(parts) < 3:
                bad(f'{os.path.basename(d)}/modMain.py 的 RegisterSystem 路径不合规: {mod_path}')
                continue
            if parts[0] != os.path.basename(d):
                bad(f'{os.path.basename(d)}/modMain.py 的模块路径首段 {parts[0]}'
                    f' 与脚本目录名 {os.path.basename(d)} 不一致')
                continue
            rel = os.path.join(*parts[1:-1]) + '.py' if len(parts) > 2 else (parts[1] + '.py')
            fp = os.path.join(d, rel)
            if not os.path.exists(fp):
                bad(f'{os.path.basename(d)}/modMain.py 注册的 {mod_path} 找不到文件 {rel}')
                continue
            if ('class ' + parts[-1]) not in open(fp, encoding='utf-8').read():
                bad(f'{os.path.basename(d)}/{rel} 里没有 class {parts[-1]}')
    for path, _ in [(p, None) for p in glob.glob(os.path.join(ROOT, 'awesome_*', '**', '__pycache__'), recursive=True)]:
        bad(f'包内残留 __pycache__：{os.path.relpath(path, ROOT)}（红线 §1.6，打包会报 2000004）')
    for path in glob.glob(os.path.join(ROOT, 'awesome_*', '**', '*.pyc'), recursive=True):
        bad(f'包内残留 .pyc：{os.path.relpath(path, ROOT)}')
    if total:
        print(f'脚本: {len(dirs)} 个脚本目录 / {total} 条 RegisterSystem 路径已解析')


def check_tab(data, ids):
    """分页 + 分组：官方硬约束、覆盖完整性，以及组间排序键必须升序。"""
    tabs = [c for p, d in data.items()
            if os.sep + 'netease_tab' + os.sep in p for c in d.get('category', [])]
    if len(tabs) != 1:
        bad(f'netease_tab 期望 1 个分页，实际 {len(tabs)}')
    groups = []
    for p, d in data.items():
        if os.sep + 'netease_group' + os.sep in p:
            groups.extend(d.get('groups', []))
    lang = open(os.path.join(RP, 'texts', 'zh_CN.lang'), encoding='utf-8').read()

    for t in tabs:
        if t.get('sort_by_identifier') is not True:
            bad(f'分页 {t.get("name")} 的 sort_by_identifier 必须为 true'
                '（false 时组间与方块段是哈希序，实测不可控）')
        key = t.get('labelText', '')
        if key and f'{key}=' not in lang:
            bad(f'分页 {t.get("name")} 缺 lang 键 {key}')
        if not os.path.exists(os.path.join(RP, t.get('icon', '') + '.png')):
            bad(f'分页 {t.get("name")} 的 icon 贴图不存在: {t.get("icon")}')

    if not groups:
        bad('缺 netease_group：平铺 + sort_by_identifier 只能给字典序，顺序不可控')
    seen = {}
    for g in groups:
        name = g['group_name']
        lst = g['list']
        if len(lst) < 2:
            bad(f'分组 {name} 只有 {len(lst)} 件（官方：list 少于 2 件注册失败）')
        if g.get('icon') not in lst:
            bad(f'分组 {name} 的 icon 不在本组 list 内（官方：仅支持本组内物品）')
        if f'{name}=' not in lang:
            bad(f'分组 {name} 缺 lang 名（页面上会显示成键名）')
        for ident in lst:
            if ident not in ids:
                bad(f'分组 {name} 引用了不存在的物品/方块: {ident}')
            if ident in seen:
                bad(f'{ident} 同时在 {seen[ident]} 与 {name}（一件只能进一个分组）')
            seen[ident] = name
    keys = [g['list'][0] for g in groups if g['list']]
    if keys != sorted(keys):
        bad(f'组间顺序会乱：每组首件不是升序 {keys}（sort_by_identifier:true 时组间按首件排）')
    ungrouped = {f'fycq:{stem}' for stem in UNGROUPED}   # 白名单存语义名，比对用完整 id
    for ident in sorted(ids - set(seen)):
        if ident.startswith('fycq:') and ident not in ungrouped:
            bad(f'{ident} 既不在任何分组也不在 UNGROUPED 白名单（顺序不可控）')
    print(f'创造栏分页: {len(tabs)} 个 | 分组 {len(groups)} 组 / {len(seen)} 件'
          f' | 未分组 {len(UNGROUPED)} 件 | 组间排序键升序')


def main():
    data = check_json()
    beh, res = collect_items(data)
    check_items(data, beh, res)
    check_attachables(data, beh)
    check_blocks(data)
    ids = known_ids(data)
    check_tab(data, ids)
    check_recipes(data, ids)
    check_recipe_rules(data, beh)
    check_loot(data, ids)
    check_entities(data)
    check_skills(data)
    check_anim_overlay(data)
    check_aggression(data)
    check_weapon_balance(data)
    check_repair_paths(data)
    check_wing_edges()
    check_spawn_rules(data)
    check_whelp_flight(data)
    check_combat_scripts()
    check_skill_hud(data)
    check_breath()
    check_altar_summon()
    check_achievements(data)
    check_summon_cap(data)
    check_entity_events(data)
    check_id_registry(data)
    check_scripts()
    check_manifests(data)
    print()
    if fails:
        print(f'RESULT: {len(fails)} 项失败')
        sys.exit(1)
    print('RESULT: ALL PASS')


if __name__ == '__main__':
    main()
