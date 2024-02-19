
STEP = 4096

class AScrollablePage():
    def __init__(self, functions: dict[str, str]):
        self.txt = None
        self.currentIdx = None
        self.functions = functions
        return
    
    def ConstructPrompt(self) -> str:
        ret = "To avoid excessive consumption of context space due to lengthy content, we have paginated the entire content. This is just one page, to browse more content, please use the following function(s) for page navigation.\n"
        funcs = []
        if ('SCROLLDOWN' in self.functions) and (self.currentIdx + STEP < len(self.txt)):
            funcs.append(f"#scroll down the page: \n{self.functions['SCROLLDOWN']}<!||!>\n")
        if ('SCROLLUP' in self.functions) and (self.currentIdx > 0):
            funcs.append(f"#scroll up the page: \n{self.functions['SCROLLUP']}<!||!>\n")
        if ('SEARCHDOWN' in self.functions) and (self.currentIdx + STEP < len(self.txt)):
            funcs.append(f"#search the content downward and jumps the page to the next matching point(Just like the F3 key normally does): \n{self.functions['SEARCHDOWN']}<!|query: str|!>\n")
        if ('SEARCHUP' in self.functions) and (self.currentIdx > 0):
            funcs.append(f"#search the content upward and jumps the page to the next matching point: \n{self.functions['SEARCHUP']}<!|query: str|!>\n")
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

    def SearchDown(self, query: str) -> bool:
        loc = self.txt.lower().find(query.lower(), self.currentIdx if 0 < self.currentIdx else 0)
        self.currentIdx = (loc - STEP//2) if -1 != loc else self.currentIdx
        return (-1 != loc)
    
    def SearchUp(self, query: str) -> bool:
        loc = self.txt.lower().rfind(query.lower(), 0, (self.currentIdx + 1) if 0 < (self.currentIdx + 1) else 0)
        self.currentIdx = (loc - STEP//2) if -1 != loc else self.currentIdx
        return (-1 != loc)
    
    def __call__(self) -> str:
        if (self.currentIdx >= len(self.txt)):
            return "EOF."
        elif ((self.currentIdx + STEP) <= 0):
            return "FILE HEADER REACHED."
        else:
            start = self.currentIdx if self.currentIdx >= 0 else 0
            end = (self.currentIdx + STEP) if (self.currentIdx + STEP) >= 0 else 0
            return self.txt[start:end] + "\n\n" + self.ConstructPrompt()