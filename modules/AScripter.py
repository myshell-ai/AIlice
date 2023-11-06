import subprocess
import tempfile

from common.lightRPC import makeServer


STEP = 1024

class AScripter():
    def __init__(self):
        self.prompt = """\n\nThis is the last page of result, you can use the following command to scroll up the result. You can scroll up multiple times until 'NONE' is returned.\n"""
        self.bashCurrent = -1
        self.bashResult = ""
        self.pyCurrent = -1
        self.pyResult = ""
        return
    
    def ResetBash(self):
        self.bashCurrent = -1
        self.bashResult = ""
        return

    def ResetPy(self):
        self.pyCurrent = -1
        self.pyResult = ""
        return
    
    def RunBash(self, cmd: str) -> str:
        try:
            self.ResetBash()
            self.bashResult = subprocess.check_output(cmd, shell=True, executable="/bin/bash", universal_newlines=True, timeout=60)
        except subprocess.CalledProcessError as e:
            self.bashResult = str(e)
        except subprocess.TimeoutExpired as e:
            self.bashResult = str(e)
        finally:
            return self.bashResult[self.bashCurrent * STEP:] + self.prompt + "SCROLLUPBASH<!||!>" if len(self.bashResult) > STEP else self.bashResult[self.bashCurrent * STEP:]

    def ScrollUpBash(self) -> str:
        self.bashCurrent -= 1
        if abs((self.bashCurrent + 1) * STEP) <= len(self.bashResult):
            return self.bashResult[self.bashCurrent * STEP: (self.bashCurrent + 1) * STEP] + self.prompt + "SCROLLUPBASH<!||!>"
        else:
            return "NONE"
    
    def RunPython(self, code: str) -> str:
        try:
            self.ResetPy()
            with tempfile.NamedTemporaryFile(mode='w', delete=True) as temp:
                temp.write(code)
                temp.flush()
                result = subprocess.run(['python3', temp.name], capture_output=True, text=True)
                self.pyResult = result.stdout if 0 == result.returncode else result.stderr
        except Exception as e:
            self.pyResult = f"Exception: {str(e)}\n"
        finally:
            return self.pyResult[self.pyCurrent * STEP:] + self.prompt + "SCROLLUPPY<!||!>" if len(self.pyResult) > STEP else self.pyResult[self.pyCurrent * STEP:]
    
    def ScrollUpPy(self) -> str:
        self.pyCurrent -= 1
        if abs((self.pyCurrent + 1) * STEP) <= len(self.pyResult):
            return self.pyResult[self.pyCurrent * STEP: (self.pyCurrent + 1) * STEP] + self.prompt + "SCROLLUPPY<!||!>"
        else:
            return "NONE"
        


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--incontainer',action="store_true",help="Run in container. Please DO NOT turn on this switch on non-virtual machines, otherwise it will cause serious security risks.")
    args = parser.parse_args()
    addr = "tcp://0.0.0.0:2005" if args.incontainer else "tcp://127.0.0.1:2005"
    py = AScripter()
    makeServer(py, addr).Run()