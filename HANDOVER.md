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
8. **物品/方块 ID 目前干净无序号**。`fycq:drasnea` 实体 ID 是原作者早期发布的，按红线 §1.3 永不改。本包已接入 ID 注册表服务（cadt-windows:8444，模组条目 `dragonkin-relic`，见教训 17），新增标识符一律 `reserve → claim → mirror → check`。
9. **动画控制器必须有 `initial_state`，且初始状态名用 `default`**（2026-10-26 作者反馈「生物的动画有问题」后查出）。我重写 BOSS 控制器时把原作者的状态名 `default` 换成了 `idle`、又没写 `initial_state` 字段 —— 结果整条控制器不进入任何状态，动画根本不播（新做的三只生物同错）。参考包（白骨精等）与官方《3-探索实体的资源控制》都是 `"initial_state": "default"` + 名为 `default` 的状态。顺带补了 `blend_transition: 0.2`，状态切换不再硬跳。
    另外两条同批修掉的：**循环动画的关键帧必须铺满 `animation_length`**（我们的 `move` 只铺到 0.36s / 长度 0.727s，播完会卡在最后一帧再跳回）；**动画驱动的腿骨名必须和模型一致**（幼龙是 `legFL/legFR/legBL/legBR`，人形是 `legL/legR`，写错就是原地滑步）。
    守卫：`check_entities` 现在断言 `initial_state` 存在、指向真实状态、且为 `default`；并对所有 `loop: true` 动画断言关键帧覆盖 ≥75% 循环长度、越界 ≤0.05s（四类违规都做过负测）。
10. **`.agents/tools/mc_preview` 的实体分支原来画错**（2026-10-26 已修）：它把 cube `origin` 当骨骼局部坐标（`origin - pivot`）并叠加父骨骼 pivot，而基岩实体几何体的 origin 是**模型绝对坐标**、pivot 只是旋转中心（拿参考模组验证：白骨精 head 在绝对 y 28~34，按局部会跑到 y 54+）。浅骨骼链（祭司/龙卫）看着没事，**深链（幼龙 body→neck→head→jaw、body→tail→tail2→tail3）会炸成散件**。现改为骨骼矩阵 `T(pivot)·R·T(-pivot)` + cube 绝对坐标；方块分支走 `collectModelFaces`，未受影响（已用星轨锅炉回归验证）。
   预览命令：`python .agents/tools/mc_preview/serve_preview.py "Project/Dragonkin Relic" --port 8811` → headless Chrome 截图**必须先写 ASCII 临时路径**（中文目录会失败），再拷回 `docs/tools/preview/`。

11. **零厚度方块必然自闪**（2026-10-26 作者反馈「龙蛇翅膀材质闪烁」后查出）：`size` 某一轴为 0 的 cube，正面与背面完全重合，同一个方块自己跟自己抢深度。本模型两翼三段膜 `leftwind/leftwind2/leftwind3` + `rightwind*` 共 **6 块**都是 `size[0]=0`。修法：**补 1 个单位（1 个纹素）居中厚度**（`fix_model_coplanar.py --write`），只动这 6 块、193 骨骼结构不变。
    ⚠ 2026-10-27 追加教训：**厚度不能用 0.05 这种亚像素值** —— 亚像素边缘面会被光栅化成 1px 细线（截图里翅膀边上的长直线），而且边缘面 UV 落在亚像素上会采到随机颜色。改成 1 纹素后边缘是一条正常的薄边；同时要在贴图上给边缘带补色，**只补「透明且未被其它部件占用」的像素**（本包补了 216 px；翅膜与 bone5/bone10/bone16 共用 UV 区，不能整片涂）。
    另：`leftwind3/rightwind3` 的 UV 展开总宽 162 > 贴图 128，但逐面矩形仍都在图内（右边界 127..128），不是溢出问题。
    ⚠ 2026-10-27 二次实机：加厚到 1 纹素后，±Z/±Y 四个 1px 侧面会沿整块 cube 的矩形描出**悬浮黑框**（透明区也被描边，截图确认）。侧面 UV 条带必须清成透明；但 x=18、x=86/87 等 36 个纹素与爪子/角/相邻翅膜的宽面共用，不能整条清。脚本 `fix_wing_edge_strips.py` 只清「属侧面条带且未被其它面覆盖」的 230 个纹素；守卫 `check_wing_edges` 断言没有不透明残留（注入 1 px 即报错）。
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

