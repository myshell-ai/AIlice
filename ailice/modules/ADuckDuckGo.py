import asyncio
import random
from duckduckgo_search import DDGS

from ailice.common.lightRPC import makeServer
from ailice.modules.AScrollablePage import AScrollablePage

class ADuckDuckGo():
    def __init__(self):
        self.baseURL = "https://api.duckduckgo.com/"
        self.sessions = {}
        self.functions = {"SCROLLDOWN": "#scroll down the page: \nSCROLL-DOWN-DUCKDUCKGO<!|session: str|!>"}
        return
    
    def ModuleInfo(self):
        return {"NAME": "duckduckgo", "ACTIONS": {"DUCKDUCKGO": {"func": "DuckDuckGo", "prompt": "Use duckduckgo to search internet content.", "type": "primary"},
                                                  "SCROLL-DOWN-DUCKDUCKGO": {"func": "ScrollDown", "prompt": "Scrolldown the results.", "type": "supportive"}}}
    
    def GetSessionID(self) -> str:
        id = f"session-{str(random.randint(0,99999999))}"
        while id in self.sessions:
            id = f"session-{str(random.randint(0,99999999))}"
        return id
    
    def DuckDuckGo(self, keywords: str) -> str:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            with DDGS() as ddgs:
                results = [r for r in ddgs.text(keywords, max_results=10)]
            ret = str(results) if len(results) > 0 else "No search results were found. Please check if you used overly complex keywords or unsupported search syntax. Note that relaxing your search terms is an effective strategy when no valid search results are returned."
        except Exception as e:
            print(f"Error during the request: {e}")
            ret = str(e)
        finally:
            loop.close()
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
    makeServer(ADuckDuckGo, dict(), args.addr, ["ModuleInfo", "DuckDuckGo", "ScrollDown"]).Run()

if __name__ == '__main__':
    main()