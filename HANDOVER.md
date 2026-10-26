# Dragonkin Relic（封印&传奇：龙裔遗骸）接手文档

命名空间 `fycq`，版本 1.0.0，实体 `fycq:drasnea`（龙蛇 BOSS）。2026-10-26 从「只有一个粗糙 BOSS」改造成龙裔内容包，并由 MCStudio 工程名「龙蛇BOSS」改名为「龙裔遗骸」（包显示名、工程名、工作区目录名三层都改了；命名空间与 `fycq:drasnea` 按红线 §1.3 保持不动）。

## 1. 双源目录

| | 路径 |
|---|---|
| 工作区（改动源） | `D:\OraSkyC\CandySweet\模组开发\Project\Dragonkin Relic`（原名 `Drasnea BOSS`） |
| MCStudio 实机工程 | `D:\MCStudioDownload\work\a1213950265@163.com\Cpp\AddOn\263d057ad8d94c6e97a729a75bc412be` |
| 世界内嵌副本 | `%APPDATA%\MinecraftPE_Netease\games\com.netease\behavior_packs\awesome_behavior_packs`（进世界时由 MCStudio 刷新，不要手改） |

- 只同步 `awesome_behavior_packs/` 与 `awesome_resource_packs/`；`studio.json` / `work.mcscfg` 只属实机工程。
- 包 uuid：BP `e454a00c-ff76-4138-a2c5-586c59ba6a7e` / RP `b63887dc-72ff-479d-b984-c8135f0897cc`，**不要改**。
- 同步后必须**完全退出 MCStudio 再进世界**，改 UI/脚本 JSON 同理。

## 2. 生成器与体检（都在 `docs/tools/`，不进包）

| 脚本 | 作用 |
|---|---|
| `ids.py` | **identifier 与创造栏顺序唯一真源**：语义名 → 带序号的 identifier（`dragon_10_scale`…，间隔 10 便于插入）。三个 gen 脚本都从这里取 id，资产文件名仍用语义名，不受影响 |
| `palette.py` | **色阶唯一真源**（METAL/GOLD/BONE/BLOOD/WOOD 五条 0~1 ramp + OUTLINE），两个 draw 脚本都从这里取，不要在脚本里各存一份 |
| `draw_wave1.py` | 14 个物品图标（含刷怪蛋）+ 2 套 64×32 甲片（图标与甲片都在这，别再拆第二个写同路径的脚本） |
| `draw_wave2_blocks.py` | 8 张 16×16 方块贴图（色调场 + 左上倒角）+ 2×2 平铺预览 |
| `gen_creative_layout.py` | **创造栏分页唯一真源**：只写 `netease_tab/drasnea.json`（单页平铺 + `sort_by_identifier: true`）。本包**不用 `netease_group`**，见 §3.7 |
| `gen_wave1_items.py` | 物品 beh/res、attachables、item_texture、配方、BOSS 掉落（**不再写分页**） |
| `gen_wave2_blocks.py` | 方块定义、方块掉落、blocks.json、terrain_texture、配方 |
| `gen_wave3_mobs.py` | 三只生物：几何体（逐只手写骨盒 + UV 自动装箱）、贴图（按面光照+鳞纹）、三段动画、控制器、client_entity、实体定义、掉落表 |
| `gen_lang.py` | **zh_CN.lang 唯一写入口**（物品/方块/实体/分页名都在这，别在别的脚本里写 lang） |
| `check_pack.py` | 体检，见下 |

