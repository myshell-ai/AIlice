import re
import requests
import tempfile
import traceback

from urllib.parse import urlparse
from urlextract import URLExtract

from ailice.common.lightRPC import makeServer
from ailice.modules.AWebBrowser import AWebBrowser
from ailice.modules.APDFBrowser import APDFBrowser
from ailice.modules.ATextBrowser import ATextBrowser

class ABrowser():
    def __init__(self, pdfOutputDir: str):
        self.pdfOutputDir = pdfOutputDir
        self.sessions = {}
        self.functions = {"SCROLLDOWN": "#scroll down the page: \nSCROLL-DOWN-BROWSER<!|session: str|!>",
                          "SCROLLUP": "#scroll up the page: \nSCROLL-UP-BROWSER<!|session: str|!>",
                          "SEARCHDOWN": "#search the content downward and jumps the page to the next matching point(Just like the F3 key normally does): \nSEARCH-DOWN-BROWSER<!|query: str, session: str|!>",
                          "SEARCHUP": "#search the content upward and jumps the page to the next matching point: \nSEARCH-UP-BROWSER<!|query: str, session: str|!>"}
        self.prompt = "The browser is running in headless mode, mouse and keyboard operations are not supported. All operations on the page must be accomplished using the functions listed after the page content."
        return

    def ModuleInfo(self):
        return {"NAME": "browser", "ACTIONS": {"BROWSE": {"func": "Browse", "prompt": "Open a webpage/PDF in headless mode and obtain the content. You need to give the page a name(the session parameter). You can reuse this session to open new webpages.", "type": "primary"},
                                               "SCROLL-DOWN-BROWSER": {"func": "ScrollDown", "prompt": "Scroll down the page.", "type": "supportive"},
                                               "SCROLL-UP-BROWSER": {"func": "ScrollUp", "prompt": "Scroll up the page.", "type": "supportive"},
                                               "SEARCH-DOWN-BROWSER": {"func": "SearchDown", "prompt": "Search content downward from the current location.", "type": "supportive"},
                                               "SEARCH-UP-BROWSER": {"func": "SearchUp", "prompt": "Search content upward from the current location.", "type": "supportive"},
                                               "GET-LINK": {"func": "GetLink", "prompt": "Get the url on the specified text fragment. The text needs to be one of those text fragments enclosed by square brackets on the page (excluding the square brackets themselves).", "type": "supportive"}}}
    
    def ParseURL(self, txt: str) -> str:
        extractor = URLExtract()
        urls = extractor.find_urls(txt)
        if 0 == len(urls):
            print("ParseURL: no url provided. ", txt)
            return None
        else:
            url = urls[0]
        return url
    
    def ParsePath(self, txt: str) -> str:
        pattern = r"^(\/.*|[^\/].*)$"
        matches = re.findall(pattern, txt)
        if not matches:
            print("ParsePath: no path provided. ", txt)
            return None
        else:
            return matches[0].strip()
    
    def GetLocation(self, txt: str) -> tuple[str,str]:
        url = self.ParseURL(txt)
        if url is not None:
            return self.ToHttps(url),None
        
        path = self.ParsePath(txt)
        if path is not None:
            return None,path

        return None,None
    
    def ToHttps(self, url: str) -> str:
        if not urlparse(url).scheme:
            url = "https://" + url
        return url

    def URLIsPDF(self, url: str) -> bool:
        response = requests.head(url, allow_redirects=True)
        return ("pdf" in response.headers.get("content-type"))
    
    def PathIsPDF(self, path: str) -> bool:
        return (path[-4:] == ".pdf")
    
    def Browse(self, url: str, session: str) -> str:
        try:
            url, path = self.GetLocation(url)
            if url is not None:
                if self.URLIsPDF(url):
                    self.sessions[session] = APDFBrowser(self.pdfOutputDir, functions=self.functions)
                    return self.prompt + "\n--------------" + "\n" + self.sessions[session].Browse(url) + "\n\n" + f'Session name: "{session}"\n'
                else:
                    self.sessions[session] = AWebBrowser(functions=self.functions)
                    return self.prompt + "\n--------------" + "\n" + self.sessions[session].Browse(url) + "\n\n" + f'Session name: "{session}"\n'
            elif path is not None:
                if self.PathIsPDF(path):
                    self.sessions[session] = APDFBrowser(self.pdfOutputDir, functions=self.functions)
                    return self.prompt + "\n--------------" + "\n" + self.sessions[session].Browse(path) + "\n\n" + f'Session name: "{session}"\n'
                else:
                    self.sessions[session] = ATextBrowser(functions=self.functions)
                    return self.prompt + "\n--------------" + "\n" + self.sessions[session].Browse(path) + "\n\n" + f'Session name: "{session}"\n'
            else:
                return "No URL/Path found in input string. Please check your input. "

        except Exception as e:
            print("EXCEPTION. e: ", str(e))
            return f"Browser Exception. please check your url input. EXCEPTION: {str(e)}\n{traceback.format_exc()}"
    
    def GetFullText(self, session: str) -> str:
        return self.sessions[session].GetFullText()

    def ScrollDown(self, session: str) -> str:
        return self.prompt + "\n--------------" + "\n" + self.sessions[session].ScrollDown() + "\n\n" + f'Session name: "{session}"\n'
    
    def ScrollUp(self, session: str) -> str:
        return self.prompt + "\n--------------" + "\n" + self.sessions[session].ScrollUp() + "\n\n" + f'Session name: "{session}"\n'

    def SearchDown(self, query: str, session: str) -> str:
        return self.prompt + "\n--------------" + "\n" + self.sessions[session].SearchDown(query=query) + "\n\n" + f'Session name: "{session}"\n'
    
    def SearchUp(self, query: str, session: str) -> str:
        return self.prompt + "\n--------------" + "\n" + self.sessions[session].SearchUp(query=query) + "\n\n" + f'Session name: "{session}"\n'
    
    def GetLink(self, text: str, session: str) -> str:
        return self.sessions[session].GetLink(text) if hasattr(self.sessions[session], "GetLink") else "GetLink not supported in current browser."

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--addr',type=str, help="The address where the service runs on.")
    parser.add_argument('--pdfOutputDir',type=str,default="", help="You can set it as a directory to store the OCR results of PDF files to avoid repeated OCR computation.")
    args = parser.parse_args()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        makeServer(ABrowser,
                   {"pdfOutputDir": (args.pdfOutputDir if "" != args.pdfOutputDir.strip() else tmpdir)},
                   args.addr,
                   ["ModuleInfo", "Browse", "ScrollDown", "ScrollUp", "SearchDown", "SearchUp", "GetFullText", "GetLink"]).Run()

if __name__ == '__main__':
    main()