import chromadb
import uuid

from common.lightRPC import makeServer

class AStorageChromaDB():
    def __init__(self):
        self.chroma_client = chromadb.Client()
        self.collections = dict()
        return

    def ModuleInfo(self):
        return {"NAME": "storage", "ACTIONS": {}}
    
    def Store(self, collection: str, txt: str) -> bool:
        try:
            print("collection: ", collection,". store: ", txt)
            if not (collection in self.collections):
                self.collections[collection] = self.chroma_client.create_collection(name=collection)

            self.collections[collection].add(documents = [txt],
                                            ids = [str(uuid.uuid4())])
        except Exception as e:
            print("store() EXCEPTION: ", e)
            return False
        return True
    
    def Query(self, collection: str, clue: str, num_results:int=1):# -> list(tuple[str,float]):
        try:
            res = self.collections[collection].query(query_texts=[clue],n_results=num_results)
            ret = None
            if (0 < len(res['documents'])):
                ret = [(txt, dist) for txt, dist in zip(res['documents'][0], res['distances'][0])]
            print("query: ", collection, ".", clue, " -> ", ret)
            return ret
        except Exception as e:
            print("query() EXCEPTION: ", e)
            return []
        


storage = AStorageChromaDB()
makeServer(storage, "ipc:///tmp/AIliceStorage.ipc", ["ModuleInfo", "Store", "Query"]).Run()