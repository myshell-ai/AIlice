
STEP = 8192

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
            funcs.append(self.functions['SCROLLDOWN'])
        if ('SCROLLUP' in self.functions) and (self.currentIdx > 0):
            funcs.append(self.functions['SCROLLUP'])
        if ('SEARCHDOWN' in self.functions) and (self.currentIdx + STEP < len(self.txt)):
            funcs.append(self.functions['SEARCHDOWN'])
        if ('SEARCHUP' in self.functions) and (self.currentIdx > 0):
            funcs.append(self.functions['SEARCHUP'])
        return ret + "\n".join(funcs) if len(funcs) > 0 else ""
    
    def LoadPage(self, txt: str, initPosition: str):
        self.txt = txt
        self.currentIdx = {"TOP": 0, "BOTTOM": len(txt) - STEP}[initPosition]
        return
    
    def ScrollDown(self) -> str:
        self.currentIdx += STEP
        return self()
    
    def ScrollUp(self) -> str:
        self.currentIdx -= STEP
        return self()

    def SearchDown(self, query: str) -> str:
        loc = self.txt.lower().find(query.lower(), self.currentIdx if 0 < self.currentIdx else 0)
        self.currentIdx = (loc - STEP//2) if -1 != loc else self.currentIdx
        return self() if (-1 != loc) else "NOT FOUND. \nSince this is an exact match search for text fragments, you can try using shorter query phrases to increase the success rate."
    
    def SearchUp(self, query: str) -> str:
        loc = self.txt.lower().rfind(query.lower(), 0, (self.currentIdx + 1) if 0 < (self.currentIdx + 1) else 0)
        self.currentIdx = (loc - STEP//2) if -1 != loc else self.currentIdx
        return self() if (-1 != loc) else "NOT FOUND. \nSince this is an exact match search for text fragments, you can try using shorter query phrases to increase the success rate."
    
    def ReplaceText(self, replacement: str, replaceAll: bool = False):
        if (self.currentIdx >= len(self.txt)) or ((self.currentIdx + STEP) <= 0):
            return
        if replaceAll:
            self.txt = replacement
        else:
            start = self.currentIdx if self.currentIdx >= 0 else 0
            end = (self.currentIdx + STEP) if (self.currentIdx + STEP) >= 0 else 0
            self.txt = self.txt[:start] + replacement + self.txt[end:]
        return
    
    def __call__(self, prompt: bool = True) -> str:
        if (self.currentIdx >= len(self.txt)):
            return "EOF." if prompt else ""
        elif ((self.currentIdx + STEP) <= 0):
            return "FILE HEADER REACHED." if prompt else ""
        else:
            start = self.currentIdx if self.currentIdx >= 0 else 0
            end = (self.currentIdx + STEP) if (self.currentIdx + STEP) >= 0 else 0
            return self.txt[start:end] + ("\n\n" + self.ConstructPrompt() if prompt else "")