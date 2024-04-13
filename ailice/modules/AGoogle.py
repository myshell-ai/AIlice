import random
from googlesearch import search

from ailice.common.lightRPC import makeServer
from ailice.modules.AScrollablePage import AScrollablePage

class AGoogle():
    def __init__(self):
        self.sessions = {}
        self.functions = {"SCROLLDOWN": "#scroll down the page: \nSCROLL_DOWN_GOOGLE<!|session: str|!>"}
        return
    
    def ModuleInfo(self):
        return {"NAME": "google", "ACTIONS": {"GOOGLE": {"func": "Google", "prompt": "Use google to search internet content."},
                                              "SCROLL_DOWN_GOOGLE": {"func": "ScrollDown", "prompt": "Scroll down the results."}}}
    
    def GetSessionID(self) -> str:
        id = f"session_{str(random.randint(0,99999999))}"
        while id in self.sessions:
            id = f"session_{str(random.randint(0,99999999))}"
        return id
    
    def Google(self, keywords: str) -> str:
        try:
            res = search(keywords, num_results=20, advanced=True, sleep_interval=5) #sleep_interval will work when num_results>100.
            ret = list(res)
        except Exception as e:
            print("google excetption: ", e)
            ret = f"google excetption: {str(e)}"
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
    makeServer(AGoogle, dict(), args.addr, ["ModuleInfo", "Google", "ScrollDown"]).Run()

if __name__ == '__main__':
    main()