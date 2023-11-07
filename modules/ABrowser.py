import os
import re
import shutil
import subprocess
import requests

from urllib.parse import urlparse, urlunparse
from urlextract import URLExtract
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import html2text

from common.lightRPC import makeServer

class ABrowser():
    def __init__(self):
        self.options = webdriver.ChromeOptions()
        self.options.add_argument('--headless')
        self.options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36")
        self.options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.options.add_argument("--disable-blink-features=AutomationControlled")

        self.driver = webdriver.Chrome(options=self.options)
        self.prompt = """\n...TO BE CONTINUED.\n\nYou can use the following command to continue browsing the page.\n#Scroll down the current web page and return the text and url on the current screen. You can SCROLLDOWN multiple times until EOF is returned.\nSCROLLDOWN<!||!>"""
        self.sections = []
        self.currentIdx = 0
        return
    
    def Reset(self):
        self.sections = []
        self.currentIdx = 0
        return
    
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
        self.sections = [res[i: i+1024] for i in range(0,len(res),1024)]
        return self.sections[self.currentIdx] + self.prompt if 0 < len(self.sections) else "EOF"
    
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
        
        outDir = f"temp/{fileName}"
        cmd = f"nougat {pdfPath} -o {outDir}"
        result = subprocess.run([cmd], stdout=subprocess.PIPE, text=True, shell=True)

        with open(f"{outDir}/{fileName}.mmd", mode='rt') as txt_file:
            self.sections = self.Split(txt_file.read())
        return self.sections[self.currentIdx] + self.prompt if 0 < len(self.sections) else "EOF"

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
            self.Reset()
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
            return "Browser Exception. please check your url input."

    def ScrollDown(self) -> str:
        try:
            self.currentIdx += 1
            if len(self.sections) <= self.currentIdx:
                return "EOF"
            return self.sections[self.currentIdx] + self.prompt
        except Exception as e:
            print("Exception. e: ", str(e))
            return "Browser Exception. ScrollDown FAILED."
    

browser = ABrowser()
makeServer(browser, "ipc:///tmp/ABrowser.ipc").Run()