import chromadb
import uuid

from ailice.common.lightRPC import makeServer

class AStorageChromaDB():
    def __init__(self):
        self.chroma_client = chromadb.Client()
        return

    def ModuleInfo(self):
        return {"NAME": "storage", "ACTIONS": {}}
    
    def Open(self, directory: str) -> str:
        try:
            if "" == directory.strip():
                self.chroma_client = chromadb.Client()
                return "chroma database has been switched to a non-persistent version."
            else:
                self.chroma_client = chromadb.PersistentClient(directory)
                return f"chroma database under {directory} is opened."
        except Exception as e:
            print(f"Open() EXCEPTION. e: {str(e)}")
            return f"Open() EXCEPTION. e: {str(e)}"
    
    def Reset(self) -> str:
        self.chroma_client.reset()
        return "chroma database reseted."
    
    def Store(self, collection: str, txt: str) -> bool:
        try:
            print("collection: ", collection,". store: ", txt)
            self.chroma_client.get_or_create_collection(name=collection).add(documents = [txt],
                                                                             ids = [str(uuid.uuid4())])
        except Exception as e:
            print("store() EXCEPTION: ", e)
            return False
        return True
    
    def Query(self, collection: str, clue: str, num_results:int=1):# -> list(tuple[str,float]):
        try:
            res = self.chroma_client.get_collection(name=collection).query(query_texts=[clue],n_results=num_results)
            ret = None
            if (0 < len(res['documents'])):
                ret = [(txt, dist) for txt, dist in zip(res['documents'][0], res['distances'][0])]
            print("query: ", collection, ".", clue, " -> ", ret)
            return ret
        except Exception as e:
            print("query() EXCEPTION: ", e)
            return []
        
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--addr',type=str, help="The address where the service runs on.")
    args = parser.parse_args()
    makeServer(AStorageChromaDB, dict(), args.addr, ["ModuleInfo", "Open", "Reset", "Store", "Query"]).Run()

if __name__ == '__main__':
    main()
