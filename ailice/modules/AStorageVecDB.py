import os
import pickle
import torch
import traceback
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel

from ailice.common.lightRPC import makeServer

TOKENIZER = 'bert-base-uncased'
MODEL = 'nomic-ai/nomic-embed-text-v1'

class AStorageVecDB():
    def __init__(self):
        self.tokenizer = None
        self.model = None
        self.data = {"tokenizer": TOKENIZER, "model": MODEL, "collections": {}}
        self.dir = None
        return

    def ModuleInfo(self):
        return {"NAME": "storage", "ACTIONS": {}}

    def CalcEmbeddings(self, txts: list[str]):
        encodedInput = self.tokenizer(txts, padding=True, truncation=True, return_tensors='pt')
        with torch.no_grad():
            modelOutput = self.model(**encodedInput)

        tokenEmbeddings = modelOutput[0]#(b,t,m)
        inputMaskExpanded = encodedInput['attention_mask'].unsqueeze(-1).expand(tokenEmbeddings.size()).float()
        embeddings = torch.sum(tokenEmbeddings * inputMaskExpanded, 1) / torch.clamp(inputMaskExpanded.sum(1), min=1e-9)#(b,m)
        embeddings = F.normalize(embeddings, p=2, dim=1)
        return embeddings
    
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
        self.tokenizer = AutoTokenizer.from_pretrained(self.data["tokenizer"])
        self.model = AutoModel.from_pretrained(self.data["model"], trust_remote_code=True)
        self.model.eval()
        return
    
    def Open(self, directory: str) -> str:
        try:
            if "" == directory.strip():
                self.dir = None
                self.PrepareModel()
                return f"vector database has been switched to a non-persistent version. tokenizer: {self.data['tokenizer']}, model: {self.data['model']}"
            else:
                self.dir = directory
                self.Load(directory)
                self.PrepareModel()
                return f"vector database under {directory} is opened. tokenizer: {self.data['tokenizer']}, model: {self.data['model']}"
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
    
    def Query(self, collection: str, clue: str, num_results:int=1):# -> list(tuple[str,float]):
        try:
            if collection not in self.data["collections"]:
                return []
            query = self.CalcEmbeddings([clue])[0]
            temp = [(txt, torch.sum((emb-query)**2,dim=0).item()) for txt, emb in self.data["collections"][collection].items()]
            ret = sorted(temp, key=lambda x: x[1])[:num_results]
            print("query: ", collection, ".", clue, " -> ", ret)
            return ret
        except Exception as e:
            print("query() EXCEPTION: ", e, traceback.print_tb(e.__traceback__))
            return []
    
    def Search(self, collection: str, keywords: list[str], num_results: int = 1) -> list[str]:
        results = [txt for txt,_ in self.data['collections'][collection].items()]
        for keyword in keywords:
            results = [txt for txt in results if keyword in txt]
        return results[:num_results] if num_results >= 0 else results
    
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--addr',type=str, help="The address where the service runs on.")
    args = parser.parse_args()
    makeServer(AStorageVecDB, dict(), args.addr, ["ModuleInfo", "Open", "Reset", "Store", "Query", "Search"]).Run()

if __name__ == '__main__':
    main()
