import re
import requests
import tempfile
import traceback

from urllib.parse import urlparse
from urlextract import URLExtract

from ailice.common.lightRPC import makeServer
from ailice.modules.AWebBrowser import AWebBrowser
from ailice.modules.APDFBrowser import APDFBrowser

class ABrowser():
    def __init__(self, pdfOutputDir: str):
        self.pdfOutputDir = pdfOutputDir
        self.browser = None
        return

    def ModuleInfo(self):
        return {"NAME": "browser", "ACTIONS": {"BROWSE": {"func": "Browse", "prompt": "Open a webpage/PDF and obtain the visible content."},
                                               "SCROLLDOWN": {"func": "ScrollDown", "prompt": "Scroll down the page."},
                                               "SEARCHDOWN": {"func": "SearchDown", "prompt": "Search content downward from the current location."},
                                               "SEARCHUP": {"func": "SearchUp", "prompt": "Search content upward from the current location."},
                                               "GETLINK": {"func": "GetLink", "prompt": "Get the url on the specified text fragment. The text needs to come from the part of the page enclosed by square brackets."}}}
    
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
        response = requests.get(url, allow_redirects=True)
        if response.status_code == 200:
            finalURL = response.url
            return finalURL.endswith('.pdf')
        else:
            return False
    
    def PathIsPDF(self, path: str) -> bool:
        return (path[-4:] == ".pdf")
    
    def Browse(self, url: str) -> str:
        try:
            url, path = self.GetLocation(url)
            if url is not None:
                if self.URLIsPDF(url):
                    self.browser = APDFBrowser(self.pdfOutputDir) if ("APDFBrowser" != type(self.browser).__name__) else self.browser
                    return self.browser.Browse(url)
                else:
                    self.browser = AWebBrowser() if ("AWebBrowser" != type(self.browser).__name__) else self.browser
                    return self.browser.Browse(url)
            elif path is not None:
                if self.PathIsPDF(path):
                    self.browser = APDFBrowser(self.pdfOutputDir) if ("APDFBrowser" != type(self.browser).__name__) else self.browser
                    return self.browser.Browse(path)
                else:
                    return "File format not supported. Please check your input."
            else:
                return "No URL/Path found in input string. Please check your input. "

        except Exception as e:
            print("EXCEPTION. e: ", str(e))
            return f"Browser Exception. please check your url input. EXCEPTION: {str(e)}\n{traceback.format_exc()}"
    
    def GetFullText(self, url: str) -> str:
        return self.browser.GetFullText(url)

    def ScrollDown(self) -> str:
        return self.browser.ScrollDown()
    
    def ScrollUp(self) -> str:
        return self.browser.ScrollUp()

    def SearchDown(self, query: str) -> bool:
        return self.browser.SearchDown(query=query)
    
    def SearchUp(self, query: str) -> bool:
        return self.browser.SearchUp(query=query)
    
    def GetLink(self, text: str) -> str:
        return self.browser.GetLink(text) if hasattr(self.browser, "GetLink") else "GetLink not supported in current browser."

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
                   ["ModuleInfo", "Browse", "ScrollDown", "SearchDown", "SearchUp", "GetFullText", "GetLink"]).Run()

if __name__ == '__main__':
    main()