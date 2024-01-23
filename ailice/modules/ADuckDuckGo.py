import requests

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
        params = {
            'q': keywords,
            'format': 'json',
        }

        try:
            response = requests.get(self.baseURL, params=params)
            ret = str(response.json())
        except requests.RequestException as e:
            print(f"Error during the request: {e}")
            ret = str(e)
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