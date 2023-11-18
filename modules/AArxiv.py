
import arxiv

from common.lightRPC import makeServer
from modules.AScrollablePage import AScrollablePage

class AArxiv():
    def __init__(self):
        self.page = AScrollablePage({"SCROLLDOWNARXIV": "SCROLLDOWNARXIV<!||!>"})
        return
    
    def ArxivSearch(self, query):
        try:
            ret = str(list(arxiv.Search(query=query, max_results=40).results()))
        except Exception as e:
            print("arxiv excetption: ", e)
            ret = f"arxiv excetption: {str(e)}"
        self.page.LoadPage(str(ret), "TOP")
        return self.page()

    def ScrollDown(self):
        self.page.ScrollDown()
        return self.page()

ar = AArxiv()
makeServer(ar, "ipc:///tmp/AArxiv.ipc", ["ArxivSearch", "ScrollDown"]).Run()