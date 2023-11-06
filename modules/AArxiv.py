
import arxiv

from common.lightRPC import makeServer

class AArxiv():
    def __init__(self):
        return
    
    def ArxivSearch(self, query):
        res = arxiv.Search(query=query, max_results=2)
        return str(list(res.results()))

ar = AArxiv()
makeServer(ar, "ipc:///tmp/AArxiv.ipc").Run()