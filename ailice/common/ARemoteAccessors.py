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
                self.pool[cfg['addr']] = {"name": serviceName, "client": makeClient(cfg['addr'])}
            except Exception as e:
                print(f"Connecting module {serviceName} FAILED. You can try running the module manually and observe its error messages. EXCEPTION: {str(e)}")
                raise e
        return
    
    def GetClient(self, moduleAddr: str):
        if moduleAddr not in self.pool:
            self.pool[moduleAddr] = {"client": makeClient(moduleAddr)}
            self.pool[moduleAddr]["name"] = self.pool[moduleAddr]["client"].ModuleInfo()["NAME"]
        return self.pool[moduleAddr]["client"]
    
    def __getitem__(self, key: str):
        for addr, client in self.pool.items():
            if key == client["name"]:
                return client["client"]
        return None
    
clientPool = AClientPool()