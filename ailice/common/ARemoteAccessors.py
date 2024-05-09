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
            try:
                self.pool[cfg['addr']] = makeClient(cfg['addr'])
            except Exception as e:
                print(f"Connecting module {serviceName} FAILED. You can try running the module manually and observe its error messages.")
                raise e
        return
    
    def GetClient(self, moduleAddr: str):
        if moduleAddr not in self.pool:
            self.pool[moduleAddr] = makeClient(moduleAddr)
        return self.pool[moduleAddr]
    
clientPool = AClientPool()