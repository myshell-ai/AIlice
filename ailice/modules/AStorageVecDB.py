import os
import pickle
import traceback
import numpy as np
from huggingface_hub import hf_hub_download
from llama_cpp import Llama

from ailice.common.lightRPC import makeServer

MODEL = 'nomic-ai/nomic-embed-text-v1-GGUF'
FILE_NAME = 'nomic-embed-text-v1.Q8_0.gguf'

class AStorageVecDB():
    def __init__(self):
        self.model = None
        self.data = {"model": MODEL, "file": FILE_NAME, "collections": {}}
        self.dir = None
        return

    def ModuleInfo(self):
        return {"NAME": "storage", "ACTIONS": {}}

    def CalcEmbeddings(self, txts: list[str]):
        return np.array(self.model.embed(txts))
    
    def Dump(self, dir):
        if None != dir:
            with open(dir+"/vecdb", 'wb') as f:
                pickle.dump(self.data, f)
        return
        
    def Load(self, dir):
        if os.path.exists(dir+"/vecdb"):
            with open(dir+"/vecdb", 'rb') as f:
                self.data = pickle.load(f)
        return

    def PrepareModel(self):
        ggufFile = hf_hub_download(repo_id=self.data['model'],filename=self.data['file'])
        self.model = Llama(
            model_path=ggufFile,
            embedding=True,
            n_gpu_layers=-1, # Uncomment to use GPU acceleration
            # seed=1337, # Uncomment to set a specific seed
            # n_ctx=2048, # Uncomment to increase the context window
        )
        return
    
    def Open(self, directory: str) -> str:
        try:
            if "" == directory.strip():
                self.dir = None
                self.PrepareModel()
                return f"vector database has been switched to a non-persistent version. model: {self.data['model']}, gguf: {self.data['file']}"
            else:
                self.dir = directory
                self.Load(directory)
                self.PrepareModel()
                return f"vector database under {directory} is opened. model: {self.data['model']}, gguf: {self.data['file']}"
        except Exception as e:
            print(f"Open() EXCEPTION. e: {str(e)}")
            raise e
    
    def Reset(self) -> str:
        self.data["collections"].clear()
        return "vector database reseted."
    
    def Store(self, collection: str, txt: str) -> bool:
        try:
            print("collection: ", collection,". store: ", txt)

            if collection not in self.data["collections"]:
                self.data["collections"][collection] = dict()
            if txt not in self.data["collections"][collection]:
                self.data["collections"][collection][txt] = self.CalcEmbeddings([txt])[0]
            self.Dump(self.dir)
        except Exception as e:
            print("store() EXCEPTION: ", e, traceback.print_tb(e.__traceback__))
            return False
        return True
    
    def Query(self, collection: str, clue: str = "", keywords: list[str] = None, num_results:int=1):# -> list(tuple[str,float]):
        try:
            if collection not in self.data["collections"]:
                return []
            
            results = [txt for txt,_ in self.data['collections'][collection].items()]
            if None != keywords:
                for keyword in keywords:
                    results = [txt for txt in results if keyword in txt]
            
            if clue in ["", None]:
                results = [(r, None) for r in results]
                return results[:num_results] if num_results > 0 else results

            query = self.CalcEmbeddings([clue])[0]
            temp = [(txt, np.sum((self.data["collections"][collection][txt]-query)**2,axis=0)[()]) for txt in results]
            ret = sorted(temp, key=lambda x: x[1])[:num_results] if num_results > 0 else temp
            print("query: ", collection, ".", clue, " -> ", ret)
            return ret
        except Exception as e:
            print("query() EXCEPTION: ", e, traceback.print_tb(e.__traceback__))
            return []
    
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--addr',type=str, help="The address where the service runs on.")
    args = parser.parse_args()
    makeServer(AStorageVecDB, dict(), args.addr, ["ModuleInfo", "Open", "Reset", "Store", "Query"]).Run()

if __name__ == '__main__':
    main()
