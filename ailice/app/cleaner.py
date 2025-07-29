import threading
import time
from concurrent.futures import ThreadPoolExecutor
from ailice.app.log import logger


class SessionCleaner:
    def __init__(self, max_workers=5):
        self.pendingGCPool = {}
        self.poolLock = threading.Lock()
        
        self.gcThread = threading.Thread(target=self.GCThread, daemon=True)
        self.gcThread.start()
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="SessionReleaser")
        logger.info(f"SessionCleaner initialized with {max_workers} release workers and GC thread started")
        return
    
    def AddSessionToGC(self, sessionName, session):
        with self.poolLock:
            self.pendingGCPool[sessionName] = session
            logger.info(f"Session '{sessionName}' added to GC pool")
    
    def IsSessionInGC(self, sessionName):
        with self.poolLock:
            return sessionName in self.pendingGCPool
    
    def ReleaseSession(self, session):
        session._release_flag = True
        try:
            session.Release()
        finally:
            session._release_flag = False
        return
    
    def GCThread(self):
        while True:
            try:
                inactiveList = []
                with self.poolLock:
                    for sessionName, session in self.pendingGCPool.items():
                        if session.state == "init":
                            inactiveList.append(sessionName)
                        elif (not getattr(session, "_release_flag", False)) and session.IsStopped():
                            self.executor.submit(self.ReleaseSession, session)
                    
                    for sessionName in inactiveList:
                        self.pendingGCPool.pop(sessionName)
                        logger.info(f"Session '{sessionName}' removed from GC pool")
                
                if len(inactiveList) > 0:
                    logger.info(f"{len(inactiveList)} sessions released. GCPool size: {len(self.pendingGCPool)}")
                time.sleep(1)
            except Exception as e:
                logger.error(f"Unexpected exception in GCThread: {str(e)}")
        return


cleaner = SessionCleaner()