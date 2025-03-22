import threading

class AMessenger():
    def __init__(self):
        self.lock = threading.Lock()
        self.continueEvent = threading.Event()
        self.continueEvent.set()
        self.msg = None
        self.msgPrevious = None
        return

    def Get(self) -> str:
        self.continueEvent.wait()
        with self.lock:
            self.msgPrevious = self.msg
            self.msg = None
        return self.msgPrevious
        
    def GetPreviousMsg(self) -> str:
        return self.msgPrevious
    
    def Lock(self):
        self.continueEvent.clear()
        return
    
    def Put(self, msg: str):
        with self.lock:
            self.msg = msg if "" != msg.strip() else None

    def Unlock(self):
        self.continueEvent.set()
        return