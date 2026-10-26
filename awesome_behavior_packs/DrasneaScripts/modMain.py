# -*- coding: utf-8 -*-
"""脚本入口。

两个服务端系统：
  · DrasneaProbeServer —— 只读探针（打 [fycq-probe] 日志，验证事件与血量可读）
  · AggroGuardServer   —— 创造/旁观玩家不被追逐（JSON 无 is_creative 过滤器，只能脚本兜底）
一个客户端系统：
  · DrasneaProbeClient —— 只确认客户端脚本加载
"""
from mod.common.mod import Mod
import mod.client.extraClientApi as clientApi
import mod.server.extraServerApi as serverApi

MOD_NAME = 'DrasneaScripts'


@Mod.Binding(name=MOD_NAME, version='0.0.2')
class DrasneaScriptsMod(object):

    def __init__(self):
        pass

    @Mod.InitServer()
    def initServer(self):
        serverApi.RegisterSystem(MOD_NAME, 'DrasneaProbeServer',
                                 MOD_NAME + '.probeServer.DrasneaProbeServer')
        serverApi.RegisterSystem(MOD_NAME, 'AggroGuardServer',
                                 MOD_NAME + '.aggroGuard.AggroGuardServer')

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
