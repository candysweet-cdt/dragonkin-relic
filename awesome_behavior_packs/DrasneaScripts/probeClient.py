# -*- coding: utf-8 -*-
"""客户端探针：只确认客户端脚本也加载成功，不做任何事。"""
import mod.client.extraClientApi as clientApi

ClientSystem = clientApi.GetClientSystemCls()
PREFIX = 'fycq:'


def log(msg):
    print('[fycq-probe] ' + msg)


class DrasneaProbeClient(ClientSystem):

    def __init__(self, namespace, systemName):
        super(DrasneaProbeClient, self).__init__(namespace, systemName)
        engineNs = clientApi.GetEngineNamespace()
        engineSys = clientApi.GetEngineSystemName()
        self.ListenForEvent(engineNs, engineSys, 'AddEntityClientEvent', self, self.OnAddEntity)
        log('client system ready')

    def OnAddEntity(self, args):
        engineType = args.get('engineTypeStr') or ''
        if not engineType.startswith(PREFIX):
            return
        log('client add %s id=%s' % (engineType, args.get('id')))
