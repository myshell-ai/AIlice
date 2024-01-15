import os
import re
import shutil
import subprocess
import requests
import tempfile
import traceback

from urllib.parse import urlparse, urlunparse
from urlextract import URLExtract
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import html2text

from ailice.common.lightRPC import makeServer
from ailice.modules.AScrollablePage import AScrollablePage

class ABrowser():
    def __init__(self, pdfOutputDir: str):
        self.inited = False
        self.pdfOutputDir = pdfOutputDir
        return
    
    def Init(self):
        if self.inited:
            return
        try:
            self.options = webdriver.ChromeOptions()
            self.options.add_argument('--headless')
            self.options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36")
            self.options.add_experimental_option("excludeSwitches", ["enable-automation"])
            self.options.add_argument("--disable-blink-features=AutomationControlled")

            self.driver = webdriver.Chrome(options=self.options)
            self.page = AScrollablePage({"SCROLLDOWN": "SCROLLDOWN", "SEARCHDOWN": "SEARCHDOWN", "SEARCHUP": "SEARCHUP"})
            self.inited = True
            return True, ""
        except Exception as e:
            return False, f"webdriver init FAILED. It may be caused by chrome not being installed correctly. please install chrome manually, or let AIlice do it for you. Exception details: {str(e)}\n{traceback.format_exc()}"
    
    def ModuleInfo(self):
        return {"NAME": "browser", "ACTIONS": {"BROWSE": {"sig": "Browse(url:str)->str", "prompt": "Open a webpage/PDF and obtain the visible content."},
                                               "SCROLLDOWN": {"sig": "ScrollDown()->str", "prompt": "Scroll down the page."},
                                               "SEARCHDOWN": {"sig": "SearchDown(query: str)->str", "prompt": "Search content downward from the current location."},
                                               "SEARCHUP": {"sig": "SearchUp(query: str)->str", "prompt": "Search content upward from the current location."}}}
    
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
        parsedURL = urlparse(url)
        if not parsedURL.scheme:
            parsedURL = parsedURL._replace(scheme="https")
        url = urlunparse(parsedURL)
        return url

    def OpenWebpage(self, url: str) -> str:
        self.driver.get(url)
        res = self.ExtractTextURLs(self.driver.page_source)
        self.page.LoadPage(res, "TOP")
        return self.page()
    
    def ExtractTextURLs(self, html: str) -> str:
        h = html2text.HTML2Text()
        h.ignore_links = False
        return str(h.handle(html))

    def SplitGen(self, txt_list):
        for txt in txt_list:
            while txt:
                yield txt[:1024]
                txt = txt[1024:]
        return
    
    def Split(self, txt: str) -> list[str]:
        sep = '\n\n'
        paragraphs = txt.split(sep)
        
        ret = []
        current_p = ""
        for s in self.SplitGen(paragraphs):
            if (len(current_p + sep + s) <= 1026):
                current_p += (sep + s)
            else:
                ret.append(current_p)
                current_p = s
        return ret
    
    def OpenPDF(self, loc: str) -> str:
        os.makedirs("temp/", exist_ok=True)
        fullName = loc.split('/')[-1]
        fileName = fullName[:fullName.rfind('.')]
        pdfPath = f"temp/{fullName}"
        if os.path.exists(loc):
            shutil.copy(loc, "./")
        else:
            response = requests.get(loc)
            if response.status_code == 200:
                with open(pdfPath, "wb") as pdf_file:
                    pdf_file.write(response.content)
            else:
                print("can not download pdf file. HTTP err code:", response.status_code)
        
        outDir = f"{self.pdfOutputDir}/{fileName}"
        cmd = f"nougat {pdfPath} -o {outDir}"
        result = subprocess.run([cmd], stdout=subprocess.PIPE, text=True, shell=True)

        with open(f"{outDir}/{fileName}.mmd", mode='rt') as txt_file:
            self.page.LoadPage(txt_file.read(), "TOP")
        return self.page()

    def URLIsPDF(self, url: str) -> bool:
        response = requests.get(url, allow_redirects=True)
        if response.status_code == 200:
            finalURL = response.url
            return finalURL.endswith('.pdf')
        else:
            return False
    
    def PathIsPDF(self, path: str) -> bool:
        return (path[-4:] == ".pdf")
    
    def SearchDown(self, query: str) -> str:
        return self.page() if self.page.SearchDown(query=query) else "NOT FOUND."
    
    def SearchUp(self, query: str) -> str:
        return self.page() if self.page.SearchUp(query=query) else "NOT FOUND."
    
    def Browse(self, url: str) -> str:
        succ, msg = self.Init()
        if not succ:
            return msg
        
        try:
            url, path = self.GetLocation(url)
            if url is not None:
                if self.URLIsPDF(url):
                    return self.OpenPDF(url)
                else:
                    return self.OpenWebpage(url)
            elif path is not None:
                if self.PathIsPDF(path):
                    return self.OpenPDF(path)
                else:
                    return "File format not supported. Please check your input."
            else:
                return "No URL/Path found in input string. Please check your input. "

        except Exception as e:
            print("EXCEPTION. e: ", str(e))
            return f"Browser Exception. please check your url input. EXCEPTION: {str(e)}"

    def ScrollDown(self) -> str:
        self.page.ScrollDown()
        return self.page()
    
    def GetFullText(self, url: str) -> str:
        return self.page.txt if self.page.txt is not None else ""

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--pdfOutputDir',type=str,default="", help="You can set it as a directory to store the OCR results of PDF files to avoid repeated OCR computation.")
    args = parser.parse_args()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        makeServer(lambda: ABrowser(pdfOutputDir=args.pdfOutputDir if "" != args.pdfOutputDir.strip() else tmpdir),
                   "ipc:///tmp/ABrowser.ipc",
                   ["ModuleInfo", "Browse", "ScrollDown", "SearchDown", "SearchUp", "GetFullText"]).Run()