**美术做法（2026-10-26 第二版，作者要求「画精细一点」后改的）**：先量原版图标语汇（`preview/ref_vanilla_8x.png`：斜柄 + 3~4 阶金属 + 深色描边 + 柄头绑金，单件不透明色数 7~11、明度跨度 149~227），然后
① 工具/武器/盔甲 —— 取原版 `diamond_*` 的**剪影与明度分布**，按色相分成 描边/金属/握柄 三类，映射到龙裔色阶（青鳞金属 / 鎏金 / 骨白），再叠一层鳞纹；
② 龙血结晶 —— 原版 `diamond` 刻面宝石换色相；
③ 龙鳞/龙牙/龙心 —— 无可借的原版件，用已确认可辨认的轮廓 + 方向光 + 贴边环境遮蔽渲染；
④ 方块与甲片 —— 先出「色调场」（0~1 浮点 + 材料），再统一过左上倒角光照（环绕取样，平铺不裂）。
成品不透明色数 5~9，落进原版区间。**只借剪影与明度，颜色与图案都是本包自己的**；要换成全手绘就得重画，先跟作者确认。

重跑顺序：`draw_wave1 → draw_wave2_blocks → gen_wave1_items → gen_wave2_blocks → gen_creative_layout → gen_lang → check_pack → 同步 live`。

`check_pack.py` 覆盖：JSON 解析、物品 beh/res 配对、图标注册与文件存在、lang 名、创造栏分页存在性、attachable 与盔甲配对、方块 blocks.json/terrain_texture/掉落表/发光取值、配方引用与红线 §2.17/§1.5（行等长、≤3 行、key 全用到、产物不超堆叠）、实体结构（组件必须在 `components` 内）、manifest 引擎版本。红线类断言都用临时副本负测验证过能报。

## 3. 本包专属坑（都付过实机学费）

1. **`minecraft:block_light_emission.emission` 只接受 0.0–1.0**（全局红线 §2.13）。2026-10-26 写 `15` → 引擎 `Failed to upgrade to version '1.19.10'` → 方块不注册 → 配方 `Condition is false: res` **断言弹窗**。满亮度写 `1`，并配 `minecraft:block_light_absorption: 0`。守卫：`check_pack.py` 已加范围断言（负测验证过能报）。
2. **创造栏分页名用 `drasnea`，不是命名空间 `fycq`**。红线 §1.7 要求「分页名 = 命名空间」的前提是命名空间独占；本包与家具拓展共用 `fycq`，若也写 `fycq` 就正好触发它要避免的「多模组挤同一分页」。两包同档时物品分页互不干扰。
3. **盔甲不需要自建几何体**：attachables 直接引引擎内置 `geometry.humanoid.armor.helmet/chestplate/leggings/boots` + `controller.render.armor`，只需自制 64×32 甲片（`_1` 头/胸/靴，`_2` 护腿）。
4. **原版 Addon 目录里可以混放 `netease_*`**（参考包 zhxw / yijian 同时有 `items/` 与 `netease_items_beh/`），判定只看有没有 `netease_*`，不看包目录叫什么。
5. **实体 `format_version` 保持 1.13.0、模型保持 1.10.0 老格式**。参考包里 1.13.0 + `minecraft:boss` 已上线（白骨精 `baigujing3.json`），升级会改变可用组件集，需整包回归。
6. **龙蛇模型实测 4.44×4.2×7.61 格**（含旋转），碰撞箱只给 2.2×3.4；模型有约 1.08 格在脚底以下（尾巴下垂），改模型前要重算包围盒。
7. **创造栏顺序：唯一可控的组合是「分组 + `sort_by_identifier: true` + 每组首件当排序键」**（2026-10-26 三条路全实测过）。

   | 试过的配置 | 实测结果 |
   |---|---|
   | 平铺 + `sort_by_identifier: false` | 方块整段排到物品前面、**方块段是哈希序**（既非字典序也非书写序），物品段反而字典序 —— 不可控 |
   | 平铺 + 序号 identifier | 可控，但 ID 被编号污染，作者否掉 |
   | 分组 + `sort_by_identifier: false` | 组内按数组序，**组间仍是哈希序**（与 `groups` 书写顺序无关）—— 不可控 |

   可利用的规则（官方《13-自定义物品分页》+《12-自定义物品分组》）：`sort_by_identifier: true` 时**分组之间按每组 `list` 首件的 identifier 字典序排**，**组内按 `list` 数组序排**。所以把每组首件挑成升序，组间与组内就都可控，identifier 保持语义名。本包的排序键：
   `dragon_fang_sword`(工具组) < `dragon_scale_helmet`(盔甲组)。**2026-10-26 作者定稿：只有武器与盔甲成组**（这两类组内顺序有语义、需要固定），材料 4 件与方块 7 件留在组外按 identifier 排。
   **改任何一组的首件都会破坏组间顺序**，`check_pack.py` 的 `check_tab` 会断言「首件序列升序」，另含单件组、重复入组、icon 不在本组、漏排、缺 lang 名五类检查（都做过负测）。
   官方硬约束：`list` 少于 2 件**注册失败**、一件只能进一个分组、分组 `icon` 必须是本组内物品。材料/方块/刷怪蛋都不进组，走 `UNGROUPED` 白名单，与「每组首件」混排（官方第三条规则），蛋靠 `zz_` 收尾。
   代价（作者已接受）：两个组各有一个折叠芯片，芯片用该组 `icon` 再画一格，看起来像"重复条目"。
   配置真源：`gen_creative_layout.py`（`GROUPS` / `MATERIALS` / `BLOCKS` / `UNGROUPED`），identifier 真源：`ids.py`。
