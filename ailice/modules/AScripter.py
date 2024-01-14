import subprocess
import os
import time
import tempfile
import traceback

from ailice.common.lightRPC import makeServer
from ailice.modules.AScrollablePage import AScrollablePage


class AScripter():
    def __init__(self, incontainer = False):
        self.incontainer = incontainer
        self.sessions = {"bash": {"proc": None, "pages": AScrollablePage({"SCROLLUP": "SCROLLUPBASH"})},
                         "py": {"proc": None, "pages": AScrollablePage({"SCROLLUP": "SCROLLUPPY"})}}
        return
    
    def ModuleInfo(self):
        return {"NAME": "scripter", "ACTIONS": {"BASH": {"sig": "RunBash(code:str)->str", "prompt": "Execute bash script. A timeout error will occur for programs that have not been completed for a long time."},
                                                "SCROLLUPBASH": {"sig": "ScrollUpBash()->str", "prompt": "Scroll up the results."},
                                                "PYTHON": {"sig": "RunPython(code:str)->str", "prompt": "Execute python code. Please note that you need to copy the complete code here, and you must not use references."},
                                                "SCROLLUPPY": {"sig": "ScrollUpPy()->str", "prompt": "Scroll up the results."}}}
    
    def RunCMD(self, session: str, cmd: list[str], timeout: int = 30):
        env = os.environ.copy()
        env["A_IN_CONTAINER"] = "1" if self.incontainer else "0"
        self.sessions[session]['proc'] = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
        os.set_blocking(self.sessions[session]['proc'].stdout.fileno(), False)
        self.Wait(process=self.sessions[session]['proc'], timeout=timeout)
        return
    
    def Wait(self, process, timeout):
        t0 = time.time()
        while time.time() < (t0 + timeout):
            if process.poll() is not None:
                return
            time.sleep(0.5)
    
    def CheckOutput(self, session: str) -> tuple[str,bool]:
        process = self.sessions[session]['proc']
        output = ''
        completed = False
        if process.poll() is not None:
            remainingOutput = process.stdout.read()
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
    
    def RunBash(self, code: str) -> str:
        res = ""
        if "" != code.strip():
            try:
                self.RunCMD('bash', ["bash", "-c", code])
            except Exception as e:
                res += f"Exception: {str(e)}\n {traceback.format_exc()}"
        
        try:
            output, completed = self.CheckOutput(session='bash')
            res += output
            res += "\nThe bash script takes longer to complete. You can pass an empty string to the BASH function to get new output." if not completed else "\nExecution completed."
        except Exception as e:
            res += f"Exception when check the output of bash execution: {str(e)}\n {traceback.format_exc()}"
            print(res)
        finally:
            self.sessions['bash']['pages'].LoadPage(res, "BOTTOM")
            return self.sessions['bash']['pages']()
    
    def ScrollUpBash(self) -> str:
        self.sessions['bash']['pages'].ScrollUp()
        return self.sessions['bash']['pages']()
    
    def RunPython(self, code: str) -> str:
        res = ""
        if "" != code.strip():
            with tempfile.NamedTemporaryFile(mode='w', delete=True) as temp:
                temp.write(code)
                temp.flush()
                try:
                    self.RunCMD('py', ['python3', '-u', temp.name])
                except Exception as e:
                    res += f"Exception: {str(e)}\n {traceback.format_exc()}"
        
        try:
            output, completed = self.CheckOutput(session='py')
            res += output
            res += "\nThe python script takes longer to complete. You can pass an empty string to the PYTHON function to get new output." if not completed else "\nExecution completed."
        except Exception as e:
            res += f"Exception when check the output of python execution: {str(e)}\n {traceback.format_exc()}"
            print(res)
        finally:
            self.sessions['py']['pages'].LoadPage(res, "BOTTOM")
            return self.sessions['py']['pages']()
    
    def ScrollUpPy(self) -> str:
        self.sessions['py']['pages'].ScrollUp()
        return self.sessions['py']['pages']()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--incontainer',action="store_true",help="Run in container. Please DO NOT turn on this switch on non-virtual machines, otherwise it will cause serious security risks.")
    args = parser.parse_args()
    addr = "tcp://0.0.0.0:59000" if args.incontainer else "tcp://127.0.0.1:59000"
    makeServer(lambda: AScripter(incontainer=args.incontainer), addr, ["ModuleInfo", "RunBash", "ScrollUpBash", "RunPython", "ScrollUpPy"]).Run()