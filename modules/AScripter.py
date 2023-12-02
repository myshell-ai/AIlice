import subprocess
import tempfile

from common.lightRPC import makeServer
from modules.AScrollablePage import AScrollablePage


class AScripter():
    def __init__(self):
        self.pages = {"bash": AScrollablePage({"SCROLLUP": "SCROLLUPBASH"}),
                      "py": AScrollablePage({"SCROLLUP": "SCROLLUPPY"})}
        return
    
    def ModuleInfo(self):
        return {"NAME": "scripter", "ACTIONS": {"BASH": {"sig": "RunBash(code:str)->str", "prompt": "Execute bash script. A timeout error will occur for programs that have not been completed for a long time."},
                                                "SCROLLUPBASH": {"sig": "ScrollUpBash()->str", "prompt": "Scroll up the results."},
                                                "PYTHON": {"sig": "RunPython(code:str)->str", "prompt": "Execute python code. Please note that you need to copy the complete code here, and you must not use references."},
                                                "SCROLLUPPY": {"sig": "ScrollUpPy()->str", "prompt": "Scroll up the results."}}}
    
    def Run(self, session: str, cmd: list[str], timeout: int = None) -> str:
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout)
            res = result.stdout
        except Exception as e:
            res = f"Exception: {str(e)}\n"
        finally:
            self.pages[session].LoadPage(res, "BOTTOM")
            return self.pages[session]()
    
    def RunBash(self, code: str) -> str:
        return self.Run('bash', ["bash", "-c", code], timeout=60)
    
    def ScrollUpBash(self) -> str:
        self.pages["bash"].ScrollUp()
        return self.pages['bash']()
    
    def RunPython(self, code: str) -> str:
        with tempfile.NamedTemporaryFile(mode='w', delete=True) as temp:
            temp.write(code)
            temp.flush()
            return self.Run('py', ['python3', temp.name])
    
    def ScrollUpPy(self) -> str:
        self.pages['py'].ScrollUp()
        return self.pages['py']()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--incontainer',action="store_true",help="Run in container. Please DO NOT turn on this switch on non-virtual machines, otherwise it will cause serious security risks.")
    args = parser.parse_args()
    addr = "tcp://0.0.0.0:2005" if args.incontainer else "tcp://127.0.0.1:2005"
    py = AScripter()
    makeServer(py, addr, ["ModuleInfo", "RunBash", "ScrollUpBash", "RunPython", "ScrollUpPy"]).Run()