8. **物品/方块 ID 目前干净无序号**。`fycq:drasnea` 实体 ID 是原作者早期发布的，按红线 §1.3 永不改。若后续要接入 ID 注册表服务（cadt-windows:8444），登记的应是最终定稿的 ID；本包尚未接这个对账。
9. **动画控制器必须有 `initial_state`，且初始状态名用 `default`**（2026-10-26 作者反馈「生物的动画有问题」后查出）。我重写 BOSS 控制器时把原作者的状态名 `default` 换成了 `idle`、又没写 `initial_state` 字段 —— 结果整条控制器不进入任何状态，动画根本不播（新做的三只生物同错）。参考包（白骨精等）与官方《3-探索实体的资源控制》都是 `"initial_state": "default"` + 名为 `default` 的状态。顺带补了 `blend_transition: 0.2`，状态切换不再硬跳。
    另外两条同批修掉的：**循环动画的关键帧必须铺满 `animation_length`**（我们的 `move` 只铺到 0.36s / 长度 0.727s，播完会卡在最后一帧再跳回）；**动画驱动的腿骨名必须和模型一致**（幼龙是 `legFL/legFR/legBL/legBR`，人形是 `legL/legR`，写错就是原地滑步）。
    守卫：`check_entities` 现在断言 `initial_state` 存在、指向真实状态、且为 `default`；并对所有 `loop: true` 动画断言关键帧覆盖 ≥75% 循环长度、越界 ≤0.05s（四类违规都做过负测）。
10. **`.agents/tools/mc_preview` 的实体分支原来画错**（2026-10-26 已修）：它把 cube `origin` 当骨骼局部坐标（`origin - pivot`）并叠加父骨骼 pivot，而基岩实体几何体的 origin 是**模型绝对坐标**、pivot 只是旋转中心（拿参考模组验证：白骨精 head 在绝对 y 28~34，按局部会跑到 y 54+）。浅骨骼链（祭司/龙卫）看着没事，**深链（幼龙 body→neck→head→jaw、body→tail→tail2→tail3）会炸成散件**。现改为骨骼矩阵 `T(pivot)·R·T(-pivot)` + cube 绝对坐标；方块分支走 `collectModelFaces`，未受影响（已用星轨锅炉回归验证）。
   预览命令：`python .agents/tools/mc_preview/serve_preview.py "Project/Dragonkin Relic" --port 8811` → headless Chrome 截图**必须先写 ASCII 临时路径**（中文目录会失败），再拷回 `docs/tools/preview/`。

