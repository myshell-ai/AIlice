import weaviate
import weaviate.classes as wvc
from typing import Union

from ailice.common.lightRPC import makeServer

class AStorageWeaviate():
    def __init__(self, clusterURL, apiKey, oaiKey):
        self.clusterURL = clusterURL
        self.apiKey = apiKey
        self.oaiKey = oaiKey
        self.client = None
        return
    
    def __del__(self):
        self.client.close()
        return

    def ModuleInfo(self):
        return {"NAME": "storage", "ACTIONS": {}}
    
    def Open(self, directory: str) -> str:
        try:
            self.client = weaviate.connect_to_wcs(
                cluster_url=self.clusterURL,
                auth_credentials=weaviate.auth.AuthApiKey(self.apiKey),
                headers={
                    "X-OpenAI-Api-Key": self.oaiKey
                }
            )
        except Exception as e:
            print(f"Open() EXCEPTION. e: {str(e)}")
            return f"Open() EXCEPTION. e: {str(e)}"
    
    def Store(self, collection: str, content: Union[str,list[str]]) -> bool:
        try:
            print("collection: ", collection,". store: ", content)
            if not self.client.collections.exists(collection):
                print(f"create a new collection: {collection}")
                self.client.collections.create(
                    name=collection,
                    vectorizer_config=wvc.config.Configure.Vectorizer.text2vec_openai(),
                    generative_config=wvc.config.Configure.Generative.openai()
                )

            self.client.collections.get(collection).data.insert_many([{"text": content}] if type(content) != list else [{"text": t} for t in content])
        except Exception as e:
            print("store() EXCEPTION: ", e)
            return False
        return True
    
    def Query(self, collection: str, clue: str, num_results:int=1) -> list[tuple[str,float]]:
        try:
            response = self.client.collections.get(collection).query.near_text(
                query=clue,
                limit=num_results
            )
            
            ret = None
            if (0 < len(response.objects)):
                ret = [(r.properties['text'], r.metadata.distance) for r in response.objects]
            print("query: ", collection, ".", clue, " -> ", ret)
            return ret
        except Exception as e:
            print("query() EXCEPTION: ", e)
            return []

    def Recall(self, collection: str, query: str, num_results:int=1) -> list[tuple[str,float]]:
        return self.Query(collection=collection, clue=query, num_results=num_results)
    
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--addr',type=str, help="The address where the service runs on.")
    parser.add_argument('--clusterURL',type=str, help="The weaviate cluster url.")
    parser.add_argument('--apiKey',type=str, help="The api key for this cluster.")
    parser.add_argument('--oaiKey',type=str, help="The OpenAI api key.")

    args = parser.parse_args()
    makeServer(AStorageWeaviate, {"clusterURL": args.clusterURL, "apiKey": args.apiKey, "oaiKey": args.oaiKey}, args.addr, ["ModuleInfo", "Open", "Reset", "Store", "Query", "Recall"]).Run()

if __name__ == '__main__':
    main()
