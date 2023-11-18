from googlesearch import search

from common.lightRPC import makeServer
from modules.AScrollablePage import AScrollablePage

class AGoogle():
    def __init__(self):
        self.page = AScrollablePage(functions={"SCROLLDOWN": "SCROLLDOWNGOOGLE<!||!>"})
        return
    
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

google = AGoogle()
makeServer(google, "ipc:///tmp/AGoogle.ipc", ["Google", "ScrollDown"]).Run()