19. **装备修复的现实约束（2026-10-27 实机确认）**：铁砧的修复材料由 `netease:weapon.level` 决定（0 木/金…3 钻石），给了 level 3 就只认**钻石**；`minecraft:repairable` 实测**不生效**（它不在网易文档的支持组件清单里，参考包也无人用过），已从 9 件装备上撤掉。
    盔甲没有 level 字段，也**没有修复材料字段**，铁砧完全修不了（实机：放龙鳞无产出）。
    因此龙鳞修复改走**龙巢交互**（`DrasneaScripts/repairStation.py`，监听 `ServerBlockUseEvent`）：主手/副手拿装备右键龙巢，1 龙鳞 = 25% 最大耐久（向上取整），保留附魔与自定义名；合成台另留 `repair_<id>` 重铸配方（装备 + 2 龙鳞 → 新件，会重置耐久与附魔）。
    两个脚本细节：`ServerBlockUseEvent` 才是**自定义方块**的右键事件（`ServerItemUseOnEvent` 对带使用逻辑的方块不触发）；`SetItemDurability` 在方块/物品事件里直接调用会失效，必须 `AddTimer(0.05)` 延后。
    守卫：`check_repair_paths` 要求每件有耐久的装备都有重铸配方、**禁止** `minecraft:repairable`，且 `repairStation.py` 的 GEAR 必须覆盖全部有耐久装备。

20. **龙巢召唤 + 自定义成就（2026-10-27）**：两套机制都监听 `ServerBlockUseEvent`（自定义方块右键），按手持物分流：龙心 = 召唤、龙裔装备 = 修复。
    召唤前用 `CreateGame(playerId).GetEntitiesAround(playerId, 32, {'test': 'is_family', 'subject': 'other', 'value': 'drasnea'})` 防叠 BOSS，`CreateBlockInfo(levelId).GetBlockNew(...)` 检查上方 4 格净空；`CreateEngineEntityByTypeStr` 必须传维度，否则会默认生成在主世界。
    成就节点放 `awesome_behavior_packs/customAchievements/*.json`：图标写 `textures/items/xxx`（不带 `.png`，相对资源包根）；本包**不配 `goal_details`**，由 `achievementServer.py` 在 `MobDieEvent` 里 `CreateAchievement(levelId).SetNodeFinish(playerId, nodeId)`，和奖励同批触发、按玩家各算一次；玩家标记走 `CreateExtraData(playerId)`（随存档保存）。
    教程示例的 `window_background: textures/ui/background/sign_warped` **在本版本不存在**，实机会整页紫黑格；改用包内 64×64 无缝龙鳞瓦片 `textures/ui/dragonkin_achievement_bg`（`docs/tools/draw_achievement_bg.py` 生成，引擎按背景板平铺）。守卫会断言根节点背景图真实存在。
    奖励用 `SpawnItemToPlayerInv`，返回 False（背包满）时用 `CreateEngineItemEntity` 掉在脚下；`MobDieEvent` 回调里不能改手持物品，发奖/发提示统一 `AddTimer(0.05)` 延后。
    守卫：`check_altar_summon` / `check_achievements`（脚本常量、modMain 注册、节点字段、图标存在、finish_tip、脚本覆盖 node_ID）。

