from ailice.common.lightRPC import makeClient
from ailice.common.AConfig import config

class AClientPool():
    def __init__(self):
        self.pool = dict()
        return
    
    def Init(self):
        for serviceName, cfg in config.services.items():
            if not config.speechOn and 'speech' == serviceName:
                continue
            self.pool[cfg['addr']] = makeClient(cfg['addr'])
        return
    
    def GetClient(self, moduleAddr: str):
        if moduleAddr not in self.pool:
            self.pool[moduleAddr] = makeClient(moduleAddr)
        return self.pool[moduleAddr]
    
clientPool = AClientPool()