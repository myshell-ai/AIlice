import json

class APromptsManager():
    def __init__(self):
        self.prompts = dict()
        self.storage = None
        self.collection = None
        return
    
    def Init(self, storage, collection):
        self.storage = storage
        self.collection = collection
        return
    
    def RegisterPrompts(self, promptClasses) -> str:
        for promptClass in promptClasses:
            if promptClass.PROMPT_NAME in self.prompts:
                return f"{promptClass.PROMPT_NAME} is already exist, please use another name."
        
        try:
            self.storage.Store(self.collection + "_prompts", [json.dumps({"name": promptClass.PROMPT_NAME, "desc": promptClass.PROMPT_DESCRIPTION, "properties": promptClass.PROMPT_PROPERTIES}) for promptClass in promptClasses])
            for promptClass in promptClasses:
                self.prompts[promptClass.PROMPT_NAME] = promptClass
            return ""
        except Exception as e:
            return f"STORE prompt to vecdb FAILED, there may be a problem with the vector database. Exception: {str(e)}"

    def __getitem__(self, promptName: str):
        return self.prompts[promptName]
    
    def __iter__(self):
        return iter(self.prompts)