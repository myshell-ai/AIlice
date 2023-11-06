from googlesearch import search

from common.lightRPC import makeServer

class AGoogle():
    def __init__(self):
        self.lastSearch = 0
        return
    
    def Google(self, keywords):
        try:
            res = search(keywords, num_results=2, advanced=True)
            ret = list(res)
        except Exception as e:
            print("google excetption: ", e)
            return "google search failed."
        return str(ret)
    

google = AGoogle()
makeServer(google, "ipc:///tmp/AGoogle.ipc").Run()