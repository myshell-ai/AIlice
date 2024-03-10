import subprocess
import traceback
import html2text
from selenium import webdriver
from ailice.modules.AScrollablePage import AScrollablePage

class AWebBrowser(AScrollablePage):
    def __init__(self):
        super(AWebBrowser, self).__init__({"SCROLLDOWN": "SCROLLDOWN", "SEARCHDOWN": "SEARCHDOWN", "SEARCHUP": "SEARCHUP"})
        self.inited = False
        return
    
    def Init(self):
        if self.inited:
            return True, ""
        try:
            subprocess.run(['google-chrome', '--version'], check=True)
            self.options = webdriver.ChromeOptions()
            self.options.add_argument('--headless')
            self.options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36")
            self.options.add_experimental_option("excludeSwitches", ["enable-automation"])
            self.options.add_argument("--disable-blink-features=AutomationControlled")

            self.driver = webdriver.Chrome(options=self.options)
            self.inited = True
            return True, ""
        except Exception as e:
            return False, f"webdriver init FAILED. It may be caused by chrome not being installed correctly. please install chrome manually, or let AIlice do it for you. Exception details: {str(e)}\n{traceback.format_exc()}"
    
    def OpenWebpage(self, url: str) -> str:
        self.driver.get(url)
        res = self.ExtractTextURLs(self.driver.page_source)
        self.LoadPage(res, "TOP")
        return self()
    
    def ExtractTextURLs(self, html: str) -> str:
        h = html2text.HTML2Text()
        h.ignore_links = False
        return str(h.handle(html))
    
    def Browse(self, url: str) -> str:
        succ, msg = self.Init()
        if not succ:
            return msg
        return self.OpenWebpage(url)
    
    def GetFullText(self, url: str) -> str:
        return self.txt if (self.txt != None) else ""