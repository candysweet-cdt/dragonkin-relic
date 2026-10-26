#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ── 这支工具是多份拷贝的同一个单文件，**权威源在运维仓库** ──────────────────────
#   权威：CaDt-Ops/tools/id-registry/client/idreg.py
#   副本：模组开发/.agents/tools/idreg/idreg.py + 三个包的 docs/tools/idreg.py
#   副本只许整体覆盖，不许就地改：
#       python tools/id-registry/client/sync_client.py --write   # 同步所有副本
#       python tools/id-registry/client/sync_client.py --check   # 只看是否漂移
#   包内守卫 check_id_registry.py 会比对包内副本与权威源，不一致就报红。
"""idreg —— 模组 ID 注册表的命令行客户端（纯 stdlib，给 agent 和生成器用）。

服务端与数据模型见运维仓库 `tools/id-registry/README.md`；本文件的 `--help` 只讲怎么调。

    环境变量：
      IDREG_URL    服务地址，默认 http://106.13.162.15:8444
      IDREG_TOKEN  写 token（**只从环境变量或文件读，不接受命令行传参** ——
                   命令行会进 shell 历史与进程列表）
      IDREG_TOKEN_FILE  token 文件路径（与 IDREG_TOKEN 二选一，后者优先）

    子命令：
      ping                         服务在不在线
      schema                       类型/键名规则/形态白名单/标签词表/必填字段/模组清单
      find   --type block --q botany [--status used] [--mod M] [--tab T]
      avail  --type block --prefix botany_ --mod growth-realm [--want 5]
      reserve --mod M --type block --key botany_x --theme botany --tab cadtgrow \
              --kind model --tags container,light --note "兰花塔同族" --holder cdt
      claim  …（同 reserve；把 reserved 转 used，或补登记存量）
      release --mod M --type block --key botany_x --reason "改主题前缀"
      batch  --file items.json [--action reserve] [--actor gen_theme_botany] [--dry-run]
      mod list                                   列出已登记的模组（免 token）
      mod add --code dragonkin-relic --name "封印之境·龙裔遗骸" --namespace fycq \
              --pack-dir "Project/Dragonkin Relic" --actor cdt
                                                 **新包第一件事**：登记模组，否则它的
                                                 ID 没有归属、`--mod` 校验直接不过
      mirror --pack "Project/Growth Realm"      拉快照落地成 docs/tools/id_registry.json
      check  --pack "Project/Growth Realm"      镜像 ↔ 包内实占 双向对账
                                                 （behavior_pack / behavior_packs /
                                                 awesome_behavior_packs / behavior_pack_xxx
                                                 四种工程目录名都认）

    退出码：0 成功；1 用法/参数错；2 服务不可达或未鉴权；3 对账发现「注册表声称有、
    包里却没有」的错账（这是唯一必须停下来问人的方向）。
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_URL = "http://106.13.162.15:8444"
TIMEOUT = 20

# 包内实占的扫描位置：type -> (相对包根的目录, 从 json 里取键的方式)
SCAN = {
    "block": ("behavior_pack/netease_blocks", None),
    # 实体蛋也是 items_beh 里的物品文件（zz_*_egg），单列一类才不会被 item 扫描漏掉/重复计
    "item": ("behavior_pack/netease_items_beh", lambda k: not (
        k.startswith("zz_") and k.endswith("_egg"))),
    "spawn_egg": ("behavior_pack/netease_items_beh",
                  lambda k: k.startswith("zz_") and k.endswith("_egg")),
    "entity": ("behavior_pack/entities", None),
}
# 这两类不在「目录里一个文件一个键」的模式里，单独扫
SCAN_SPECIAL = ("tab", "ui_screen")
UI_EXCLUDE = {"_ui_defs", "neteasecommonui"}
# 创造分页/主题的真源（各包自己的文件，注册表不抄）
TAB_SOURCES = ("docs/tools/creative_tabs.json",)
# 没有 creative_tabs.json 的包（生长之境 / 家具拓展），分页真源就是引擎读的那份
TAB_FALLBACK = "behavior_pack/netease_tab"   # 目录名的别名由 pack_subdir 统一去认


def pack_subdir(pack, rel):
    """`behavior_pack/netease_blocks` 这种相对路径 → 实际存在的目录；都没有就返回 None。

    实测存在的四种写法（MCStudio 会按工程形态改名，判定只看有没有 `netease_*` 目录）：
      `behavior_pack/`（工作区里的开发工程）
      `behavior_packs/`
      `awesome_behavior_packs/`（MCStudio 内容库工程，如龙裔遗骸）
      `behavior_pack_z6qLDV7H_d2286d12/`（MCStudio 导出时带随机后缀的实机工程）
    只认第一种会对后三种**全扫成空集**，`check` 于是静默报「无错账」—— 2026-10-27 实测踩过。
    """
    head, _, tail = rel.partition("/")
    stem = "behavior_pack" if head.startswith("behavior_pack") else "resource_pack"
    names = {stem, stem + "s", "awesome_" + stem + "s"}
    try:
        names.update(d for d in os.listdir(pack) if d.startswith(stem + "_"))
    except OSError:
        return None
    for name in sorted(names):
        p = os.path.join(pack, name, tail)
        if os.path.isdir(p):
            return p
    return None


class Down(Exception):
    pass


def _utf8():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def token():
    tok = os.environ.get("IDREG_TOKEN", "").strip()
    if tok:
        return tok
    path = os.environ.get("IDREG_TOKEN_FILE", "").strip()
    if path and os.path.isfile(path):
        return open(path, encoding="utf-8").read().strip()
    return ""


def base():
    return (os.environ.get("IDREG_URL") or DEFAULT_URL).rstrip("/")


def call(path, method="GET", body=None, auth=False):
    url = base() + path
    data = None
    req = urllib.request.Request(url, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    if auth:
        tok = token()
        if not tok:
            raise Down("没有写 token：设 IDREG_TOKEN 或 IDREG_TOKEN_FILE"
                       "（不要放命令行）。只读命令不需要它。")
        req.add_header("Authorization", "Bearer " + tok)
    try:
        with urllib.request.urlopen(req, data, timeout=TIMEOUT) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {"ok": False, "error": "HTTP %d" % e.code}
    except Exception as exc:
        raise Down("%s 不可达：%s: %s" % (base(), type(exc).__name__, str(exc)[:120]))


def die(msg, code=1):
    print("ERROR: " + msg, file=sys.stderr)
    sys.exit(code)


def show(result):
    print(json.dumps(result, ensure_ascii=False, indent=2))
    ok = isinstance(result, dict) and result.get("ok")
    return 0 if ok else 2


# ---------------- 实占扫描 ----------------

def scan_tab_names(pack):
    root = pack_subdir(pack, TAB_FALLBACK)
    out = set()
    if not root:
        return out
    for name in os.listdir(root):
        if not name.endswith(".json"):
            continue
        try:
            d = json.load(open(os.path.join(root, name), encoding="utf-8"))
        except (OSError, ValueError):
            continue
        out.update(c.get("name", "") for c in d.get("category", []))
    return out


def scan_ui_screens(pack):
    root = pack_subdir(pack, "resource_pack/ui")
    if not root:
        return set()
    return set(n for n in (os.path.splitext(f)[0] for f in os.listdir(root)
                           if f.endswith(".json"))
               if n.lower() not in UI_EXCLUDE and re.match(r"^[a-z0-9]+$", n))


def scan_pack(pack, type_):
    """返回包里真实占用的键集合（不含命名空间）；没有扫描源的类返回 None（跳过）。"""
    if type_ == "tab":
        return scan_tab_names(pack) or None
    if type_ == "ui_screen":
        return scan_ui_screens(pack) or None
    if type_ not in SCAN:
        return None
    rel, keep = SCAN[type_]
    root = pack_subdir(pack, rel)
    if not root:
        return None
    out = set()
    for name in sorted(os.listdir(root)):
        if not name.endswith(".json"):
            continue
        key = os.path.splitext(name)[0]
        if keep is None or keep(key):
            out.add(key)
    return out


def pack_namespace(pack):
    """从包内任一 json 里读 identifier 的命名空间（不猜、不写死）。"""
    for _t, (rel, _m) in SCAN.items():
        root = pack_subdir(pack, rel)          # 也要走别名，否则 awesome_* 包读不出命名空间
        if not root:
            continue
        for name in sorted(os.listdir(root)):
            if not name.endswith(".json"):
                continue
            try:
                text = open(os.path.join(root, name), encoding="utf-8").read()
            except OSError:
                continue
            m = re.search(r'"identifier"\s*:\s*"([a-z0-9_]+):', text)
            if m:
                return m.group(1)
    return ""


def tab_source_keys(pack):
    """本包创造分页与主题的合法集合（真源在包里，不在注册表）。"""
    for rel in TAB_SOURCES:
        p = os.path.join(pack, rel)
        if not os.path.isfile(p):
            continue
        d = json.load(open(p, encoding="utf-8"))
        tabs = set(t.get("name", "") for t in d.get("tabs", []))
        themes = set(d.get("theme_zh", {})) or set(d.get("themes", ()))
        return tabs, themes or None
    root = os.path.join(pack, TAB_FALLBACK)
    if os.path.isdir(root):
        tabs = set()
        for name in os.listdir(root):
            if not name.endswith(".json"):
                continue
            d = json.load(open(os.path.join(root, name), encoding="utf-8"))
            tabs.update(c.get("name", "") for c in d.get("category", []))
        if tabs:
            # 只校分页。主题不校：theme_id_map.json 是 10-22 那次迁移的**部分**映射
            # （只含当时 347 个方块），拿它当主题全集会把后来新增的 botany/farm 线
            # 全判成错账。主题只在包自己声明了全集时才校（见上面 creative_tabs 分支）。
            return tabs, None
    return None, None


# ---------------- 子命令 ----------------

def _same_dir(pack_dir, abs_pack):
    """`mods.pack_dir` 是工作区相对路径（Project/xxx），--pack 可能相对（cwd=工作区）
    也可能绝对 —— 两种都要能对上，所以比 全路径 与 「以该相对路径结尾」两种形态。"""
    pd = os.path.normcase(os.path.normpath(pack_dir)).strip(
        os.sep + (os.altsep or ""))            # Linux 上 os.altsep 是 None，别直接拼
    ap = os.path.normcase(os.path.normpath(abs_pack))
    return ap == os.path.normcase(os.path.abspath(pack_dir)) or \
        ap.endswith(os.sep + pd)


def scope_entries(snap, pack, mod=""):
    """把全库快照收窄到某个包。mirror 与 check 必须共用这一条式子 ——
    两边各写一份就会漂移：不带命名空间的类型（face_key/ui_screen/tab/lang_key）
    只按 namespace 过滤会被静默丢掉。
    返回 (entries, 说明)。
    """
    entries = snap.get("entries", [])
    if mod:
        return [e for e in entries if e.get("mod") == mod], "模组 " + mod
    # 先按 mods.pack_dir 精确命中本包：`fycq` 这类命名空间是**多个模组共用**的
    # （家具正式版 + 免费版 + 龙裔遗骸），只按命名空间收窄会把别的模组的行算成
    # 「注册表声称有、包里扫不到」的假错账。pack_dir 是登记模组时填的，可靠。
    abs_pack = os.path.abspath(pack)
    hits = sorted(m["code"] for m in snap.get("mods", [])
                  if m.get("pack_dir") and _same_dir(m["pack_dir"], abs_pack))
    if len(hits) == 1:
        return ([e for e in entries if e.get("mod") == hits[0]],
                "模组 %s（按 mods.pack_dir 命中本包）" % hits[0])
    ns = pack_namespace(pack)
    if not ns:
        return entries, "全库"
    mods = set(m["code"] for m in snap.get("mods", []) if m.get("namespace") == ns)
    kept = [e for e in entries
            if e.get("namespace") == ns
            or (not e.get("namespace") and e.get("mod") in mods)]
    spanned = sorted(set(e.get("mod") for e in kept))
    hint = ("（⚠️ 这批行跨 %d 个模组：%s —— 显式加 --mod 才是本包的账）"
            % (len(spanned), ",".join(spanned))) if len(spanned) > 1 else ""
    return kept, "命名空间 %s / 模组 %s%s" % (ns, ",".join(sorted(mods)) or "-", hint)


def cmd_ping(_a):
    code, r = call("/api/health")
    print("%s -> %s" % (base(), json.dumps(r, ensure_ascii=False)))
    return 0 if code == 200 and r.get("ok") else 2


def cmd_schema(_a):
    code, r = call("/api/schema")
    if code != 200:
        return show(r)
    print("类型：" + ", ".join("%s(%s)" % (k, v) for k, v in sorted(r["types"].items())))
    for t in sorted(r["required_fields"]):
        print("  %-10s 必填 %-45s 形态 %s" % (
            t, "/".join(r["required_fields"][t]), "|".join(r["kinds"][t])))
    print("标签：" + ", ".join(sorted(r["tags"])))
    print("模组：" + ", ".join("%s=%s" % (m["code"], m["namespace"]) for m in r["mods"]))
    print("键名规则：" + json.dumps(r["key_patterns"], ensure_ascii=False))
    return 0


_SCHEMA_CACHE = {}


def cmd_mod(a):
    """模组台账：`list` 列出；`add` 登记/更新一个模组（新包第一次注册 ID 之前先跑它）。

    服务端是 upsert：`code` 已存在就更新信息字段；但**已经挂上 ID 的模组不许改命名空间**
    （会撕裂既有记录），那种情况服务端返回 409。
    """
    if a.op == "list":
        code, r = call("/api/mods")
        if code != 200:
            return show(r)
        for m in (r.get("mods") if isinstance(r, dict) else r) or []:
            extra = ("  iid=%s 模组码=%s" % (m.get("iid"), m.get("modcode"))
                     if m.get("iid") or m.get("modcode") else "")
            print("%-22s %-10s %s%s" % (m["code"], m.get("namespace", ""),
                                        m.get("name_zh", ""), extra))
        return 0
    if not a.name or not a.namespace:
        die("add 需要 --name（中文名）与 --namespace；命名空间从包里任一 identifier "
            "读（`grep -m1 identifier` 任一 json），别猜")
    body = {"code": a.code, "name_zh": a.name, "namespace": a.namespace,
            "iid": a.iid or "", "modcode": a.modcode or "",
            "pack_dir": a.pack_dir or "", "note": a.note or "",
            "actor": a.actor or ""}
    code, r = call("/api/mods", "POST", body, auth=True)
    if code == 409:
        print("拒绝：%s" % r.get("error"), file=sys.stderr)
        return 2
    return show(r)


def schema():
    if not _SCHEMA_CACHE:
        code, r = call("/api/schema")
        if code != 200:
            raise Down("取 /api/schema 失败：HTTP %d" % code)
        _SCHEMA_CACHE.update(r)
    return _SCHEMA_CACHE


def mod_namespace(mod):
    for m in schema().get("mods", []):
        if m["code"] == mod:
            return m.get("namespace", "")
    return None


NS_SPLIT = ("block", "item", "entity", "spawn_egg")


def _meta_args(a):
    m = {}
    for k in ("mod", "namespace", "theme", "tab", "kind"):
        v = getattr(a, k, None)
        if v:
            m[k] = v
    # 模组登记时就带了命名空间，别再让调用方填一遍（填错反而是错账）。
    # 但只有「键本身带命名空间」的四类才填：face_key / ui_screen / tab / lang_key 的键
    # 不属于任何包命名空间，填了会让「客户端写的」和「裸调 API 写的」两种形态并存。
    if m.get("mod") and not m.get("namespace") and getattr(a, "type", "") in NS_SPLIT:
        ns = mod_namespace(m["mod"])
        if ns is None:
            raise Down("模组 %s 未登记；先 POST /api/mods 或网页登记，再注册 ID" % m["mod"])
        m["namespace"] = ns
    if getattr(a, "tags", None):
        m["tags"] = [x.strip() for x in a.tags.split(",") if x.strip()]
    return m


def cmd_write(a, action):
    body = {"type": a.type, "key": a.key, "holder": a.holder or "",
            "note": getattr(a, "note", "") or ""}
    body.update(_meta_args(a))
    if a.cmd == "release":
        body.pop("namespace", None) if not body.get("namespace") else None
    if action == "reserve" and a.days:
        body["days"] = a.days
    if action == "release":
        body["reason"] = getattr(a, "reason", "") or ""
    code, r = call("/api/" + action, "POST", body, auth=True)
    if code == 409 and action == "reserve" and r.get("taken"):
        t = r["taken"]
        print("撞车：%s 已被 %s（模组 %s / 主题 %s / 备注 %s）占用"
              % (t["full_key"], t.get("holder") or "?", t.get("mod"), t.get("theme"),
                 t.get("note")), file=sys.stderr)
        return 2
    return show(r)


def cmd_find(a):
    q = {k: v for k, v in (("type", a.type), ("q", a.q), ("status", a.status),
                           ("mod", a.mod), ("tab", a.tab), ("theme", a.theme),
                           ("tag", a.tag)) if v}
    code, r = call("/api/ids?" + urllib.parse.urlencode(q))
    if code != 200:
        return show(r)
    rows = r.get("ids", [])
    for e in rows:
        print("%-10s %-42s %-8s %-14s %-10s %-22s %s" % (
            e["type"], e["full_key"], e["status"], e["mod"], e["theme"], e["tab"],
            ",".join(e["tags"])))
    print("共 %d 条" % len(rows))
    return 0


def cmd_avail(a):
    q = {"type": a.type, "want": a.want}
    if a.prefix:
        q["prefix"] = a.prefix
    if a.mod:
        q["mod"] = a.mod
    if a.namespace:
        q["namespace"] = a.namespace
    code, r = call("/api/available?" + urllib.parse.urlencode(q))
    show(r)
    return 0 if code == 200 else 2


def cmd_batch(a):
    if not os.path.isfile(a.file):
        die("找不到 --file %s" % a.file)
    items = json.load(open(a.file, encoding="utf-8"))
    if isinstance(items, dict):
        items = items.get("items", [])
    # 批量路径也要自动填命名空间 —— 这条正是生成器用的，漏了它等于逼调用方手填易错字段
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        mod = (item.get("mod") or (item.get("meta") or {}).get("mod") or "")
        if not mod:
            continue
        ns = mod_namespace(mod)
        if ns is None:
            die("第 %d 条的模组 %s 未登记（先跑 schema 看 mods 清单）" % (i, mod))
        for holder in (item, item.get("meta") or {}):
            if isinstance(holder, dict) and not holder.get("namespace"):
                holder["namespace"] = ns
    body = {"action": a.action, "items": items, "dry_run": bool(a.dry_run)}
    if a.actor:
        body["actor"] = a.actor
    code, r = call("/api/batch", "POST", body, auth=True)
    print("applied=%s total=%s failed=%s dry_run=%s"
          % (r.get("applied"), r.get("total"), r.get("failed"), r.get("dry_run")))
    for it in r.get("results", []):
        if it.get("http", 200) >= 400:
            print("  [%d] %s -> %s" % (it["index"], it.get("key"), it.get("error")))
    return 0 if code == 200 and r.get("ok") else 2


def resolve_pack_mod(pack, mod=""):
    """本包对应哪个模组代号：显式 --mod 优先，其次按 `mods.pack_dir` 精确命中（唯一命中才算）。
    命中不了返回 ""（调用方回落到按命名空间收窄）。"""
    if mod:
        return mod
    code, r = call("/api/mods")
    if code != 200:
        return ""
    abs_pack = os.path.abspath(pack)
    hits = sorted(m["code"] for m in (r.get("mods") if isinstance(r, dict) else r) or []
                  if m.get("pack_dir") and _same_dir(m["pack_dir"], abs_pack))
    return hits[0] if len(hits) == 1 else ""


def cmd_mirror(a):
    # 能确定是本包哪个模组就找服务端按模组收窄：counts/breakdown 会跟着收窄，
    # 镜像里就不会带全库统计（否则别的包一登记 ID，本包镜像凭空多出几十行 diff）。
    scoped_mod = "" if a.all_ else resolve_pack_mod(a.pack, a.mod)
    url = "/api/snapshot" + ("?mod=" + urllib.parse.quote(scoped_mod) if scoped_mod else "")
    code, r = call(url)
    if code != 200:
        return show(r)
    out = os.path.join(a.pack, "docs", "tools", "id_registry.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    # 默认只留本包命名空间的记录：跨包同名本来就合法（命名空间不同），
    # 把全库快照塞进每个包既白占仓库体积（实测 1.1MB/包），也没带来碰撞信息。
    total = len(r["entries"])
    if a.all_:
        entries, scope = r["entries"], "全库"
    else:
        entries, scope = scope_entries(r, a.pack, scoped_mod)
    if scoped_mod and (r.get("scoped") or {}).get("mod") != scoped_mod and total != len(entries):
        print("⚠️ 服务端没按 mod 收窄统计（老部署）—— 镜像里的 counts/breakdown 仍是全库口径，"
              "重新部署服务端即可")
    r["entries"] = entries
    r["scoped_to"] = scope
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(r, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    print("落地 %s（%s：%d/%d 条，%dKB）"
          % (out, scope, len(r["entries"]), total, os.path.getsize(out) // 1024))
    return 0


def cmd_check(a):
    mirror = os.path.join(a.pack, "docs", "tools", "id_registry.json")
    if not os.path.isfile(mirror):
        die("先跑 mirror：没有 %s" % mirror, 2)
    snap = json.load(open(mirror, encoding="utf-8"))
    entries = [e for e in snap.get("entries", []) if not a.mod or e["mod"] == a.mod]
    # 不给 --mod 时按本包命名空间自动收窄：否则会把别的模组的记录拿去对着本包扫，
    # 报出一堆「包里扫不到」的假错账（实测踩过）。
    before = len(entries)
    entries, scope = scope_entries(snap, a.pack, a.mod)
    print("作用域：%s（%d/%d 条）" % (scope, len(entries), before))
    tabs, themes = tab_source_keys(a.pack)
    bad_claim, missing, bad_enum = [], [], []
    for e in entries:
        real = scan_pack(a.pack, e["type"])
        if real is None:
            continue
        if e["key"] not in real:
            bad_claim.append(e)                      # 注册表说有、包里没有 ⇒ 错账
    universe = sorted(set(SCAN) | set(SCAN_SPECIAL))
    for t in (a.types or universe):
        real = scan_pack(a.pack, t)
        if real is None:
            continue
        reg = set(e["key"] for e in entries if e["type"] == t)
        missing.append((t, sorted(real - reg)))
    for e in entries:
        if tabs and e.get("tab") and e["tab"] not in tabs:
            bad_enum.append((e["full_key"], "tab", e["tab"]))
        if themes and e.get("theme") and e["theme"] not in themes:
            bad_enum.append((e["full_key"], "theme", e["theme"]))

    print("镜像 %s（schema v%s，%d 条）" % (mirror, snap.get("schema"), len(entries)))
    if bad_claim:
        print("🔴 注册表声称有、包里扫不到（多半是记错了模组/键名）：")
        for e in bad_claim[:10]:
            print("   %s  mod=%s tab=%s" % (e["full_key"], e["mod"], e["tab"]))
        if len(bad_claim) > 10:
            print("   …另有 %d 条（完整清单看 mirror 落地文件）" % (len(bad_claim) - 10))
    if bad_enum:
        print("🔴 tab/theme 不在本包真源里：")
        for k, field, val in bad_enum:
            print("   %s  %s=%s" % (k, field, val))
    total_missing = 0
    for t, keys in missing:
        total_missing += len(keys)
        print("⚪ %s：包内 %d 个未登记（前 5：%s）"
              % (t, len(keys), ", ".join(keys[:5])))
    if not bad_claim and not bad_enum:
        print("✅ 无错账；未登记 %d 个待补%s" % (
            total_missing,
            "（--strict-unregistered 已开：非零即退出码 3）" if a.strict_unregistered
            else "（不阻断，除非 --strict-unregistered）"))
    if a.strict_unregistered and total_missing:
        return 3
    return 3 if (bad_claim or bad_enum) else 0


# ---------------- 入口 ----------------

def build():
    ap = argparse.ArgumentParser(
        prog="idreg", description="模组 ID 注册表客户端（详见文件头 docstring）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("ping").set_defaults(fn=cmd_ping)
    sub.add_parser("schema").set_defaults(fn=cmd_schema)

    p = sub.add_parser("find")
    for k in ("--type", "--q", "--status", "--mod", "--tab", "--theme", "--tag"):
        p.add_argument(k, default="")
    p.set_defaults(fn=cmd_find)

    p = sub.add_parser("avail")
    p.add_argument("--type", required=True)
    p.add_argument("--prefix", default="")
    p.add_argument("--mod", default="")
    p.add_argument("--namespace", default="")
    p.add_argument("--want", type=int, default=5)
    p.set_defaults(fn=cmd_avail)

    for name, fn in (("reserve", cmd_write), ("claim", cmd_write),
                     ("release", cmd_write)):
        p = sub.add_parser(name)
        p.add_argument("--type", required=True)
        p.add_argument("--key", required=True)
        p.add_argument("--mod", default="")
        p.add_argument("--namespace", default="")
        p.add_argument("--theme", default="")
        p.add_argument("--tab", default="")
        p.add_argument("--kind", default="")
        p.add_argument("--tags", default="")
        p.add_argument("--note", default="")
        p.add_argument("--holder", default="")
        p.add_argument("--days", type=int, default=0)
        p.add_argument("--reason", default="")
        p.set_defaults(fn=fn, action=name)

    p = sub.add_parser("mod", help="模组台账：新包先登记模组，再注册它的第一个 ID")
    mp = p.add_subparsers(dest="op", required=True)
    mp.add_parser("list", help="列出已登记模组（免 token）")
    q = mp.add_parser("add", help="登记/更新一个模组（要写 token）")
    q.add_argument("--code", required=True, help="模组代号，如 dragonkin-relic")
    q.add_argument("--name", required=True, help="中文名，如 封印之境·龙裔遗骸")
    q.add_argument("--namespace", required=True, help="命名空间，如 fycq（同空间=共用键池）")
    q.add_argument("--iid", default="", help="平台 iid（可后补）")
    q.add_argument("--modcode", default="", help="模组码（可后补）")
    q.add_argument("--pack-dir", dest="pack_dir", default="",
                   help="工程目录，如 Project/Dragonkin Relic")
    q.add_argument("--note", default="")
    q.add_argument("--actor", default="", help="谁登记的（进审计流水）")
    p.set_defaults(fn=cmd_mod)

    p = sub.add_parser("batch")
    p.add_argument("--file", required=True)
    p.add_argument("--action", default="reserve",
                   choices=("reserve", "claim", "release"))
    p.add_argument("--actor", default="")
    p.add_argument("--dry-run", dest="dry_run", action="store_true")
    p.set_defaults(fn=cmd_batch)

    p = sub.add_parser("mirror")
    p.add_argument("--pack", required=True)
    p.add_argument("--mod", default="")
    p.add_argument("--all", dest="all_", action="store_true",
                   help="落全库快照（默认只落本包命名空间，省仓库体积）")
    p.set_defaults(fn=cmd_mirror)

    p = sub.add_parser("check")
    p.add_argument("--pack", required=True)
    p.add_argument("--mod", default="")
    p.add_argument("--types", default="", help="逗号分隔，默认扫 block/item/entity")
    p.add_argument("--strict-unregistered", dest="strict_unregistered",
                   action="store_true")
    p.set_defaults(fn=cmd_check)
    return ap


def main(argv=None):
    _utf8()
    ap = build()
    a = ap.parse_args(argv)
    if getattr(a, "types", ""):
        a.types = [x.strip() for x in a.types.split(",") if x.strip()]
    else:
        a.types = None
    try:
        if a.cmd in ("reserve", "claim", "release"):
            return a.fn(a, a.action)
        return a.fn(a)
    except Down as exc:
        die("%s\n⇒ 注册表不可用时**停下来报告**，不许先建 ID 再补登记，也不许静默跳过。" % exc, 2)


if __name__ == "__main__":
    sys.exit(main())
