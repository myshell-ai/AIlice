import arxiv
import random
import threading
import json

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
        self.lock = threading.Lock()
        return
    
    #This is a standard interface for ext-module that must be implemented. It allows users to dynamically load and use modules at runtime. 
    def ModuleInfo(self):
        #The ACTIONS dictionary contains a series of methods to be registered with the client. The key of this dictionary is the name of the ACTION(in other words, method).
        #Under the "func" key is the name of the member function that implements this action.
        #"prompt" provides a description of the functionality associated with this ACTION, which will appear at the end of each paragraph returned to the user, indicating the available ACTIONS (e.g., prompting the user to use SCROLL-DOWN-ARXIV to scroll through the remaining content at the end of the text).
        #The "type" field contains two choices: "primary" or "supportive". The former represents the ACTION corresponding to the main functionality, while the latter is for auxiliary functions, such as scroll down. The key difference between the two is that the "supportive" type of ACTION will appear in the prompt at the end of the text returned by the "primary" type, prompting the user to further perform certain operations (e.g., scroll down).
        return {"NAME": "arxiv",
                "ACTIONS": {
                    "ARXIV": {
                        "func": "ArxivSearch",
                        "prompt": '''Search arXiv for academic papers.
Examples:
ARXIV<!|query="transformer architecture", options='{"max_results": 5, "sort_by": "submittedDate"}'|!>
ARXIV<!|query="quantum computing", options='{}'|!>
ARXIV<!|query="hep-ph", options='{"search_by": "cat", "sort_by": "submittedDate", "sort_order": "descending", "max_results": 5, "start_index": 0}'|!>

Parameters:
- query (str): The search query.
- options (str): A JSON string with search parameters. Pass '{}' to use all default values.
  - search_by (optional, str): Field to search in. Default: 'all'. Supported fields:
    - 'ti': Title
    - 'au': Author
    - 'abs': Abstract
    - 'co': Comment
    - 'jr': Journal Reference
    - 'cat': Subject Category
    - 'rn': Report Number
    - 'id': Id
    - 'all': All of the above
  - sort_by (optional, str): Sort criterion. Default: 'relevance'. Options: 'relevance', 'lastUpdatedDate', 'submittedDate'.
  - sort_order (optional, str): Sort order. Default: 'descending'. Options: 'ascending', 'descending'.
  - max_results (optional, int): Number of results to return. Default: 10.
  - start_index (optional, int): Start index for pagination. Default: 0.''',
                        "type": "primary"
                    },
                    "SCROLL-DOWN-ARXIV": {"func": "ScrollDown", "prompt": "Scroll down the results.", "type": "supportive"}
                }}
    
    def GetSessionID(self) -> str:
        with self.lock:
            id = f"session-{str(random.randint(0,99999999))}"
            while id in self.sessions:
                id = f"session-{str(random.randint(0,99999999))}"
            return id

    def ParseEntry(self, entry: arxiv.Result) -> dict:
        return {
            'arxiv_id': entry.entry_id.split('/')[-1],
            'title': entry.title,
            'authors': [author.name for author in entry.authors],
            'summary': entry.summary.replace('\n', ' '),
            'published_date': entry.published.isoformat(),
            'pdf_url': entry.pdf_url
        }

    def FormatResults(self, results: list, start_index: int) -> str:
        if not results:
            return "No search results were found. Please check if you used overly complex keywords or unsupported search syntax. Note that relaxing your search terms is an effective strategy when no valid search results are returned."
        
        return "\n\n---\n\n".join(
            (
                f"Result {start_index + i + 1}:\n"
                f"  ID: {r['arxiv_id']}\n"
                f"  Title: {r['title']}\n"
                f"  Authors: {', '.join(r['authors'])}\n"
                f"  Summary: {r['summary']}\n"
                f"  Published: {r['published_date']}\n"
                f"  PDF URL: {r['pdf_url']}"
            )
            for i, r in enumerate(results)
        )

    def ArxivSearch(self, query: str, options: str) -> str:
        try:
            # Parse options from JSON string, with error handling
            try:
                opts = json.loads(options) if options else {}
            except json.JSONDecodeError:
                return "Error: Invalid JSON format in options parameter."

            # Set parameters with natural defaults
            search_by = opts.get('search_by', 'all')
            sort_by = opts.get('sort_by', 'relevance')
            sort_order = opts.get('sort_order', 'descending')
            max_results = opts.get('max_results', 10)
            start_index = opts.get('start_index', 0)

            full_query = f"{search_by}:{query}" if search_by not in ['all', ''] else query

            
            sort_criterion = {"relevance": arxiv.SortCriterion.Relevance,
                              "lastUpdatedDate": arxiv.SortCriterion.LastUpdatedDate,
                              "submittedDate": arxiv.SortCriterion.SubmittedDate}[sort_by]
            sort_order_enum = {"ascending": arxiv.SortOrder.Ascending,
                               "descending": arxiv.SortOrder.Descending}[sort_order]

            # The arxiv library's search takes max_results as the total number of results to fetch.
            # To implement pagination, we fetch all results up to the desired end point.
            total_to_fetch = start_index + max_results
            search = arxiv.Search(
                query=full_query,
                max_results=total_to_fetch,
                sort_by=sort_criterion,
                sort_order=sort_order_enum
            )
            
            # Slicing the generator to get the desired page of results.
            all_results = list(search.results())
            paginated_results = all_results[start_index:]

            parsed_results = [self.ParseEntry(r) for r in paginated_results]
            ret = self.FormatResults(parsed_results, start_index)

        except Exception as e:
            #Regardless of whether the result is obtained or an error occurs, it is recommended to return the obtained information to the user in the form of a string so that the user can know the details.
            ret = f"arxiv exception: {str(e)}"

        session = self.GetSessionID()
        content = AScrollablePage(functions=self.functions)
        #"TOP" means to set the currently visible page to the top of the results. You can also use "BOTTOM" to set the currently visible page to the bottom of the results. The latter is usually more commonly used when outputting results of program execution.
        content.LoadPage(str(ret), "TOP")
        with self.lock:
            self.sessions[session] = content
        #The __call__() method of AScrollablePage returns the text within the currently visible page range.
        return content() + "\n\n" + f'Session name: "{session}"\n'

    def ScrollDown(self, session: str) -> str:
        with self.lock:
            if session not in self.sessions:
                return "Invalid session ID."
            return self.sessions[session].ScrollDown() + "\n\n" + f'Session name: "{session}"\n'

def main():
    import argparse
    parser = argparse.ArgumentParser()
    #Try to avoid using configuration files and instead utilize startup args to pass configurations. You can design startup args as you like.
    parser.add_argument('--addr',type=str, help="The address where the service runs on.")
    args = parser.parse_args()
    #makeServer() is used to start the module as an RPC service. objArgs are the parameters passed to AArxiv(...) when creating the AArxiv object, and since there are no such parameters here, an empty dictionary is passed. The methods listed in the list are the methods open to clients. Please choose a port number between 59050 and 59200.
    #atomicCall is used to mark whether to add service object-level locking. Set it to True unless you specifically designed it to be thread-safe.
    makeServer(AArxiv, dict(), args.addr, ["ModuleInfo", "ArxivSearch", "ScrollDown"], atomicCall=False).Run()

if __name__ == '__main__':
    main()