11. **零厚度方块必然自闪**（2026-10-26 作者反馈「龙蛇翅膀材质闪烁」后查出）：`size` 某一轴为 0 的 cube，正面与背面完全重合，同一个方块自己跟自己抢深度。本模型两翼三段膜 `leftwind/leftwind2/leftwind3` + `rightwind*` 共 **6 块**都是 `size[0]=0`。修法：**补 1 个单位（1 个纹素）居中厚度**（`fix_model_coplanar.py --write`），只动这 6 块、193 骨骼结构不变。
    ⚠ 2026-10-27 追加教训：**厚度不能用 0.05 这种亚像素值** —— 亚像素边缘面会被光栅化成 1px 细线（截图里翅膀边上的长直线），而且边缘面 UV 落在亚像素上会采到随机颜色。改成 1 纹素后边缘是一条正常的薄边；同时要在贴图上给边缘带补色，**只补「透明且未被其它部件占用」的像素**（本包补了 216 px；翅膜与 bone5/bone10/bone16 共用 UV 区，不能整片涂）。
    另：`leftwind3/rightwind3` 的 UV 展开总宽 162 > 贴图 128，但逐面矩形仍都在图内（右边界 127..128），不是溢出问题。
    检测工具 `analyze_model_flicker.py`：把 cube 的 6 面按骨骼链变换到模型空间、按「法线+平面偏移」分桶、桶内用**凸多边形真求交**算重叠面积。⚠ 不要用投影 AABB 近似——斜置的大膜片会被误判（初版因此把左右翼、bone55/bone2 全报成冲突）。
    现状：补厚后翅膀相关冲突清零，全模型仍余 **107 处**真重叠，集中在头部小骨 `bone100–bone118`（各 12–15 处）、`head/head`（12 面积）、`bone55/bone2`（9.5 面积）——这几处也会闪，但作者只报了翅膀，未处理。
    另：`mc_preview` **不认老格式 `geometry.xxx` 根键模型**，BOSS 预览会退化成蛋色占位块，所以 BOSS 模型改完只能靠数值 + 实机验证。

12. **纯 JSON 也能做状态机与技能**（2026-10-26，照参考包 sword_devil / 天启之境 melee_soldier 复刻）：
    - **攻击态**：`minecraft:behavior.delayed_attack` + 控制器读 `query.is_delayed_attacking == 1`（不需要脚本）
    - **受击态**：`damage_sensor.on_damage` 触发事件 → 加 `component_groups`（`minecraft:is_sheared` 当布尔标记 + `minecraft:timer` 0.45s）→ `time_down_event` 再触发移除 → 控制器读 `query.is_sheared` / `!query.is_sheared`。全库没有 `query.is_hurt`
    - **技能组件**：`knockback_roar`（震地击退）、`summon_entity`（召唤，`sequence[].entity_type` 必须是本包实体）、`area_attack`（范围伤害，`entity_filter` 限定玩家）、`leap_at_target`（扑咬）
    - **音效**：client_entity 的 `sound_effects` 把短名映射到音效事件（本包直接复用原版事件，无自研音频），动画时间轴用 `"sound_effects": {"0.3": {"effect": "attack"}}` 播放
    - 断言：`check_pack.py` 的 `check_skills` 校验「有 attack 态就必须有 delayed_attack」「damage_sensor/timer 触发的事件必须存在且互相对应」「受击组必须能被 timer 解除」「召唤目标必须是本包实体」（5 类违规都做过负测）

13. **脚本目录必须有 `__init__.py`**（2026-10-27 实机日志确认）：网易引擎跑 **Python 2**，目录没有 `__init__.py` 就不算包。症状是引擎日志里
    `LoadWindowsAddonPy: DrasneaProbe.modMain` 紧跟 `ImportError: No module named DrasneaProbe.modMain` —— 目录位置和加载流程都是对的，只差这个空文件。
    参考包 `customEntityModScripts/`、`Script_NeteaseMod001/` 都带一个 0 字节的 `__init__.py`。守卫：`check_scripts` 已断言。
    另：`studio.json` 的 `"CodeEnable": false` **不拦脚本加载**（该工程一直是 false，但引擎照样尝试 ImportModMain）。

