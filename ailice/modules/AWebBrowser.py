import random
import subprocess
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.common.by import By

from ailice.modules.AScrollablePage import AScrollablePage


class AWebBrowser(AScrollablePage):
    def __init__(self):
        super(AWebBrowser, self).__init__({"SCROLLDOWN": "SCROLLDOWN", "SEARCHDOWN": "SEARCHDOWN", "SEARCHUP": "SEARCHUP"})
        self.inited = False
        self.driver = None
        self.baseURL = None
        self.urls = {}
        self.prompt = "\nThe text with links are enclosed in square brackets to highlight it. If you need to get the url on a certain text, please use the GETLINK<!|text: str|!> function. Please note that the text must exactly match the content in the square brackets."
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
        root = self.driver.find_element(By.TAG_NAME, "html")
        self.LoadPage(self.TraverseDOM(root), "TOP")
        return self() + self.prompt
    
    def GetFullText(self, url: str) -> str:
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
        tag_name = node.tag_name.lower()
        text = self.driver.execute_script("""
        var parent = arguments[0];
        var child = parent.firstChild;
        var texts = [];
        while (child) {
            if (child.nodeType === Node.TEXT_NODE) {
                texts.push(child.nodeValue);
            }
            child = child.nextSibling;
        }
        return texts.join('').trim();
        """, node)
        attributes = self.driver.execute_script(
            """
            var items = {}; 
            for (index = 0; index < arguments[0].attributes.length; ++index) { 
                items[arguments[0].attributes[index].name] = arguments[0].attributes[index].value 
            }; 
            return items;
            """, node)
        
        if tag_name in ['p', 'li', 'span', 'div']:
            return text
        elif tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            level = int(tag_name[1])
            return '\n\n' + '#' * level + ' ' + text + "\n"
        elif tag_name == 'a':
            href = attributes.get('href', '')
            if ('' != text) and ('' != href):
                href = urljoin(self.baseURL, attributes.get('href', ''))
                textUni = self.EnsureUnique(text)
                self.urls[textUni] = href
                return f"[{textUni}]"
            else:
                return text
        elif tag_name == 'img':
            src = attributes.get('src', '')
            alt = attributes.get('alt', '')
            if ('' != src):
                return f"{alt}: <AImageLocation|'{urljoin(self.baseURL, src)}'|AImageLocation>"
            else:
                return alt
        elif tag_name == 'ul':
            return text
        elif tag_name == 'ol':
            return text
        elif tag_name in ['script', 'style']:
            return ""
        else:
            return text

    def TraverseDOM(self, node) -> str:
        ret = self.ProcessNode(node)
        children = node.find_elements(By.XPATH, "./*")
        for child in children:
            ret += self.TraverseDOM(child)
        return ret