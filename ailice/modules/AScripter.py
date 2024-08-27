import subprocess
import os
import time
import random
import threading
import tempfile
import platform
import traceback

from ailice.common.lightRPC import makeServer
from ailice.modules.AScrollablePage import AScrollablePage


class AScripter():
    def __init__(self, incontainer = False):
        self.incontainer = incontainer
        self.sessions = {}
        self.sessionsLock = threading.Lock()
        self.reader = threading.Thread(target=self.OutputReader, args=())
        self.reader.start()
        self.functions = {"SCROLLUP": "#scroll up the page: \nSCROLL-UP-TERM<!|session: str|!>"}
        return
    
    def ModuleInfo(self):
        return {"NAME": "scripter", "ACTIONS": {"PLATFORM-INFO": {"func": "PlatformInfo", "prompt": "Get the platform information of the current code execution environment.", "type": "primary"},
                                                "BASH": {"func": "RunBash", "prompt": "Execute bash script. A timeout error will occur for programs that have not been completed for a long time. Different calls to a BASH function are independent of each other. The state remaining from previous calls, such as the current directory, will not affect future calls.", "type": "primary"},
                                                "PYTHON": {"func": "RunPython", "prompt": "Execute python code. Please note that you need to copy the complete code here, and you must not use references.", "type": "primary"},
                                                "CHECK-OUTPUT": {"func": "CheckOutput", "prompt": "Obtain script execution output result.", "type": "supportive"},
                                                "SCROLL-UP-TERM": {"func": "ScrollUp", "prompt": "Scroll up the results.", "type": "supportive"},
                                                "SAVE-TO-FILE": {"func": "Save2File", "prompt": "Save text or code to file.", "type": "primary"}}}
    
    def GetSessionID(self) -> str:
        id = f"session-{str(random.randint(0,99999999))}"
        while id in self.sessions:
            id = f"session-{str(random.randint(0,99999999))}"
        return id
    
    def RunCMD(self, session: str, cmd: list[str], timeout: int = 30):
        env = os.environ.copy()
        env["A_IN_CONTAINER"] = "1" if self.incontainer else "0"
        self.sessions[session]['proc'] = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
        if os.name != "nt":
            os.set_blocking(self.sessions[session]['proc'].stdout.fileno(), False)
        self.Wait(process=self.sessions[session]['proc'], timeout=timeout)
        return
    
    def Wait(self, process, timeout):
        t0 = time.time()
        while time.time() < (t0 + timeout):
            if process.poll() is not None:
                return
            time.sleep(0.5)
    
    def CheckProcOutput(self, session: str) -> tuple[str,bool]:
        process = self.sessions[session]['proc']
        output = ''
        completed = False
        if process.poll() is not None:
            for i in range(2):
                remainingOutput = ""
                try:
                    remainingOutput = process.stdout.read()
                    break
                except TypeError as e:
                    time.sleep(1)
                    remainingOutput += str(e) if 1==i else ""
                    continue
            if remainingOutput:
                output += remainingOutput
            completed = True
        else:
            while True:
                line = process.stdout.readline()
                if line:
                    output += line
                else:
                    break
        return output, completed
    
    def UpdateSession(self, session: str):
        try:
            output, completed = self.CheckProcOutput(session=session)
            self.sessions[session]['completed'] = completed
            self.sessions[session]['output'] += output
            p = "\nThe program takes longer to complete. You can use WAIT to wait for a while and then use CHECK-OUTPUT function to get new output." if not completed else "\nExecution completed."
        except Exception as e:
            p = f"Exception when check the output of program execution: {str(e)}\n {traceback.format_exc()}"
            print(p)
        finally:
            self.sessions[session]['pages'].LoadPage(self.sessions[session]['output'] + p, "BOTTOM")
                        
    def OutputReader(self):
        while True:
            with self.sessionsLock:
                for session in self.sessions:
                    if self.sessions[session]['completed']:
                        continue
                    self.UpdateSession(session)
            time.sleep(1.0)
        return
    
    def CheckOutput(self, session: str) -> str:
        with self.sessionsLock:
            return self.sessions[session]['pages']() + "\n\n" + f'Session name: "{session}"\n'
    
    def PlatformInfo(self) -> str:
        info = platform.uname()
        currentPath = os.getcwd()
        contents = os.listdir(currentPath)
        return f"""system: {info.system}, release: {info.release}, version: {info.version}, machine: {info.machine}
current path: {currentPath}
contents of current path: {contents if len(contents) <= 32 else (contents[:32] + '....[The tail content has been ignored. You can use BASH function to execute system commands to view the remaining content]')}
"""
    
    def RunBash(self, code: str) -> str:
        with self.sessionsLock:
            try:
                session = self.GetSessionID()
                self.sessions[session] = {"proc": None, "pages": AScrollablePage(functions=self.functions), "output": "", "lock": threading.Lock()}
                self.RunCMD(session, ["bash", "-c", code])
            except Exception as e:
                self.sessions[session]['output'] += f"Exception: {str(e)}\n {traceback.format_exc()}"
            
            self.UpdateSession(session)
            return self.sessions[session]['pages']() + "\n\n" + f'Session name: "{session}"\n'
    
    def RunPython(self, code: str) -> str:
        with self.sessionsLock:
            with tempfile.NamedTemporaryFile(mode='w', delete=True) as temp:
                temp.write(code)
                temp.flush()
                try:
                    session = self.GetSessionID()
                    self.sessions[session] = {"proc": None, "pages": AScrollablePage(functions=self.functions), "output": "", "lock": threading.Lock()}
                    self.RunCMD(session, ['python3', '-u', temp.name])
                except Exception as e:
                    self.sessions[session]['output'] += f"Exception: {str(e)}\n {traceback.format_exc()}"
            
            self.UpdateSession(session)
            return self.sessions[session]['pages']() + "\n\n" + f'Session name: "{session}"\n'
    
    def ScrollUp(self, session: str) -> str:
        with self.sessionsLock:
            return self.sessions[session]['pages'].ScrollUp() + "\n\n" + f'Session name: "{session}"\n'
    
    def Save2File(self, filePath: str, code: str) -> str:
        try:
            dirPath = os.path.dirname(filePath)
            if "" != dirPath:
                os.makedirs(dirPath, exist_ok=True)
            with open(filePath, 'w') as f:
                f.write(code)
            return f"The file contents has been written."
        except Exception as e:
            return f"Exception encountered while writing to file. EXCEPTION: {str(e)}"


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--addr',type=str, help="The address where the service runs on.")
    parser.add_argument('--incontainer',action="store_true",help="Run in container. Please DO NOT turn on this switch on non-virtual machines, otherwise it will cause serious security risks.")
    args = parser.parse_args()
    #addr = "tcp://0.0.0.0:59000" if args.incontainer else "tcp://127.0.0.1:59000"
    makeServer(AScripter, {"incontainer": args.incontainer}, args.addr, ["ModuleInfo", "PlatformInfo", "CheckOutput", "RunBash", "RunPython", "ScrollUp", "Save2File"]).Run()

if __name__ == '__main__':
    main()
