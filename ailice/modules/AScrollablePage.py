import re

STEP = 8192

class AScrollablePage():
    def __init__(self, functions: dict[str, str]):
        self.txt = None
        self.indivisibles = []
        self.currentIdx = None
        self.currentEnd = None
        self.functions = functions
        return
    
    def Clamp(self, x: int) -> int:
        r = 0 if x < 0 else x
        r = len(self.txt) if r > len(self.txt) else r
        return r
    
    def BoundCorrection(self, edge: int) -> int:
        for l,r in self.indivisibles:
            if l < edge and edge < r:
                return (l, r)
        return (edge, edge)
    
    def CalcWindow(self, pos: int, posType: str) -> tuple[int, int]:
        pos = self.Clamp(pos)
        
        delta = {"start": 0, "mid": -STEP//2, "end": -STEP}
        start = pos + delta[posType]
        end = start + STEP
        start = self.Clamp(start)
        end = self.Clamp(end)
        
        lBound, rBound = self.BoundCorrection(start), self.BoundCorrection(end)

        if "start" == posType:
            return start, rBound[0] if rBound[0] > start else rBound[1]
        elif "end" == posType:
            return lBound[1] if lBound[1] < end else lBound[0], end
        elif "mid" == posType:
            return (lBound[1], rBound[0]) if lBound[1] < rBound[0] else (lBound[0], rBound[1])
    
    def ConstructPrompt(self) -> str:
        ret = "To avoid excessive consumption of context space due to lengthy content, we have paginated the entire content. This is just one page, to browse more content, please use the following function(s) for page navigation.\n"
        funcs = []
        if ('SCROLLDOWN' in self.functions) and (self.currentEnd < len(self.txt)):
            funcs.append(self.functions['SCROLLDOWN'])
        if ('SCROLLUP' in self.functions) and (self.currentIdx > 0):
            funcs.append(self.functions['SCROLLUP'])
        if ('SEARCHDOWN' in self.functions) and (self.currentEnd < len(self.txt)):
            funcs.append(self.functions['SEARCHDOWN'])
        if ('SEARCHUP' in self.functions) and (self.currentIdx > 0):
            funcs.append(self.functions['SEARCHUP'])
        pos = self.currentIdx
        prior = (float(pos)/float(len(self.txt))) * 100
        remaining = (float(len(self.txt) - self.currentEnd)/float(len(self.txt))) * 100
        return f"Prior: {prior:.1f}% / Remaining: {remaining:.1f}% \n\n" + ((ret + "\n".join(funcs)) if len(funcs) > 0 else "")
    
    def LoadPage(self, txt: str, initPosition: str):
        self.txt = txt
        self.indivisibles = [(match.start(), match.end()) for match in re.finditer(r'!\[([^\]]*)\]\(([^)]+)\)', self.txt)]
        self.currentIdx, self.currentEnd = {"TOP": self.CalcWindow(0, "start"), "BOTTOM": self.CalcWindow(len(txt), "end")}[initPosition]
        return
    
    def ScrollDown(self) -> str:
        self.currentIdx, self.currentEnd = self.CalcWindow(self.currentEnd, "start")
        return self()
    
    def ScrollUp(self) -> str:
        self.currentIdx, self.currentEnd = self.CalcWindow(self.currentIdx, "end")
        return self()

    def SearchDown(self, query: str) -> str:
        loc = self.txt.lower().find(query.lower(), self.currentIdx)
        self.currentIdx, self.currentEnd = self.CalcWindow(loc, "mid") if -1 != loc else (self.currentIdx, self.currentEnd)
        return self() if (-1 != loc) else "NOT FOUND. \nSince this is an exact match search for text fragments, you can try using shorter query phrases to increase the success rate."
    
    def SearchUp(self, query: str) -> str:
        loc = self.txt.lower().rfind(query.lower(), 0, self.currentIdx)
        self.currentIdx, self.currentEnd = self.CalcWindow(loc, "mid") if -1 != loc else (self.currentIdx, self.currentEnd)
        return self() if (-1 != loc) else "NOT FOUND. \nSince this is an exact match search for text fragments, you can try using shorter query phrases to increase the success rate."
    
    def ReplaceText(self, replacement: str, replaceAll: bool = False):
        if replaceAll:
            self.txt = replacement
        else:
            self.txt = self.txt[:self.currentIdx] + replacement + self.txt[self.currentEnd:]
        return
    
    def __call__(self, prompt: bool = True) -> str:
        ret = self.txt[self.currentIdx:self.currentEnd]
        return f"\n\n---\n\n{ret}\n\n---\n\n{self.ConstructPrompt()}" if prompt else ret