import os
import time
import pickle
import traceback
import importlib.util
import numpy as np
from typing import Union
from huggingface_hub import hf_hub_download

from threading import Thread, Lock

from ailice.common.lightRPC import makeServer

INFERENCE_ENGINE = None
if (None != importlib.util.find_spec("llama_cpp")):
    from llama_cpp import Llama
    INFERENCE_ENGINE = "llama_cpp"
elif (None != importlib.util.find_spec("gpt4all")):
    from gpt4all import GPT4All, Embed4All
    INFERENCE_ENGINE = "gpt4all"

MODEL = 'nomic-ai/nomic-embed-text-v1-GGUF'
FILE_NAME = 'nomic-embed-text-v1.Q8_0.gguf'

model = None
modelPath = None
modelLock = Lock()

class AStorageVecDB():
    def __init__(self):
        self.data = {"model": MODEL, "file": FILE_NAME, "collections": {}}
        self.dir = None
        self.buffers = {}
        self.buffersLock = Lock()
        self.hippocampus = Thread(target=self.Hippocampus, args=())
        self.hippocampus.start()
        return

    def ModuleInfo(self):
        return {"NAME": "storage", "ACTIONS": {}}

    def CalcEmbeddings(self, txts: list[str]):
        global model, modelLock
        with modelLock:
            return np.array(model.embed(txts))
    
    def Hippocampus(self):
        while True:
            with self.buffersLock:
                for collection in self.buffers:
                    if len(self.buffers[collection]['texts']) == 0:
                        continue
                    
                    with self.buffers[collection]['lock']:
                        try:
                            embeddings = self.CalcEmbeddings(self.buffers[collection]['texts'])
                            for txt, emb in zip(self.buffers[collection]['texts'], embeddings):
                                if txt not in self.data["collections"][collection]:
                                    self.data["collections"][collection][txt] = emb
                            self.Dump(self.dir)
                            self.buffers[collection]['texts'] = []
                        except Exception as e:
                            continue #TODO.
            time.sleep(0.1)
    
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

    def PrepareModel(self) -> str:
        global model, modelPath, modelLock

        ggufFile = hf_hub_download(repo_id=self.data['model'],filename=self.data['file'])
        with modelLock:
            if model and ggufFile == modelPath:
                return f"Embedding model {self.data['model']} has already been loaded."
            
            if "llama_cpp" == INFERENCE_ENGINE:
                model = Llama(
                    model_path=ggufFile,
                    embedding=True,
                    n_gpu_layers=-1, # Uncomment to use GPU acceleration
                    # seed=1337, # Uncomment to set a specific seed
                    # n_ctx=2048, # Uncomment to increase the context window
                )
                modelPath = ggufFile
                return "Embedding model has been loaded."
            elif "gpt4all" == INFERENCE_ENGINE:
                gpus = []
                try:
                    gpus = GPT4All.list_gpus()
                    device = gpus[0] if len(gpus) > 0 else "cpu"
                except Exception as e:
                    device = "cpu"
                model = Embed4All(ggufFile, device = device)
                modelPath = ggufFile
                return f"GPUs found on this device: {gpus}. Embedding model has been loaded on {device}."
            else:
                return "No inference engine was found. Please use one of the following commands to install: `pip install gpt4all` or `ailice_turbo`."
    
    def Open(self, directory: str) -> str:
        try:
            if "" == directory.strip():
                self.dir = None
                r = self.PrepareModel()
                return f"{r}\nvector database has been switched to a non-persistent version. model: {self.data['model']}, gguf: {self.data['file']}"
            else:
                self.dir = directory
                self.Load(directory)
                r = self.PrepareModel()
                return f"{r}\nvector database under {directory} is opened. model: {self.data['model']}, gguf: {self.data['file']}"
        except Exception as e:
            print(f"Open() EXCEPTION. e: {str(e)}")
            raise e
    
    def Reset(self) -> str:
        self.data["collections"].clear()
        return "vector database reseted."
    
    def Store(self, collection: str, content: Union[str,list[str]]) -> bool:
        try:
            print("collection: ", collection,". store: ", content)
            if collection not in self.data["collections"]:
                self.data["collections"][collection] = dict()
                with self.buffersLock:
                    self.buffers[collection]={"texts": [], "lock": Lock()}
            
            texts = [content] if type(content) != list else content
            with self.buffers[collection]['lock']:
                self.buffers[collection]['texts'] += texts
        except Exception as e:
            print("store() EXCEPTION: ", e, traceback.print_tb(e.__traceback__))
            return False
        return True
    
    def Query(self, collection: str, clue: str = "", keywords: list[str] = None, num_results:int=1) -> list[tuple[str,float]]:
        try:
            if collection not in self.data["collections"]:
                return []
            
            while (collection in self.buffers) and (len(self.buffers[collection]['texts']) > 0):
                time.sleep(0.1)
            
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
    
    def Recall(self, collection: str, query: str, num_results:int=1) -> list[tuple[str,float]]:
        return self.Query(collection=collection, clue=query, num_results=num_results)
    
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--addr',type=str, help="The address where the service runs on.")
    args = parser.parse_args()
    makeServer(AStorageVecDB, dict(), args.addr, ["ModuleInfo", "Open", "Reset", "Store", "Query", "Recall"]).Run()

if __name__ == '__main__':
    main()