21. **实机三连修正（2026-10-27 晚，作者报「幼龙还击后 BOSS 跑掉」「击杀不结算」「龙息不消失且自伤」）**：
    - `ServerSystem` **没有 `AddTimer`**：实机 `AttributeError: 'AchievementServer' object has no attribute 'AddTimer'`。定时器一律用 `CreateGame(levelId).AddTimer(delay, func, *args)`；`repairStation` / `achievementServer` / `dragonBreath` 已改，守卫禁止脚本出现 `self.AddTimer(`。
    - `MobDieEvent.attacker` 是占位 id（实测 `-4294967295`），不能认击杀者。改为 `PlayerAttackEntityEvent` 记最近一次玩家攻击 + `ActuallyHurtServerEvent`（`projectileId` → `CreateBulletAttributes(pid).GetSourceEntityId()`）兜底，60 秒内有效；首杀标记换成 `..._v2`，旧版报错那次的玩家再杀一只即可结算。
    - 内讧根因：`knockback_roar` 默认打范围内**所有**实体（没有过滤），龙息云也会伤同族。三处 roar 都已加 `damage_filters` / `knockback_filters` 玩家过滤；四只实体删掉 `behavior.hurt_by_target`（被擦到就反击）；`damage_sensor` 增加 `cause: magic` 免伤（原版龙息云的 potion 伤害）。
    - 原版 `dragon_fireball` 的 `spawn_aoe_cloud.duration = 120` 秒，太长；`dragonBreath.py` 追踪 BOSS 发射的龙息球，命中后 5 秒销毁对应 `minecraft:area_effect_cloud`（其它云不动）。
    守卫：`check_aggression` 新增「禁 hurt_by_target / roar 必须玩家过滤 / magic 免伤」；`check_breath` 校验脚本与注册；`check_scripts` 禁 `self.AddTimer(`。

22. **自然刷怪 + 幼龙飞行 + 成就树 + 首召闭环（2026-10-27）**：
    - `spawn_rules` 放 `awesome_behavior_packs/spawn_rules/<stem>.json`，条件用 `spawns_on_surface` + `brightness_filter` + `difficulty_filter` + `weight` + `herd` + `biome_filter`；BOSS 不写规则。三只小怪加 `minecraft:despawn` 防越积越多。
    - 幼龙真飞：先用蜜蜂/悦灵那套 `navigation.hover` + `random_hover`，**实机只会原地悬停打转**（作者反馈）；改成鹦鹉式 `navigation.fly` + `movement.fly` + `behavior.random_fly`（xz 15 / y 4）+ `physics.has_gravity:false`，并删掉 `navigation.walk` / `movement.basic` / `random_stroll` / `leap_at_target`。
    - 自定义成就树：子节点 `parent_node` 指 `fycq_dragonkin_first_kill`；10 杀幼龙用 `goal_details.default_kill` 自动记；首召在 `altarSummon` 成功后 `SetNodeFinish`；四件套由 `achievementServer` 每 5 秒扫背包+盔甲后 `SetNodeFinish`。
    - **首召闭环**：首召 8 龙鳞（世界标记 `fycq_drasnea_ever_summoned`），之后 1 龙心 + 4 龙鳞；祭司 5% 龙心是提前再召的捷径。
    守卫：`check_spawn_rules` / `check_whelp_flight`；`check_achievements` 增加父节点存在性与「无 goal_details 的节点必须有脚本完成」。

23. **A 批：龙魂觉醒 + 套装效果 + 龙息斩（2026-10-27）**：
    - 新增 6 个 item ID 已按规程 `reserve → claim`（`dragon_soul` + 觉醒剑/四件甲），镜像 36 条。
    - 升级配方用 shapeless：觉醒剑 = 原剑 + 龙魂 + 4 鳞；每件甲 = 原件 + 龙魂 + 2 鳞。觉醒件同样有 `repair_<id>` 重铸配方，并加入 `repairStation.py` 的 GEAR。
    - 套装效果：`dragonSetBonus.py` 每 2 秒查 4 个 ARMOR 槽（0头/1胸/2腿/3靴），四件齐（原版/觉醒混搭）就给 `fire_resistance` / `regeneration` **10 秒**，并且先用 `GetAllEffects` 看剩余时间、**不足 4 秒才续**（作者指出一直刷会让效果闪）。
    - 龙息斩：`dragonSlash.py` 取朝向用 `serverApi.GetDirFromRot`，横向投影做锥形判定；`GetEntitiesAround` 用 `is_family=mob` 过滤掉玩家，跳过三只友军，`CreateHurt(...).Hurt(..., EntityAttack, playerId, None, True)`；12 秒冷却。**触发方式见教训 24**。
    守卫：`check_combat_scripts`；`check_repair_paths` 覆盖 14 件有耐久装备。

