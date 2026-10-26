"""Drasnea BOSS 包体检：结构、引用完整性、注册一致性。

用法：python docs/tools/check_pack.py
任何 FAIL 都会以非零退出。
"""
import glob
import json
import os
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
