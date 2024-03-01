import threading

class AMessenger():
    def __init__(self):
        self.lock = threading.Lock()
        self.msg = None
        self.msgPrevious = None
        return

    def Get(self) -> str:
        with self.lock:
            self.msgPrevious = self.msg
            self.msg = None
            return self.msgPrevious
        
    def GetPreviousMsg(self) -> str:
        return self.msgPrevious
    
    def Lock(self):
        self.lock.acquire()
        return
    
    def Put(self, msg: str):
        self.msg = msg

    def Unlock(self):
        self.lock.release()
        return
    
messenger = AMessenger()
    