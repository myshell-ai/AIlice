from googlesearch import search

from ailice.common.lightRPC import makeServer
from ailice.modules.AScrollablePage import AScrollablePage

class AGoogle():
    def __init__(self):
        self.page = AScrollablePage(functions={"SCROLLDOWN": "SCROLLDOWNGOOGLE"})
        return
    
    def ModuleInfo(self):
        return {"NAME": "google", "ACTIONS": {"GOOGLE": {"func": "Google", "prompt": "Use google to search internet content."},
                                              "SCROLLDOWNGOOGLE": {"func": "ScrollDown", "prompt": "Scroll down the results."}}}
    
    def Google(self, keywords: str) -> str:
        try:
            res = search(keywords, num_results=20, advanced=True, sleep_interval=5) #sleep_interval will work when num_results>100.
            ret = list(res)
        except Exception as e:
            print("google excetption: ", e)
            ret = f"google excetption: {str(e)}"
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
    makeServer(AGoogle, dict(), args.addr, ["ModuleInfo", "Google", "ScrollDown"]).Run()

if __name__ == '__main__':
    main()