24. **技能按钮：右键在触屏版不可靠，`ServerItemTryUseEvent` 对 `netease:weapon` 根本不触发（2026-10-27 实机确认）**：
    - 作者反馈「觉醒剑右键没用」。排查结论：**`netease:weapon` 物品没有「使用动画」，引擎不会抛 `ServerItemTryUseEvent`**，脚本监听它永远收不到；`ServerItemUseOnEvent`（右键方块）能收到但不等于空手右键。已在 `dragonSlash.py` 里删掉该监听，并让 `check_skill_hud` 禁止这个事件名再出现。
    - 基岩版要面向触屏玩家，所以主路径改成 **HUD 技能按钮**：手持龙牙剑/觉醒剑时屏幕出现一个可拖动圆形按钮，点一下放技能，位置持久化；`RightClickBeforeClientEvent`（鼠标右键 / 触屏交互键 / 手柄 LT）保留为**兜底**，且**不取消事件**，免得挡掉原版右键容器。
    - UI 三件套：`RP/ui/_ui_defs.json` 注册命名空间 → `RP/ui/dragonskillhud.json`（`main@common.base_screen` → 100%×100% 的 `skillPanel` → `skillButton@common.button`）→ Python `clientApi.RegisterUI(modName, uiKey, '包.模块.类名', '命名空间.main')` + `CreateUI(..., {'isHud': 1})`。`isHud:1` 的关键作用是**开着背包也不挡操作**。
    - 按钮必须写 `"button_mappings": []`，否则点击被控件映射吃掉、Python 的 `AddTouchEventParams` 回调收不到；`dragged` 三件套是 `draggable: "both"` + `contained: true` + `is_handle_button_move_event: true`。
    - 拖拽与点击共用一套回调：`GetBaseUIControl(path).asButton().AddTouchEventParams({'isSwallow': True})` + `SetButtonTouchDownCallback/MoveCallback/UpCallback`；Move 回调参数里是 `TouchPosX/TouchPosY`（相对屏幕），位移超过 6px 视为拖动 → `SetPosition` + 存位置、**抬起时不施放**；没超过就当作点击施放。抬起才算拖动结束，避免边拖边放。
    - 位置持久化用 `serverApi.CreateConfigClient(LEVEL_ID).SetConfigData(key, {'x':..,'y':..}, True)`（`isGlobal=True` 跨世界），`GetConfigData` 取回；`GetBaseUIControl(...).GetPosition()` 拿初始位置。
    - 客户端 → 服务端用 `ClientSystem.NotifyToServer(事件名, 普通dict)`；服务端监听四元组是 `(客户端mod名, 客户端System名, 事件名)`，mod 名就是 `@Mod.Binding(name=...)` / `RegisterSystem` 第一个参数。**引擎会给服务端回调的 args 注入 `__id__` = 发送方玩家 id**（参考模组《一键生成生物UI控件交互事件传递》直接用它取玩家），比自己塞进 payload 的 `playerId` 更可信 —— 两条都带上、服务端优先认 `__id__`。
    - 显隐由 `OnCarriedNewItemChangedClientEvent` 驱动（切物品瞬间），再用 `OnScriptTickClient` 兜底（进世界/初始化时补一次）。冷却只在前端显示数字（`ceil(剩余)`），**服务端独立再算一次 CD**，前端数字不是权威。
    - `ui_screen` 类型的 ID 已按规程注册（键名 `^[a-z0-9]+$`，kind=`hud`，本包镜像 37 条）；`check_id_registry` 现在会扫 `RP/ui/*.json` 的每个命名空间，防止手写 UI 文件绕过台账。
    守卫：`check_skill_hud`（`_ui_defs` 收录、命名空间、`base_screen` 基模板、`button_mappings == []`、`is_handle_button_move_event`、`draggable/contained`、默认 `visible: false`、按钮贴图存在、客户端/服务端事件名与 `COOLDOWN` 一致、`dragonSlash.py` 里不得再出现 `ServerItemTryUseEvent`）。