14. **三只生物「无脑攻击 / 内讧 / 创造模式也打」的根因与修法**（2026-10-27 作者实机反馈）：
    - **内讧**：技能会伤到同族（祭司火球、龙卫震地），被打的怪走 `behavior.hurt_by_target` 反击，形成连锁。修法：所有龙裔在 `damage_sensor` 的 **第一条**加 `{on_damage: {filters: {test: is_family, subject: other, value: dragonkin}, deals_damage: false}}` —— 顺序必须在受击事件触发之前。
      ⚠ 2026-10-27 二修：**过滤是按「攻击者」的 family 判定的**，而 BOSS 的 `type_family` 当时漏了 `dragonkin`（只有 drasnea/monster/mob/boss/fycq），所以 BOSS 误伤幼龙时幼龙那边判不中 → 照样反打。BOSS 已补 `dragonkin`。
      再加一道脚本兜底：`aggroGuard.py` 每 5 tick 检查，**仇恨目标是本包另一个生物就 `SetAttackTarget(None)`**（弹射物伤害归属不一定算到施法者头上，JSON 层堵不严）。守卫：`check_aggression` 断言每个 fycq 实体的 family 必含 `dragonkin`。
    - **无脑攻击**：我原来写的是 `must_see: false` + `within_radius: 24`，等于隔墙全图仇恨且永不脱战。改成参考包 `guchengyuanling` 的原版派写法：`must_see: true` + 每类 `max_dist`（幼龙 12 / 龙卫 16 / 祭司 20 / BOSS 20）。
    - **创造模式也打**：官方文档与参考模组全库**没有** `is_creative` 这类过滤器测试，JSON 无解。只能脚本兜底：`aggroGuard.py` 每 5 tick 检查本包生物的 `GetAttackTarget()`，若目标是创造/旁观玩家就 `SetAttackTarget(None)`（`GameType.Creative=1 / Spectator=6`）。表现上是「盯着你但不追不打」，不是隐身。
    - 守卫：`check_pack.py` 的 `check_aggression` 断言「必须 `must_see: true`」「目标类型必须有 ≤32 的 `max_dist`」「`damage_sensor` 第一条必须是 dragonkin 免伤」（三类违规都做过负测）。

15. **脚本侧实机验证结果（2026-10-27，`[fycq-probe]` 日志）**：
    - 通过：`server/client system ready`、`AddEntityServerEvent`（entityTypeStr/pos 可读）、`ActorHurtServerEvent`（cause/damage 可读）、`CreateAttr().GetAttrValue(AttrType.HEALTH)` 血量读数（500→491→…→0.5 连续正确）、`MobDieEvent`（attacker/cause 可读）
    - 两个需要注意的点：
      1. **`ActorHurtServerEvent` 在死亡后会再触发一次**（日志里 `die` 之后还有一条 `hp=-8.5`）。以后用受伤事件做阶段切换必须加 `hp > 0` 守卫，否则会在尸体上触发
      2. `MobDieEvent.attacker` 在 MCStudio 单机下拿到的是 `-4294967295`（本地玩家伪 id），不是正常实体 id。做「首杀记给谁」时不能直接把它当玩家 id 用，需要用 `GetPlayerGameType`/玩家列表交叉验证

16. **「受击时动作被立马初始化」= 非叠加状态把 idle 的 root 动画清零**（2026-10-27 作者反馈）。龙蛇的 `animation.drasnea` 用 `root.position` 做悬空浮动（最高 26.5 单位），而 `hurt` 段没有 root、`attack` 段又自己写了 root 位移 —— 切进这些状态时 root 立刻回绑定姿势，整只看上去"弹回原位"。
    修法（两条都要）：① 状态里的动画**必须叠加 idle**（`["idle", "hurt"]` / `["idle", "attack"]`），让 root 始终有人驱动；② 叠加用的片段**不要再写 root**（attack 原有 root 位移已删）。
    BOSS 直接**取消受击态**（原版 BOSS 也没有受击动画），改用渲染控制器 `is_hurt_color: {r:1, g:0.25, b:0.25, a:0.55}` 红闪（`format_version` 需 1.10.0，参考 DeathAnimation 包）；同时删掉不再使用的 `animation.drasnea.hurt`、受击标记组与事件，客户端 `animations` 里的 `hurt` 短名也要一起去掉（否则 `check_entities` 会报未定义）。
    守卫：`check_anim_overlay` —— 只要 idle 动了 root，其它状态若不叠加 idle 且自身没 root 关键帧就报错（负测验证过）。

