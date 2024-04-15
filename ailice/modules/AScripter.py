import subprocess
import os
import time
import random
import tempfile
import traceback

from ailice.common.lightRPC import makeServer
from ailice.modules.AScrollablePage import AScrollablePage


class AScripter():
    def __init__(self, incontainer = False):
        self.incontainer = incontainer
        self.sessions = {}
        self.functions = {"SCROLLUP": "#scroll up the page: \nSCROLL_UP_TERM<!|session: str|!>"}
        return
    
    def ModuleInfo(self):
        return {"NAME": "scripter", "ACTIONS": {"BASH": {"func": "RunBash", "prompt": "Execute bash script. A timeout error will occur for programs that have not been completed for a long time.", "type": "primary"},
                                                "PYTHON": {"func": "RunPython", "prompt": "Execute python code. Please note that you need to copy the complete code here, and you must not use references.", "type": "primary"},
                                                "CHECK_OUTPUT": {"func": "CheckOutput", "prompt": "Obtain script execution output result.", "type": "supportive"},
                                                "SCROLL_UP_TERM": {"func": "ScrollUp", "prompt": "Scroll up the results.", "type": "supportive"},
                                                "SAVE_TO_FILE": {"func": "Save2File", "prompt": "Save text or code to file.", "type": "primary"}}}
    
    def GetSessionID(self) -> str:
        id = f"session_{str(random.randint(0,99999999))}"
        while id in self.sessions:
            id = f"session_{str(random.randint(0,99999999))}"
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
                try:
                    remainingOutput = process.stdout.read()
                    break
                except TypeError as e:
                    time.sleep(1)
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
    
    def CheckOutput(self, session: str) -> str:
        res = ""
        try:
            output, completed = self.CheckProcOutput(session=session)
            res += output
            res += "\nThe bash script takes longer to complete. You can use WAIT to wait for a while and then use CHECK_OUTPUT function to get new output." if not completed else "\nExecution completed."
        except Exception as e:
            res += f"Exception when check the output of bash execution: {str(e)}\n {traceback.format_exc()}"
            print(res)
        finally:
            self.sessions[session]['pages'].LoadPage(res, "BOTTOM")
            return self.sessions[session]['pages']() + "\n\n" + f'Session name: "{session}"\n'
        
    def RunBash(self, code: str) -> str:
        res = ""
        try:
            session = self.GetSessionID()
            self.sessions[session] = {"proc": None, "pages": AScrollablePage(functions=self.functions)}
            self.RunCMD(session, ["bash", "-c", code])
        except Exception as e:
            res += f"Exception: {str(e)}\n {traceback.format_exc()}"
        
        try:
            output, completed = self.CheckProcOutput(session=session)
            res += output
            res += "\nThe bash script takes longer to complete. You can use WAIT to wait for a while and then use CHECK_OUTPUT function to get new output." if not completed else "\nExecution completed."
        except Exception as e:
            res += f"Exception when check the output of bash execution: {str(e)}\n {traceback.format_exc()}"
            print(res)
        finally:
            self.sessions[session]['pages'].LoadPage(res, "BOTTOM")
            return self.sessions[session]['pages']() + "\n\n" + f'Session name: "{session}"\n'
    
    def RunPython(self, code: str) -> str:
        res = ""
        with tempfile.NamedTemporaryFile(mode='w', delete=True) as temp:
            temp.write(code)
            temp.flush()
            try:
                session = self.GetSessionID()
                self.sessions[session] = {"proc": None, "pages": AScrollablePage(functions=self.functions)}
                self.RunCMD(session, ['python3', '-u', temp.name])
            except Exception as e:
                res += f"Exception: {str(e)}\n {traceback.format_exc()}"
        
        try:
            output, completed = self.CheckProcOutput(session=session)
            res += output
            res += "\nThe python script takes longer to complete. You can use WAIT to wait for a while and then use CHECK_OUTPUT function to get new output." if not completed else "\nExecution completed."
        except Exception as e:
            res += f"Exception when check the output of python execution: {str(e)}\n {traceback.format_exc()}"
            print(res)
        finally:
            self.sessions[session]['pages'].LoadPage(res, "BOTTOM")
            return self.sessions[session]['pages']() + "\n\n" + f'Session name: "{session}"\n'
    
    def ScrollUp(self, session: str) -> str:
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
    makeServer(AScripter, {"incontainer": args.incontainer}, args.addr, ["ModuleInfo", "CheckOutput", "RunBash", "RunPython", "ScrollUp", "Save2File"]).Run()

if __name__ == '__main__':
    main()
