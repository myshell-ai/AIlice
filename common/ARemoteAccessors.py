from common.lightRPC import makeClient
from common.AConfig import config

class AClientPool():
    def __init__(self):
        self.pool = dict()
        return
    
    def Init(self):
        storage = config.services['storage']['addr']
        browser = config.services['browser']['addr']
        arxiv = config.services['arxiv']['addr']
        google = config.services['google']['addr']
        duckduckgo = config.services['duckduckgo']['addr']
        speech = config.services['speech']['addr']
        scripter = config.services['scripter']['addr']
        
        self.pool = {storage: makeClient(storage),
                     browser: makeClient(browser),
                     arxiv: makeClient(arxiv),
                     google: makeClient(google),
                     duckduckgo: makeClient(duckduckgo),
                     scripter: makeClient(scripter)}
        if config.speechOn:
            self.pool[speech] = makeClient(speech)
        return
    
    def GetClient(self, moduleAddr: str):
        if moduleAddr not in self.pool:
            self.pool[moduleAddr] = makeClient(moduleAddr)
        return self.pool[moduleAddr]
    
clientPool = AClientPool()