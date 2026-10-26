# -*- coding: utf-8 -*-
"""脚本入口。

八个服务端系统：
  · DrasneaProbeServer —— 只读探针（打 [fycq-probe] 日志，验证事件与血量可读）
  · AggroGuardServer   —— 创造/旁观玩家不被追逐（JSON 无 is_creative 过滤器，只能脚本兜底）
  · RepairStationServer —— 龙巢修复（手拿装备右键龙巢，消耗龙鳞回满耐久）
  · AltarSummonServer  —— 龙巢召唤（首召 8 龙鳞，之后 1 龙心 + 4 龙鳞）
  · AchievementServer  —— 4 个成就（首杀/首召/10 幼龙/集齐四件套）
  · DragonBreathServer —— BOSS 龙息火球的落地云 5 秒后销毁（原版 120 秒）
  · DragonSetBonusServer —— 龙鳞四件套：抗火 I + 生命恢复 I
  · DragonSlashServer  —— 龙牙剑右键龙息斩（12 秒冷却）
一个客户端系统：
  · DrasneaProbeClient —— 只确认客户端脚本加载
"""
from mod.common.mod import Mod
import mod.client.extraClientApi as clientApi
import mod.server.extraServerApi as serverApi

MOD_NAME = 'DrasneaScripts'


@Mod.Binding(name=MOD_NAME, version='0.0.3')
class DrasneaScriptsMod(object):

    def __init__(self):
        pass

    @Mod.InitServer()
    def initServer(self):
        serverApi.RegisterSystem(MOD_NAME, 'DrasneaProbeServer',
                                 MOD_NAME + '.probeServer.DrasneaProbeServer')
        serverApi.RegisterSystem(MOD_NAME, 'AggroGuardServer',
                                 MOD_NAME + '.aggroGuard.AggroGuardServer')
        serverApi.RegisterSystem(MOD_NAME, 'BossPhaseServer',
                                 MOD_NAME + '.bossPhase.BossPhaseServer')
        serverApi.RegisterSystem(MOD_NAME, 'RepairStationServer',
                                 MOD_NAME + '.repairStation.RepairStationServer')
        serverApi.RegisterSystem(MOD_NAME, 'AltarSummonServer',
                                 MOD_NAME + '.altarSummon.AltarSummonServer')
        serverApi.RegisterSystem(MOD_NAME, 'AchievementServer',
                                 MOD_NAME + '.achievementServer.AchievementServer')
        serverApi.RegisterSystem(MOD_NAME, 'DragonBreathServer',
                                 MOD_NAME + '.dragonBreath.DragonBreathServer')
        serverApi.RegisterSystem(MOD_NAME, 'DragonSetBonusServer',
                                 MOD_NAME + '.dragonSetBonus.DragonSetBonusServer')
        serverApi.RegisterSystem(MOD_NAME, 'DragonSlashServer',
                                 MOD_NAME + '.dragonSlash.DragonSlashServer')

    @Mod.DestroyServer()
    def destroyServer(self):
        pass

    @Mod.InitClient()
    def initClient(self):
        clientApi.RegisterSystem(MOD_NAME, 'DrasneaProbeClient',
                                 MOD_NAME + '.probeClient.DrasneaProbeClient')

    @Mod.DestroyClient()
    def destroyClient(self):
        pass