25. **技能按钮实机第二轮：按钮太大 + 「点了没技能，只有 12 秒倒计时」（2026-10-27）**：
    - **「倒计时出现」不等于「服务端收到」**。上一版 `RequestCast` 的写法是先 `self.cdUntil = now + COOLDOWN` 再 `NotifyToServer(...)`，所以**发送那行一旦抛异常，按钮照样倒计时**，看起来就是"技能放了但没效果"。现在顺序反过来：`try: NotifyToServer(普通dict)` 成功才起算本地冷却，失败打 `[fycq-skill] NotifyToServer failed`；载荷从 `self.CreateEventData()` 换成**普通 dict**（参考模组一律传 dict：《冰与火法杖》`NotifyToServer("bullet", {...})`、《自定义3D武器》`NotifyToServer('AttackedPacket', {...})`）。守卫禁止客户端再出现 `CreateEventData`。
    - **加了服务端→客户端的回执，让一次实机就能分段定位**：`dragonSlash` 每次都 `NotifyToClient(playerId, 'FycqDragonSkillResult', {state, hits, left})`，按钮上短暂显示命中数（`3` / `0` / `剑`），冷却回执还会把客户端倒计时同步成服务端剩余秒。**只有倒计时、按钮数字不出现 ⇒ 服务端压根没收到**，去「脚本测试日志」看 `[fycq-slash] server ready` / `cast from` / `reject:` 三行。守卫断言服务端必须有 `RESULT_EVENT`/`NotifyToClient`/`__id__`/`reject` 四类要素。
    - **`ALLY` 跳过是错的**：世界里会咬玩家的正是幼龙/祭司/龙卫（玩家没有友好龙裔，龙巢召的是龙蛇本体），上一版把三个都跳过 → 对着一群龙裔放技能会"什么都没打中"。现在只排除玩家家族，锥形内所有非玩家生物都吃这一刀。守卫禁止 `ALLY` 再出现。
    - 判定改成参考模组《自定义3D武器》`sector_attack` 的口径：`CreatePos(id).GetFootPos()`（脚部，不是中心）、`any_of` + `is_family` + `operator: not` + `value: player`（不是"必须是 mob"）、`Hurt(damage, cause, attacker, childAttacker, knock)` 的**返回值不参与命中计数**（参考实现根本不读返回值，靠它计数会永远 0）。
    - 尺寸 64 → **44**（作者原话「按钮太大了点」）；标签 `offset` 从 `[0,30]` 归零到按钮中央。守卫断言 `size` 是 24–48 的整数边长（负测：填回 64 会 FAIL）。
    - 触屏没有稳定右键：`RightClickBeforeClientEvent` 官方口径是"移动端长按/PC F11 模式、PC 普通模式鼠标右键"，《自定义3D武器》打动作还额外监听 `TapBeforeClientEvent` + `LeftClickBeforeClientEvent`。**不要把施放绑到 tap**（普通点一下就放技能会误触），主路径只能是 HUD 按钮。

## 4. 当前内容

