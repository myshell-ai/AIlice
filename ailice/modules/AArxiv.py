
import arxiv
import random

from ailice.common.lightRPC import makeServer
from ailice.modules.AScrollablePage import AScrollablePage

class AArxiv():
    def __init__(self):
        self.sessions = {}
        self.functions = {"SCROLLDOWN": "#scroll down the page: \nSCROLL_DOWN_ARXIV<!|session: str|!>"}
        return
    
    def ModuleInfo(self):
        return {"NAME": "arxiv", "ACTIONS": {"ARXIV": {"func": "ArxivSearch", "prompt": "Use arxiv to search academic literatures."},
                                             "SCROLL_DOWN_ARXIV": {"func": "ScrollDown", "prompt": "Scroll down the results."}}}
    
    def GetSessionID(self) -> str:
        id = f"session_{str(random.randint(0,99999999))}"
        while id in self.sessions:
            id = f"session_{str(random.randint(0,99999999))}"
        return id
    
    def ArxivSearch(self, keywords: str) -> str:
        try:
            ret = str(list(arxiv.Search(query=keywords, max_results=40).results()))
        except Exception as e:
            print("arxiv excetption: ", e)
            ret = f"arxiv excetption: {str(e)}"
        session = self.GetSessionID()
        self.sessions[session] = AScrollablePage(functions=self.functions)
        self.sessions[session].LoadPage(str(ret), "TOP")
        return self.sessions[session]() + "\n\n" + f'Session name: "{session}"\n'

    def ScrollDown(self, session: str) -> str:
        return self.sessions[session].ScrollDown() + "\n\n" + f'Session name: "{session}"\n'
    
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--addr',type=str, help="The address where the service runs on.")
    args = parser.parse_args()
    makeServer(AArxiv, dict(), args.addr, ["ModuleInfo", "ArxivSearch", "ScrollDown"]).Run()

if __name__ == '__main__':
    main()