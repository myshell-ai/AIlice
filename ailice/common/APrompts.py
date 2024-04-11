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
    
    def RegisterPrompt(self, promptClass) -> str:
        if promptClass.PROMPT_NAME in self.prompts:
            return f"{promptClass.PROMPT_NAME} is already exist, please use another name."
        self.prompts[promptClass.PROMPT_NAME] = promptClass
        
        if not self.storage.Store(self.collection + "_prompts", json.dumps({"name": promptClass.PROMPT_NAME, "desc": promptClass.PROMPT_DESCRIPTION})):
            self.prompts.pop(promptClass.PROMPT_NAME)
            return "STORE prompt to vecdb FAILED, there may be a problem with the vector database."
        return ""

    def __getitem__(self, promptName: str):
        return self.prompts[promptName]
    
    def __iter__(self):
        return iter(self.prompts)
    
promptsManager = APromptsManager()