17. **ID 注册表接入（2026-10-27）**：本包原先在注册表里**没有模组条目**，因此不能注册任何新 ID。已通过 `/api/mods` 补上 `dragonkin-relic`（namespace `fycq`，pack_dir `Project/Dragonkin Relic`），并 `batch --action claim` 补齐存量 30 条（13 物品 / 7 方块 / 4 实体 / 4 蛋 / 1 分页 / 1 消耗品），`check --mod dragonkin-relic` 零欠账。
    同批修了两个共享客户端 bug（`.agents/tools/idreg/idreg.py`，不在本包仓库）：
    ① `SCAN` 写死 `behavior_pack/`，`awesome_behavior_packs/` 的包会被**空扫**——扫描不到任何键，`check` 永远报"无错账"。已加 `pack_dir()` 兼容三种包目录命名。
    ② `_meta_args()` 里引用了未定义的 `type_`，`claim`/`reserve` 带 `--mod` 且不填 `--namespace` 时直接 NameError。已改成 `getattr(a, "type", "")`。
    守卫：`check_pack.py` 的 `check_id_registry` 读 `docs/tools/id_registry.json`，离线断言「包内每个 ID 都登记、注册表每条都在包里」（双向）。

18. **血量阶段用脚本触发实体事件**（2026-10-27）：`bossPhase.py` 监听 `ActorHurtServerEvent`，读 `CreateAttr().GetAttrValue/GetAttrMaxValue(HEALTH)` 算比例，过阈值就 `CreateEntityEvent(entityId).TriggerCustomEvent(entityId, 'fycq:drasnea_phase2/3')`；实体侧用 `component_groups` + `events` 覆盖 `movement`/`attack`/`boss.name`/`knockback_roar`/`summon_entity`。
    **必须加 `hp > 0` 守卫**：实测死亡后还会再收到一次 `ActorHurtServerEvent`（hp=-8.5），不挡就会在尸体上触发阶段。
    守卫：`check_entity_events` 断言实体 `events` 增删的每个 `component_groups` 都真实存在。

## 4. 当前内容

