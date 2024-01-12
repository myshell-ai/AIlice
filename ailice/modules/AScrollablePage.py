
STEP = 4096

class AScrollablePage():
    def __init__(self, functions: dict[str, str]):
        self.txt = None
        self.currentIdx = None
        self.functions = functions
        return
    
    def ConstructPrompt(self) -> str:
        ret = "This is a page of the results. To browse more results, you can use the following functions.\n"
        funcs = []
        if ('SCROLLDOWN' in self.functions) and (self.currentIdx + STEP < len(self.txt)):
            funcs.append(f"#scroll down the page: \n{self.functions['SCROLLDOWN']}<!||!>\n")
        if ('SCROLLUP' in self.functions) and (self.currentIdx > 0):
            funcs.append(f"#scroll up the page: \n{self.functions['SCROLLUP']}<!||!>\n")
        if ('SEARCHDOWN' in self.functions) and (self.currentIdx + STEP < len(self.txt)):
            funcs.append(f"#search page down, exactly matches query in the text: \n{self.functions['SEARCHDOWN']}<!|query: str|!>\n")
        if ('SEARCHUP' in self.functions) and (self.currentIdx > 0):
            funcs.append(f"#search page up, exactly matches query in the text: \n{self.functions['SEARCHUP']}<!|query: str|!>\n")
        return ret + "".join(funcs) if len(funcs) > 0 else ""
    
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

    def SearchDown(self, keyword: str):
        loc = self.txt.find(keyword, self.currentIdx if 0 < self.currentIdx else 0)
        self.currentIdx = (loc - STEP//2) if -1 != loc else self.currentIdx
        return
    
    def SearchUp(self, keyword: str):
        loc = self.txt.rfind(keyword, 0, (self.currentIdx + 1) if 0 < (self.currentIdx + 1) else 0)
        self.currentIdx = (loc - STEP//2) if -1 != loc else self.currentIdx
        return
    
    def __call__(self) -> str:
        if (self.currentIdx >= len(self.txt)):
            return "EOF."
        elif ((self.currentIdx + STEP) <= 0):
            return "FILE HEADER REACHED."
        else:
            start = self.currentIdx if self.currentIdx >= 0 else 0
            end = (self.currentIdx + STEP) if (self.currentIdx + STEP) >= 0 else 0
            return self.txt[start:end] + "\n\n" + self.ConstructPrompt()