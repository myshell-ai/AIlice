import asyncio
from duckduckgo_search import DDGS

from ailice.common.lightRPC import makeServer
from ailice.modules.AScrollablePage import AScrollablePage

class ADuckDuckGo():
    def __init__(self):
        self.baseURL = "https://api.duckduckgo.com/"
        self.page = AScrollablePage(functions={"SCROLLDOWN": "SCROLLDOWNDUCKDUCKGO"})
        return
    
    def ModuleInfo(self):
        return {"NAME": "duckduckgo", "ACTIONS": {"DUCKDUCKGO": {"func": "DuckDuckGo", "prompt": "Use duckduckgo to search internet content."},
                                                  "SCROLLDOWNDUCKDUCKGO": {"func": "ScrollDown", "prompt": "Scrolldown the results."}}}
    
    def DuckDuckGo(self, keywords: str) -> str:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            with DDGS() as ddgs:
                ret = [r for r in ddgs.text(keywords, max_results=10)]
        except Exception as e:
            print(f"Error during the request: {e}")
            ret = str(e)
        finally:
            loop.close()
        self.page.LoadPage(str(ret), "TOP")
        return self.page()
    
    def ScrollDown(self) -> str:
        self.page.ScrollDown()
        return self.page()

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--addr',type=str, help="The address where the service runs on.")
    args = parser.parse_args()
    makeServer(ADuckDuckGo, dict(), args.addr, ["ModuleInfo", "DuckDuckGo", "ScrollDown"]).Run()

if __name__ == '__main__':
    main()