- BOSS `fycq:drasnea`：500 血、29 组件、4 段动画（idle/move/attack/death）、原版 BOSS 血条、火球三连 + 冲撞、专属掉落、不自然刷怪（`spawn_rules` 已删，靠刷怪蛋/`/summon`）
- 24 物品：5 材料（含**龙魂**）+ 龙牙剑 + 镐斧锹锄 + 龙鳞四件套 + **龙牙剑·觉醒 + 觉醒四件甲** + 龙血凝露（饮用回血/抗性，返空瓶）+ 4 张刷怪蛋，外加 1 张显式刷怪蛋 `fycq:zz_drasnea_egg`（`custom_item_type: egg` + `netease:egg`，官方规范见《1-自定义物品/4-自定义生物蛋》，支持右键生成/刷怪笼/发射器；`zz_` 前缀让它排在分页末尾）
- 7 方块：龙鳞块 / 龙鳞砖 / 龙鳞柱 / 龙骨块 / 龙晶块 / 龙晶灯 / 龙巢
- 3 生物（波 3）：`dragon_whelp` 幼龙（30 血，**飞行近战**，fly 导航 + random_fly）、`dragon_priest` 龙祭司（60 血火球远程）、`dragon_guard` 龙卫（120 血近战精英）；各带几何体、64×128 贴图、动画、控制器、渲染控制器、掉落表、`netease:egg` 刷怪蛋与原版音效绑定
- **自然刷怪**：三只都有 `spawn_rules`（夜晚、亮度 0–7，群山/台地/台地类群系，权重 6/3/1，队伍 1–2/1/1），带 `minecraft:despawn` 按距离消失；BOSS **不自然刷**
- 三只小怪 5 态动画：`idle / move / attack / hurt / death`（攻击态由延迟攻击驱动，受击态由受击标记驱动）；BOSS 4 段（受击用 `is_hurt_color` 红闪）
- **龙蛇三阶段**（脚本 `bossPhase.py`，阈值 66% / 33%）：phase2 移速 0.36 / 伤害 16 / 震地 CD 8 / **龙息火球 + 冲锋** / 血条「龙蛇·血怒」；phase3 移速 0.42 / 伤害 22 / 震地 CD 6 / **贴身灼烧 area_attack** / 血条「龙蛇·狂怒」
- **限量召唤**：JSON 的 `summon_entity` 全部移除（无数量上限），改由脚本每 10s 招一波；**按召唤者独立计数**：每只龙蛇最多 6 只、每只祭司最多 2 只；**蛋召/野生的幼龙不计入、不受限**
- **修复**：工具铁砧只能用**钻石**（`netease:weapon.level=3` 决定），盔甲铁砧修不了（无修复材料字段）；`minecraft:repairable` 实测不生效、已撤。龙鳞路线 = **龙巢修复**（手拿装备右键龙巢，1 龙鳞 = 25% 最大耐久，保留附魔）+ **重铸配方**（装备 + 2 龙鳞 → 新件，重置耐久与附魔）
- **龙巢召唤**：**首召（每个世界一次）主手龙鳞 + 8 龙鳞，不需要龙心**（否则龙心只能靠龙蛇掉，死循环）；之后主手龙心 + 4 龙鳞。8 秒玩家冷却、附近 32 格已有龙蛇/上方不足 4 格净空/材料不够均拒绝且不扣材料
- **成就 4 节点**（同一页，根 `fycq_dragonkin_first_kill`）：首杀「龙裔猎人」、首召「龙巢初醒」、击杀 10 幼龙「幼龙克星」、集齐四件套「龙鳞全装」（原版/觉醒混搭均可）；首杀发 3 结晶 + 8 鳞，其余只弹成就
- **龙魂觉醒**：龙蛇玩家击杀保底 1 龙魂；龙牙剑 + 龙魂 + 4 鳞 → 觉醒剑（13 伤害/2800 耐久），每件甲 + 龙魂 + 2 鳞 → 觉醒甲（+1 防、+2 韧性、+10% 耐久）；觉醒件同样可龙巢修复/重铸
- **套装效果**（`dragonSetBonus.py`）：四件龙鳞甲（原版/觉醒混搭）→ 抗火 I + 生命恢复 I；一次给 10 秒，**只有剩余不足 4 秒才续**（反复 AddEffect 会让状态图标/粒子闪），脱一件后最多 10 秒自然结束
- **龙息斩**（`dragonSlash.py` 服务端 + `dragonSkillClient.py` 客户端）：手持龙牙剑/觉醒剑时屏幕出现**直径 44 的可拖动技能按钮**（位置持久化，点一下施放、拖动不误放），鼠标右键/触屏交互键作为兜底且**不取消事件**（不挡右键容器）；前方 5.5 格 ±65° 锥形，普通剑 8 / 觉醒剑 12 伤害 + 击退，12 秒冷却（服务端权威，客户端倒计时会被服务端回执同步）；命中数/未命中/需持剑都会回显到按钮上；除了玩家以外什么都打（含幼龙/祭司/龙卫）
- **龙息与友伤**：phase2/3 龙息火球落地云 **5 秒销毁**（原版 120 秒）；龙裔 `damage_sensor` 免疫 `magic`，BOSS 不再被自己的云伤到、幼龙也不会被擦伤反击；`knockback_roar` 只作用于玩家；四只实体已移除 `hurt_by_target`
- **首杀成就（按玩家各算）**：`customAchievements/dragonkin_first_kill.json` + `achievementServer.py`；每个玩家第一次击杀龙蛇弹「龙裔猎人」成就，发 龙血结晶 ×3 + 龙鳞 ×8，ExtraData 防重复
- 技能：BOSS 震地怒吼（**只击退玩家** 4 格、伤 10）+ 召唤 2 只幼龙；龙祭司召唤 1 只幼龙 + 火球；龙卫震地怒吼（只打玩家）+ 贴身范围伤害；幼龙扑咬
- 音效：`sound_effects` 短名 + 动画时间轴播放（复用原版音效事件）
- 掉落：每只都有保底池 + 稀有池（`random_chance_with_looting` 受抢夺加成）：BOSS 35% 龙血结晶、龙卫 12% 龙血结晶、祭司 5% 龙心
- 40 配方（18 常规 + 3 条反向拆解 + 14 条重铸 + 5 条觉醒升级）；创造栏单页平铺 + 工具/盔甲两组（含觉醒件）
- 脚本 `DrasneaScripts`：9 个服务端 System（探针、仇恨守卫、BOSS 阶段、龙巢修复、祭坛召唤、成就结算、龙息清理、套装效果、龙息斩）+ 2 个客户端 System（探针、技能按钮 HUD `dragonskillhud`）

