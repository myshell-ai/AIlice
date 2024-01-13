from googlesearch import search

from ailice.common.lightRPC import makeServer
from ailice.modules.AScrollablePage import AScrollablePage

class AGoogle():
    def __init__(self):
        self.page = AScrollablePage(functions={"SCROLLDOWN": "SCROLLDOWNGOOGLE"})
        return
    
    def ModuleInfo(self):
        return {"NAME": "google", "ACTIONS": {"GOOGLE": {"sig": "Google(keywords:str)->str", "prompt": "Use google to search internet content."},
                                              "SCROLLDOWNGOOGLE": {"sig": "ScrollDown()->str", "prompt": "Scroll down the results."}}}
    
    def Google(self, keywords):
        try:
            res = search(keywords, num_results=20, advanced=True, sleep_interval=5) #sleep_interval will work when num_results>100.
            ret = list(res)
        except Exception as e:
            print("google excetption: ", e)
            ret = f"google excetption: {str(e)}"
        self.page.LoadPage(str(ret), "TOP")
        return self.page()
    
    def ScrollDown(self):
        self.page.ScrollDown()
        return self.page()

makeServer(AGoogle, "ipc:///tmp/AGoogle.ipc", ["ModuleInfo", "Google", "ScrollDown"]).Run()