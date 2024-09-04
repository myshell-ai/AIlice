import arxiv
import random

#ailice is already exist in the local running environment, please do not try to install or build them.
from ailice.common.lightRPC import makeServer
#For cases where the returned result is too long, we recommend use AScrollablePage class to implement a scrolling page effect. AScrollablePage contains the following methods: LoadPage(txt: str, initPosition: str)->str, ScrollDown()->str, ScrollUp()->str, SearchDown(query: str)->str, SearchUp(query: str)->str.
from ailice.modules.AScrollablePage import AScrollablePage

class AArxiv():
    def __init__(self):
        #All interfaces exposed by the ext-module to users should be stateless. We use sessions to handle state operations.
        self.sessions = {}
        #The parameter is a dict, used to map the keys("SCROLLUP" / "SCROLLDOWN" / "SEARCHUP" / "SEARCHDOWN", you can choose a subset based on the convenience for users) to a prompt including corresponding ACTION names. The ACTION name is decided by you, but it needs to be consistent with the one in ModuleInfo().
        self.functions = {"SCROLLDOWN": "#scroll down the page: \nSCROLL-DOWN-ARXIV<!|session: str|!>"}
        return
    
    #This is a standard interface for ext-module that must be implemented. It allows users to dynamically load and use modules at runtime. 
    def ModuleInfo(self):
        #The ACTIONS dictionary contains a series of methods to be registered with the client. The key of this dictionary is the name of the ACTION(in other words, method).
        #Under the "func" key is the name of the member function that implements this action.
        #"prompt" provides a description of the functionality associated with this ACTION, which will appear at the end of each paragraph returned to the user, indicating the available ACTIONS (e.g., prompting the user to use SCROLL-DOWN-ARXIV to scroll through the remaining content at the end of the text).
        #The "type" field contains two choices: "primary" or "supportive". The former represents the ACTION corresponding to the main functionality, while the latter is for auxiliary functions, such as scroll down. The key difference between the two is that the "supportive" type of ACTION will appear in the prompt at the end of the text returned by the "primary" type, prompting the user to further perform certain operations (e.g., scroll down).
        return {"NAME": "arxiv", "ACTIONS": {"ARXIV": {"func": "ArxivSearch", "prompt": "Use arxiv to search academic literatures.", "type": "primary"},
                                             "SCROLL-DOWN-ARXIV": {"func": "ScrollDown", "prompt": "Scroll down the results.", "type": "supportive"}}}
    
    def GetSessionID(self) -> str:
        id = f"session-{str(random.randint(0,99999999))}"
        while id in self.sessions:
            id = f"session-{str(random.randint(0,99999999))}"
        return id
    
    def ArxivSearch(self, keywords: str) -> str:
        try:
            results = list(arxiv.Search(query=keywords, max_results=40).results())
            ret = str(results) if len(results) > 0 else "No search results were found. Please check if you used overly complex keywords or unsupported search syntax. Note that relaxing your search terms is an effective strategy when no valid search results are returned."
        except Exception as e:
            print("arxiv excetption: ", e)
            #Regardless of whether the result is obtained or an error occurs, it is recommended to return the obtained information to the user in the form of a string so that the user can know the details.
            ret = f"arxiv excetption: {str(e)}"
        session = self.GetSessionID()
        self.sessions[session] = AScrollablePage(functions=self.functions)
        #"TOP" means to set the currently visible page to the top of the results. You can also use "BOTTOM" to set the currently visible page to the bottom of the results. The latter is usually more commonly used when outputting results of program execution.
        self.sessions[session].LoadPage(str(ret), "TOP")
        #The __call__() method of AScrollablePage returns the text within the currently visible page range.
        return self.sessions[session]() + "\n\n" + f'Session name: "{session}"\n'

    def ScrollDown(self, session: str) -> str:
        return self.sessions[session].ScrollDown() + "\n\n" + f'Session name: "{session}"\n'
    
def main():
    import argparse
    parser = argparse.ArgumentParser()
    #Try to avoid using configuration files and instead utilize startup args to pass configurations. You can design startup args as you like.
    parser.add_argument('--addr',type=str, help="The address where the service runs on.")
    args = parser.parse_args()
    #makeServer() is used to start the module as an RPC service. objArgs are the parameters passed to AArxiv(...) when creating the AArxiv object, and since there are no such parameters here, an empty dictionary is passed. The methods listed in the list are the methods open to clients. Please choose a port number between 59050 and 59200.
    makeServer(AArxiv, dict(), args.addr, ["ModuleInfo", "ArxivSearch", "ScrollDown"]).Run()

if __name__ == '__main__':
    main()