## 5. 待办

- **实机验收**：按 `docs/验收清单.md` 跑（三阶段、召唤上限、龙巢修复/首召/常规召唤、4 个成就、斧伤手感、龙息云 5 秒消失且不自伤/误伤、怒吼只打玩家、幼龙不反击、自然刷怪群系/权重、幼龙飞行（会移动不是原地打转）、**龙魂掉落/觉醒升级/套装效果**、**技能按钮 HUD：手持剑出现 / 拖动并重进世界后位置仍在 / 点击施放 / 冷却数字 / 右键兜底不挡容器**）
- **数值平衡**：自然刷怪权重（6/3/1）、龙鳞获取量、首召 8 鳞、1 心 + 4 鳞、5 个龙魂的觉醒成本、套装抗火+恢复、龙息斩 8/12 伤害与 12 秒冷却，等实机手感
- **模型剩余共面**：翅膀已修；头部小骨 `bone100–118`、`head/head`、`bone55/bone2` 仍余 107 处可能闪烁，实机看到再修
- **上架准备**：pack_icon 目前是旧图；商店封面/宣传图/简介/版本号待作者定
- 屏幕 BOSS 血条 UI：**作者明确不做**，沿用原版顶部 BOSS 条

## 6. 快照

- git 仓库已建（2026-10-27，按作者「commit吧」），annotated tag **`v1.0.0-20261027`** 是初始回退点；之后每批「同步 live + diff 复核 → commit」。
- 历史 zip：`Project/.backup/2026-10-26-drasnea-before.zip`（改造前原始包）、`2026-10-26-drasnea-wave12.zip`（波 1+2 落地后）。
