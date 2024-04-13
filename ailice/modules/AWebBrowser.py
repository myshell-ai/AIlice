import random
import subprocess
from urllib.parse import urljoin
from selenium import webdriver
from bs4 import BeautifulSoup, Comment
from ailice.modules.AScrollablePage import AScrollablePage


class AWebBrowser(AScrollablePage):
    def __init__(self, functions: dict[str, str]):
        super(AWebBrowser, self).__init__(functions=functions)
        self.inited = False
        self.driver = None
        self.baseURL = None
        self.urls = {}
        self.prompt = "\nThe text with links are enclosed in square brackets to highlight it. If you need to get the url on a certain text, please use the GET_LINK<!|text: str, session: str|!> function. Please note that the text must exactly match the content in the square brackets."
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
    
    def Browse(self, url: str) -> str:
        succ, msg = self.Init()
        if not succ:
            return msg
        
        self.driver.get(url)
        self.baseURL = url
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        body = soup.find('body')
        self.LoadPage(self.ProcessNode(body), "TOP")
        return self() + self.prompt
    
    def GetFullText(self) -> str:
        return self.txt if (self.txt != None) else ""
    
    def GetLink(self, text: str) -> str:
        return self.urls.get(text, "No url found on specified text.")
    
    def ScrollDown(self) -> str:
        return super(AWebBrowser, self).ScrollDown() + self.prompt
    
    def ScrollUp(self) -> str:
        return super(AWebBrowser, self).ScrollUp() + self.prompt

    def SearchDown(self, query: str) -> bool:
        return super(AWebBrowser, self).SearchDown(query) + self.prompt
    
    def SearchUp(self, query: str) -> bool:
        return super(AWebBrowser, self).SearchUp(query) + self.prompt
    
    def Action(self, action: str, paras: dict):
        return
    
    def EnsureUnique(self, txt: str) -> str:
        ret = txt
        while ret in self.urls:
            ret = txt + "   |" + str(random.randint(0, 10000000))
        return ret
    
    def ProcessNode(self, node) -> str:
        ret = ''
        if node.name is None:  # This is a text node or a comment node
            if isinstance(node, Comment):
                # Handle comment nodes
                return ""
            else:
                # Handle text nodes
                return node.string if node.string else ''
        elif node.name == 'li':
            li = ''
            for child in node.children:
                li += self.ProcessNode(child)
            ret = f"- {li}\n"
        elif node.name == 'p':
            ret += "\n\n"
            for child in node.children:
                ret += self.ProcessNode(child)
        elif node.name == 'code':
            ret = f"\n\n```\n{''.join([self.ProcessNode(child) for child in node.children])}\n```\n\n"
        elif node.name in ['span', 'div']:
            for child in node.children:
                ret += self.ProcessNode(child)
        elif node.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            level = int(node.name[1])
            for child in node.children:
                ret += self.ProcessNode(child)
            ret = '\n\n' + '#' * level + ' ' + ret + "\n"
        elif node.name == 'a':
            href = node.get('href', '')
            text = ""
            for child in node.children:
                text += self.ProcessNode(child)
            if ('' != text) and ('' != href):
                href = urljoin(self.baseURL, node.get('href', ''))
                textUni = self.EnsureUnique(text)
                self.urls[textUni] = href
                ret = f"[{textUni}]"
            else:
                ret = text
        elif node.name == 'img':
            src = node.get('src', '')
            alt = node.get('alt', '')
            if ('' != src):
                ret = f"{alt}: <AImageLocation|'{urljoin(self.baseURL, src)}'|AImageLocation>"
            else:
                ret = alt
        elif node.name in ['ul', 'ol']:
            ret += "\n\n"
            for child in node.children:
                ret += self.ProcessNode(child)
            ret += "\n\n"
        elif node.name in ['script', 'style', 'noscript']:
            ret = ""
        else:
            for child in node.children:
                ret += self.ProcessNode(child)
        return ret