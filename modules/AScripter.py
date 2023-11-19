import subprocess
import tempfile

from common.lightRPC import makeServer
from modules.AScrollablePage import AScrollablePage


class AScripter():
    def __init__(self):
        self.pageBash = AScrollablePage({"SCROLLUP": "SCROLLUPBASH<!||!>"})
        self.pagePy = AScrollablePage({"SCROLLUP": "SCROLLUPPY<!||!>"})
        return
    
    def ModuleInfo(self):
        return {"NAME": "scripter", "ACTIONS": {"BASH": "RunBash(code:str)->str", "SCROLLUPBASH": "ScrollUpBash()->str", "PYTHON": "RunPython(code:str)->str", "SCROLLUPPY": "ScrollUpPy()->str"}}
    
    def RunBash(self, code: str) -> str:
        try:
            res = subprocess.check_output(code, shell=True, executable="/bin/bash", universal_newlines=True, timeout=60)
        except subprocess.CalledProcessError as e:
            res = str(e)
        except subprocess.TimeoutExpired as e:
            res = str(e)
        finally:
            self.pageBash.LoadPage(res, "BOTTOM")
            return self.pageBash()

    def ScrollUpBash(self) -> str:
        self.pageBash.ScrollUp()
        return self.pageBash()
    
    def RunPython(self, code: str) -> str:
        try:
            with tempfile.NamedTemporaryFile(mode='w', delete=True) as temp:
                temp.write(code)
                temp.flush()
                result = subprocess.run(['python3', temp.name], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                res = result.stdout
        except Exception as e:
            res = f"Exception: {str(e)}\n"
        finally:
            self.pagePy.LoadPage(res, "BOTTOM")
            return self.pagePy()
    
    def ScrollUpPy(self) -> str:
        self.pagePy.ScrollUp()
        return self.pagePy()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--incontainer',action="store_true",help="Run in container. Please DO NOT turn on this switch on non-virtual machines, otherwise it will cause serious security risks.")
    args = parser.parse_args()
    addr = "tcp://0.0.0.0:2005" if args.incontainer else "tcp://127.0.0.1:2005"
    py = AScripter()
    makeServer(py, addr, ["ModuleInfo", "RunBash", "ScrollUpBash", "RunPython", "ScrollUpPy"]).Run()