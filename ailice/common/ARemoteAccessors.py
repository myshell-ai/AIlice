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
                self.pool[cfg['addr']] = {"name": serviceName, "client": makeClient(url=cfg['addr'], clientPrivateKeyPath=cfg.get("clientPrivateKeyPath", None), serverPublicKeyPath=cfg.get("serverPublicKeyPath", None))}
            except Exception as e:
                print(f"Connecting module {serviceName} FAILED. You can try running the module manually and observe its error messages. EXCEPTION: {str(e)}")
                raise e
        return
    
    def GetClient(self, moduleAddr: str, clientPrivateKeyPath=None, serverPublicKeyPath=None):
        if moduleAddr not in self.pool:
            self.pool[moduleAddr] = {"client": makeClient(url=moduleAddr, clientPrivateKeyPath=clientPrivateKeyPath, serverPublicKeyPath=serverPublicKeyPath)}
            self.pool[moduleAddr]["name"] = self.pool[moduleAddr]["client"].ModuleInfo()["NAME"]
        return self.pool[moduleAddr]["client"]
    
    def __getitem__(self, key: str):
        for addr, client in self.pool.items():
            if key == client["name"]:
                return client["client"]
        return None
    
    def Destroy(self):
        for _, client in self.pool.items():
            destroy = getattr(client["client"], "Destroy", None)
            if callable(destroy):
                try:
                    destroy()
                except Exception as e:
                    print(f"AClientPool.Destroy Exception: {str(e)}")
                    continue
        self.pool.clear()
        return