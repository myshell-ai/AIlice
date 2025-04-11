import re
import os
import requests
import tempfile
import traceback

from urllib.parse import urlparse
from urlextract import URLExtract

from ailice.common.lightRPC import makeServer
from ailice.modules.AWebBrowser import AWebBrowser
from ailice.modules.APDFBrowser import APDFBrowser
from ailice.modules.ATextBrowser import ATextBrowser
from ailice.modules.AFileBrowser import AFileBrowser

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
        return {"NAME": "browser", "ACTIONS": {"BROWSE": {"func": "Browse", "prompt": "Open any PDFs, web pages in headless mode to retrieve their content. The 'url' parameter can be either a URL or a local path. You need to give the page a name(the session parameter). You can reuse this session to open new url/path.", "type": "primary"},
                                               "BROWSE-EDIT": {"func": "Edit", "prompt": "Browse and edit any text document (including code files with various extensions) in headless mode. You need to give the page a name(the session parameter). You can reuse this session to open new file.", "type": "primary"},
                                               "SCROLL-DOWN-BROWSER": {"func": "ScrollDown", "prompt": "Scroll down the page.", "type": "supportive"},
                                               "SCROLL-UP-BROWSER": {"func": "ScrollUp", "prompt": "Scroll up the page.", "type": "supportive"},
                                               "SEARCH-DOWN-BROWSER": {"func": "SearchDown", "prompt": "Search content downward from the current location.", "type": "supportive"},
                                               "SEARCH-UP-BROWSER": {"func": "SearchUp", "prompt": "Search content upward from the current location.", "type": "supportive"},
                                               "GET-LINK": {"func": "GetLink", "prompt": "Get the url on the specified text fragment. The text needs to be one of those text fragments enclosed by square brackets on the page (excluding the square brackets themselves).", "type": "supportive"},
                                               "EXECUTE-JS": {"func": "ExecuteJS", "prompt": "Execute js code on the current web page, especially suitable for form operations such as entering text, clicking buttons, etc. Use triple quotes on your code.", "type": "supportive"},
                                               "REPLACE": {"func": "Replace", "prompt": "Replace the matching content within the current page. When regexMode==True, you can use regular expressions to represent the pattern and replacement. This function is a simple wrapper for re.sub() in this mode. When regexMode==False, pattern and replacement represent literal strings. Use triple quotes to represent pattern and replacement.", "type": "supportive"},
                                               "REPLACE-ALL": {"func": "ReplaceAll", "prompt": "Replace all matching content in the entire document. When regexMode==True, you can use regular expressions to represent the pattern and replacement. This function is a simple wrapper for re.sub() in this mode. When regexMode==False, pattern and replacement represent literal strings. Use triple quotes to represent pattern and replacement.", "type": "supportive"},
                                               "SAVETO": {"func": "SaveTo", "prompt": "Save the modified content to a file. If the dstPath parameter is an empty string, save it to the original file.", "type": "supportive"},
                                               }}
    
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
        contentType = response.headers.get("content-type")
        return ("pdf" in contentType) if contentType else False
    
    def PathIsPDF(self, path: str) -> bool:
        return (path[-4:] == ".pdf")
    
    def Browse(self, url: str, session: str) -> str:
        try:
            if session in self.sessions:
                self.sessions[session].Destroy()
                self.sessions.pop(session)
            
            url, path = self.GetLocation(url)
            if url is not None:
                if self.URLIsPDF(url):
                    self.sessions[session] = APDFBrowser(self.pdfOutputDir, functions=self.functions)
                    return self.prompt + "\n\n" + self.sessions[session].Browse(url) + "\n\n" + f'Session name: "{session}"\n'
                else:
                    self.sessions[session] = AWebBrowser(functions=self.functions)
                    return self.prompt + "\n\n" + self.sessions[session].Browse(url) + "\n\n" + f'Session name: "{session}"\n'
            elif path is not None:
                if os.path.isdir(path):
                    self.sessions[session] = AFileBrowser(functions=self.functions)
                    return self.prompt + "\n\n" + self.sessions[session].Browse(path) + "\n\n" + f'Session name: "{session}"\n'
                elif self.PathIsPDF(path):
                    self.sessions[session] = APDFBrowser(self.pdfOutputDir, functions=self.functions)
                    return self.prompt + "\n\n" + self.sessions[session].Browse(path) + "\n\n" + f'Session name: "{session}"\n'
                else:
                    self.sessions[session] = ATextBrowser(functions=self.functions)
                    return self.prompt + "\n\n" + self.sessions[session].Browse(path) + "\n\n" + f'Session name: "{session}"\n'
            else:
                return "No URL/Path found in input string. Please check your input. "

        except Exception as e:
            print("EXCEPTION. e: ", str(e))
            return f"Browser Exception. please check your url input. EXCEPTION: {str(e)}\n{traceback.format_exc()}"
    
    def ExecuteJS(self, js_code: str, session: str) -> str:
        return self.sessions[session].ExecuteJS(js_code) if hasattr(self.sessions[session], "ExecuteJS") else "ExecuteJS not supported in current browser."
    
    def Edit(self, path: str, session: str) -> str:
        try:
            if session in self.sessions:
                self.sessions[session].Destroy()
                self.sessions.pop(session)
            
            self.sessions[session] = ATextBrowser(functions=self.functions)
            return self.prompt + "\n\n" + self.sessions[session].Edit(path) + "\n\n" + f'Session name: "{session}"\n'
        except Exception as e:
            print("EXCEPTION. e: ", str(e))
            return f"Browser Exception. please check your path input. EXCEPTION: {str(e)}\n{traceback.format_exc()}"
        return
    
    def GetFullText(self, session: str) -> str:
        return self.sessions[session].GetFullText() if session in self.sessions else f"ERROR: Invalid session name: {session}"

    def ScrollDown(self, session: str) -> str:
        return self.prompt + "\n\n" + self.sessions[session].ScrollDown() + "\n\n" + f'Session name: "{session}"\n'
    
    def ScrollUp(self, session: str) -> str:
        return self.prompt + "\n\n" + self.sessions[session].ScrollUp() + "\n\n" + f'Session name: "{session}"\n'

    def SearchDown(self, query: str, session: str) -> str:
        return self.prompt + "\n\n" + self.sessions[session].SearchDown(query=query) + "\n\n" + f'Session name: "{session}"\n'
    
    def SearchUp(self, query: str, session: str) -> str:
        return self.prompt + "\n\n" + self.sessions[session].SearchUp(query=query) + "\n\n" + f'Session name: "{session}"\n'
    
    def GetLink(self, text: str, session: str) -> str:
        return self.sessions[session].GetLink(text) if hasattr(self.sessions[session], "GetLink") else "GetLink not supported in current browser."
    
    def Replace(self, pattern: str, replacement: str, regexMode: bool, session: str) -> str:
        return self.sessions[session].Replace(pattern, replacement, regexMode) if hasattr(self.sessions[session], "Replace") else "Replace not supported in current browser."
    
    def ReplaceAll(self, pattern: str, replacement: str, regexMode: bool, session: str) -> str:
        return self.sessions[session].ReplaceAll(pattern, replacement, regexMode) if hasattr(self.sessions[session], "ReplaceAll") else "ReplaceAll not supported in current browser."
    
    def SaveTo(self, dstPath: str, session: str) -> str:
        return self.sessions[session].SaveTo(dstPath) if hasattr(self.sessions[session], "SaveTo") else "SaveTo not supported in current browser."

    def Destroy(self):
        for _, session in self.sessions.items():
            destroy = getattr(session, "Destroy", None)
            if callable(destroy):
              destroy()
        self.sessions.clear()
        self.computer = None
        self.scripter = None
        return

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
                   ["ModuleInfo", "Browse", "Edit", "ScrollDown", "ScrollUp", "SearchDown", "SearchUp", "GetFullText", "GetLink", "ExecuteJS", "Replace", "ReplaceAll", "SaveTo", "Destroy"]).Run()

if __name__ == '__main__':
    main()