
STEP = 1024

class AScrollablePage():
    def __init__(self, functions: dict[str, str]):
        self.txt = None
        self.currentIdx = None
        self.functions = functions
        return
    
    def ConstructPrompt(self) -> str:
        ret = "This is a page of the results. To browse more results, you can use the following functions.\n"
        if 'SCROLLDOWN' in self.functions:
            ret += f"#scroll down the page: \n{self.functions['SCROLLDOWN']}\n"
        if 'SCROLLUP' in self.functions:
            ret += f"#scroll up the page: \n{self.functions['SCROLLUP']}\n"
        return ret
    
    def LoadPage(self, txt: str, initPosition: str):
        self.txt = txt
        self.currentIdx = {"TOP": 0, "BOTTOM": len(txt) - STEP}[initPosition]
        return
    
    def ScrollDown(self):
        self.currentIdx += STEP
        return
    
    def ScrollUp(self):
        self.currentIdx -= STEP
        return
    
    def __call__(self) -> str:
        if (self.currentIdx >= len(self.txt)):
            return "EOF."
        elif ((self.currentIdx + STEP) <= 0):
            return "FILE HEADER REACHED."
        else:
            return self.txt[self.currentIdx: self.currentIdx + STEP] + "\n\n" + self.ConstructPrompt()