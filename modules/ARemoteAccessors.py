from common.lightRPC import makeClient
from common.AConfig import config

Storage = "ipc:///tmp/AIliceStorage.ipc"
Browser = "ipc:///tmp/ABrowser.ipc"
Arxiv = "ipc:///tmp/AArxiv.ipc"
Google = "ipc:///tmp/AGoogle.ipc"
Duckduckgo = "ipc:///tmp/ADuckDuckGo.ipc"
Speech = "ipc:///tmp/ASpeech.ipc"
Scripter = "tcp://127.0.0.1:2005"


class AClientPool():
    def __init__(self):
        self.pool = dict()
        return
    
    def Init(self):
        self.pool = {Storage: makeClient(Storage),
                     Browser: makeClient(Browser),
                     Arxiv: makeClient(Arxiv),
                     Google: makeClient(Google),
                     Duckduckgo: makeClient(Duckduckgo),
                     Scripter: makeClient(Scripter)}
        if config.speechOn:
            self.pool[Speech] = makeClient(Speech)
        return
    
    def GetClient(self, moduleAddr: str):
        return self.pool[moduleAddr]
    
clientPool = AClientPool()