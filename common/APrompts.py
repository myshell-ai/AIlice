class APromptsManager():
    def __init__(self):
        self.prompts = dict()
        return
    
    def RegisterPrompt(self, promptClass):
        assert promptClass.PROMPT_NAME not in self.prompts, f"{promptClass.PROMPT_NAME} is already exist, please use another name."
        self.prompts[promptClass.PROMPT_NAME] = promptClass
        return

    def __getitem__(self, promptName: str):
        return self.prompts[promptName]
    
    def __iter__(self):
        return iter(self.prompts)
    
promptsManager = APromptsManager()