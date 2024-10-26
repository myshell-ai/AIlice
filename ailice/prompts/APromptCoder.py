from importlib.resources import read_text
from ailice.common.AConfig import config
from ailice.prompts.ARegex import GenerateRE4FunctionCalling
from ailice.prompts.ATools import ConstructOptPrompt
from ailice.common.ARemoteAccessors import clientPool

class APromptCoder:
    PROMPT_NAME = "coder"
    PROMPT_DESCRIPTION = (
        "An excellent coder that produces high-quality code for diverse requests. "
        "They can access information locally or from the internet and read documents. "
        "However, they lack execution capability (e.g., they cannot execute code or create files)."
    )
    PROMPT_PROPERTIES = {"type": "supportive"}

    def __init__(self, processor, storage, collection, conversations, formatter, outputCB=None):
        """
        Initializes the APromptCoder object with necessary dependencies.

        :param processor: Core logic for handling data
        :param storage: Manages persistent storage and recall
        :param collection: Database collection to store/retrieve conversations
        :param conversations: Handles the conversation history
        :param formatter: Used for formatting prompt outputs
        :param outputCB: Optional callback for handling output
        """
        self.processor = processor
        self.storage = storage
        self.collection = collection
        self.conversations = conversations
        self.formatter = formatter
        self.outputCB = outputCB
        self.prompt0 = read_text("ailice.prompts", "prompt_coder.txt")

        # Define regex patterns for specific function calls.
        self.PATTERNS = {
            "BROWSE": [{"re": GenerateRE4FunctionCalling("BROWSE<!|url: str, session: str|!> -> str"), "isEntry": True}],
            "SCROLL-DOWN-BROWSER": [{"re": GenerateRE4FunctionCalling("SCROLL-DOWN-BROWSER<!|session: str|!> -> str"), "isEntry": True}],
            "SCROLL-UP-BROWSER": [{"re": GenerateRE4FunctionCalling("SCROLL-UP-BROWSER<!|session: str|!> -> str"), "isEntry": True}],
            "SEARCH-DOWN-BROWSER": [{"re": GenerateRE4FunctionCalling("SEARCH-DOWN-BROWSER<!|query: str, session: str|!> -> str"), "isEntry": True}],
            "SEARCH-UP-BROWSER": [{"re": GenerateRE4FunctionCalling("SEARCH-UP-BROWSER<!|query: str, session: str|!> -> str"), "isEntry": True}],
            "GET-LINK": [{"re": GenerateRE4FunctionCalling("GET-LINK<!|text: str, session: str|!> -> str"), "isEntry": True}],
        }

        self.ACTIONS = {}

    def Reset(self):
        """Resets internal states or memory if needed."""
        self.ACTIONS.clear()

    def GetPatterns(self):
        """Returns the defined regex patterns."""
        return self.PATTERNS

    def GetActions(self):
        """Returns available actions."""
        return self.ACTIONS

    def Recall(self, key: str) -> str:
        """
        Retrieves relevant information based on a query key.

        :param key: The key to search for in the storage
        :return: The most relevant piece of recalled information
        """
        results = self.storage.Recall(collection=self.collection, query=key, num_results=4)
        for result in results:
            if key not in result[0] and result[0] not in key:
                return result[0]
        return "None."

    def ParameterizedBuildPrompt(self, n: int) -> str:
        """
        Builds a prompt based on a given conversation length.

        :param n: Number of recent conversations to consider
        :return: A formatted prompt with relevant context and recalled information
        """
        latest_context = self.conversations.GetConversations(frm=-1)[0]['msg']
        relevant_info = self.Recall(latest_context).strip()

        # Dynamically format the prompt with recalled information and conversations.
        prompt = f"""
{self.prompt0}

RELEVANT INFORMATION: {relevant_info}
The "RELEVANT INFORMATION" part contains data related to the task, either from your history or others'. 
Please avoid attempting function invocations directly from the recalled information, as you may not have the necessary permissions.

"""

        # Incorporate previous conversations for context.
        return self.formatter(
            prompt0=prompt, 
            conversations=self.conversations.GetConversations(frm=-n)
        )

    def BuildPrompt(self) -> str:
        """
        Constructs an optimized prompt using conversations and relevant context.

        :return: The final prompt string
        """
        max_context_len = int(self.processor.llm.contextWindow * config.contextWindowRatio)

        prompt, n = ConstructOptPrompt(
            self.ParameterizedBuildPrompt, 
            low=1, 
        