- BOSS `fycq:drasnea`：500 血、29 组件、4 段动画（idle/move/attack/death）、原版 BOSS 血条、火球三连 + 冲撞、专属掉落、不自然刷怪（`spawn_rules` 已删，靠刷怪蛋/`/summon`）
- 18 物品：4 材料 + 龙牙剑 + 镐斧锹锄 + 龙鳞四件套 + 龙血凝露（饮用回血/抗性，返空瓶）+ 4 张刷怪蛋，外加 1 张显式刷怪蛋 `fycq:zz_drasnea_egg`（`custom_item_type: egg` + `netease:egg`，官方规范见《1-自定义物品/4-自定义生物蛋》，支持右键生成/刷怪笼/发射器；`zz_` 前缀让它排在分页末尾）
- 7 方块：龙鳞块 / 龙鳞砖 / 龙鳞柱 / 龙骨块 / 龙晶块 / 龙晶灯 / 龙巢
- 3 生物（波 3）：`dragon_whelp` 幼龙（30 血近战，掉龙鳞）、`dragon_priest` 龙祭司（60 血火球远程，掉龙鳞+龙血结晶）、`dragon_guard` 龙卫（120 血近战精英，掉龙牙+龙鳞）；各带几何体、64×128 贴图、idle/move/death 三段动画、控制器、渲染控制器、掉落表、`netease:egg` 刷怪蛋与原版音效绑定
- 每只生物 5 态动画：`idle / move / attack / hurt / death`（攻击态由延迟攻击驱动，受击态由受击标记驱动）
- **龙蛇三阶段**（脚本 `bossPhase.py`，阈值 66% / 33%）：phase2 移速 0.36 / 伤害 16 / 震地 CD 8 / **龙息火球 + 冲锋** / 血条「龙蛇·血怒」；phase3 移速 0.42 / 伤害 22 / 震地 CD 6 / **贴身灼烧 area_attack** / 血条「龙蛇·狂怒」
- **限量召唤**：JSON 的 `summon_entity` 全部移除（无数量上限），改由脚本每 10s 招一波；**按召唤者独立计数**：每只龙蛇最多 6 只、每只祭司最多 2 只；**蛋召/野生的幼龙不计入、不受限**
- **修复两条路**：① 所有有耐久装备加 `minecraft:repairable`（龙鳞/龙牙，每次 25% 耐久，待实机验证）；② 重铸配方 `损坏件 + 2 龙鳞 → 新件`（纯 JSON 保底，会重置耐久与附魔）
- 技能：BOSS 震地怒吼（击退 4 格、伤 10）+ 召唤 2 只幼龙；龙祭司召唤 1 只幼龙 + 火球；龙卫震地怒吼 + 贴身范围伤害；幼龙扑咬
- 音效：`sound_effects` 短名 + 动画时间轴播放（复用原版音效事件）
- 掉落：每只都有保底池 + 稀有池（`random_chance_with_looting` 受抢夺加成）：BOSS 35% 龙血结晶、龙卫 12% 龙血结晶、祭司 5% 龙心
- 20 配方（含 3 条反向拆解）；创造栏单页平铺 + 工具/盔甲两组
- 脚本 `DrasneaScripts`：`[fycq-probe]` 只读探针（已实机验证加载成功）+ `[fycq-guard]` 创造/旁观玩家不被追逐

## 5. 待办

- **波 3 收尾**：三只生物目前**只能靠刷怪蛋/`/summon` 出现**（没写 `spawn_rules`，不自然刷）；要不要给它们配自然刷怪群系、以及幼龙是否真要飞（现在 `has_gravity: true` 走地，翅膀只作动画）待定
- **实机验收**：三只的体型/剪影离线已用 mc_preview 核过（`preview/wave3_models_v2.png`），但动画播放、`query.is_charging` 攻击态、音效事件名、掉落表实际产出仍需进游戏确认
- **脚本只读探针（已实机验证通过，2026-10-27）**：`awesome_behavior_packs/DrasneaScripts/`（`modMain.py` + `probeServer.py` + `probeClient.py` + `aggroGuard.py`）。日志前缀 `[fycq-probe]`，判据：
  1. 进世界后出现 `server system ready` → ModSDK 加载成功
  2. 出现 `client system ready` → 客户端脚本也加载
  3. 召唤/生成本包生物 → `add fycq:dragon_whelp id=... pos=(...) hp=...`
  4. 打它一下 → `hurt fycq:... cause=... dmg=... hp=...`（证明能读血量）
  5. 打死 → `die fycq:... attacker=... cause=...`
  若**一条都没有**，先查 MCStudio 工程的 `studio.json` 里 `"CodeEnable": false` 是否门控脚本（本包一直是 false，未验证过含义）。
  探针通过后再做：血量三阶段、屏幕 BOSS 血条、祭坛交互召唤、首杀成就。
- **血量三阶段 / 屏幕血条 / 祭坛交互 / 首杀成就**：纯 JSON 做不到（网易无 BossBar 接口，实体 JSON 无血量过滤器），依赖上一条探针通过后再做
- 数值平衡：龙鳞获取量（BOSS 掉 4–8、幼龙 1–2、祭司 1–3、龙卫 2–4）与四件套成本（5/8/7/4）是否合理，等实机手感

## 6. 快照

`Project/.backup/2026-10-26-drasnea-before.zip`（改造前原始包）、`2026-10-26-drasnea-wave12.zip`（波 1+2 落地后）。本包无 git（按工作区约定不顺手 `git init`）。
