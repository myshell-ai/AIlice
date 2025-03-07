import os
import random
import difflib
import traceback
from urllib.parse import urljoin
from selenium import webdriver
from bs4 import BeautifulSoup, Comment
import selenium
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from ailice.modules.AScrollablePage import AScrollablePage


class AWebBrowser(AScrollablePage):
    def __init__(self, functions: dict[str, str]):
        super(AWebBrowser, self).__init__(functions=functions)
        self.inited = False
        self.driver = None
        self.urls = {}
        self.prompt = '''
The text with links are enclosed in square brackets to highlight it. If you need to open the page linked to a certain text, please call GET-LINK<!|text: str, session: str|!> function to get the url, and then call BROWSE<!|url: str, session: str|!>. Please note that the text parameter of GET-LINK must exactly match the content in the square brackets (excluding the square brackets themselves).
The forms on the webpage have been listed in text format, and you can use the EXECUTE-JS<!|js_code: str, session: str|!> function to operate the form, such as entering text, clicking buttons, etc. Use triple quotes on your code. Example: 
!EXECUTE-JS<!|"""
document.querySelector('form.mini-search input[name="query"]').value = "hello world";
document.querySelector('form.mini-search').submit();
""", "arxiv_session"|!>
'''
        return
    
    def Init(self):
        if self.inited:
            return True, ""
        try:
            self.options = webdriver.ChromeOptions()
            self.options.add_argument('--headless')
            if os.path.exists('/.dockerenv'):
                self.options.add_argument('--no-sandbox')
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
        WebDriverWait(self.driver, 30).until(
            lambda d: d.execute_script("return document.readyState == 'complete'")
        )

        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        body = soup.find('body')
        self.LoadPage(self.ProcessNode(body), "TOP")
        return self() + self.prompt
    
    def GetFullText(self) -> str:
        return self.txt if (self.txt != None) else ""
    
    def GetLink(self, text: str) -> str:
        if text in self.urls:
            return self.urls[text]
        else:
            prompt = "Please note that the text you use to query the URL should be the part enclosed in square brackets (excluding the square brackets themselves), otherwise the search will not yield results."
            similars = '\n'.join(['[' + key + '](' + self.urls[key] + ')' for key in difflib.get_close_matches(text, self.urls, n=3)])
            if "" == similars:
                return "No url found on specified text. \n" + prompt
            else:
                return f"No exact match found, the most similar URLs are as follows:\n {similars} \n{prompt}"
    
    def ScrollDown(self) -> str:
        return super(AWebBrowser, self).ScrollDown() + self.prompt
    
    def ScrollUp(self) -> str:
        return super(AWebBrowser, self).ScrollUp() + self.prompt

    def SearchDown(self, query: str) -> str:
        return super(AWebBrowser, self).SearchDown(query) + self.prompt
    
    def SearchUp(self, query: str) -> str:
        return super(AWebBrowser, self).SearchUp(query) + self.prompt
    
    def ExecuteJS(self, js_code: dict):
        try:
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            result = self.driver.execute_script(js_code)
            
            WebDriverWait(self.driver, 30).until(
                lambda d: d.execute_script("return document.readyState == 'complete'")
            )
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            body = soup.find('body')
            self.LoadPage(self.ProcessNode(body), "TOP")
            result = "JavaScript executed successfully." if result is None else result
            return f"JS execution returned: {result} \n\nThe current page content is as follows:\n\n{self() + self.prompt}"
        except Exception as e:
            return f"Error executing JavaScript: {str(e)}"
    
    def EnsureUnique(self, txt: str) -> str:
        ret = txt
        while ret in self.urls:
            ret = txt + "   |" + str(random.randint(0, 10000000))
        return ret
    
    def IsBase64Image(self, string):
        if string.startswith('data:image'):
            if ';base64,' not in string:
                return False
            string = string.split(';base64,')[1]
        
        try:
            valid_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=')
            return all(c in valid_chars for c in string)
        except Exception:
            return False
    
    def ProcessNode(self, node, strip=True) -> str:
        ret = ''
        if node is None:
            return ''
        if node.name is None:  # This is a text node or a comment node
            if isinstance(node, Comment):
                # Handle comment nodes
                return ""
            else:
                # Handle text nodes
                return (node.string.strip() if strip else node.string) if node.string else ''
        elif node.name == 'form':
            return f"\n\n```\n{self.ProcessForm(node)}\n```\n\n"
        elif node.name == 'li':
            li = ''
            for child in node.children:
                li += self.ProcessNode(child)
            ret = f"- {li}\n"
        elif node.name == 'p':
            ret += "\n\n"
            for child in node.children:
                ret += self.ProcessNode(child)
        elif node.name == 'pre':
            for child in node.children:
                ret += self.ProcessNode(child, strip=False)
        elif node.name == 'code':
            ret = f"\n\n```\n{''.join([self.ProcessNode(child, strip=False) for child in node.children])}\n```\n\n"
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
                href = urljoin(self.driver.current_url, node.get('href', ''))
                textUni = self.EnsureUnique(text)
                self.urls[textUni] = href
                ret = f"[{textUni}]"
            else:
                ret = text
        elif node.name == 'img':
            src = node.get('src', '')
            alt = node.get('alt', '').strip() if strip else node.get('alt', '')
            if ('' != src):
                textUni = self.EnsureUnique(alt)
                url = urljoin(self.driver.current_url, src)
                if not self.IsBase64Image(url):
                    self.urls[textUni] = url
                    ret = f"\n![{textUni}]({url})\n"
            else:
                ret = alt
        elif node.name == 'video':
            videoURL = None
            if node.has_attr('src'):
                videoURL = node.get('src', '')
            else:
                for source in node.find_all('source'):
                    videoURL = source.get('src', '')
                    if videoURL:
                        break
            if videoURL:
                ret = f"\n\n[Video]({urljoin(self.driver.current_url, videoURL)})\n\n"
        elif node.name in ['ul', 'ol']:
            ret += "\n\n"
            for child in node.children:
                ret += self.ProcessNode(child)
            ret += "\n\n"
        elif node.name in ['script', 'style', 'noscript']:
            ret = ""
        elif node.name in ['iframe']:
            try:
                iframeElement = WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, f'''iframe[src="{node.get('src')}"]'''))
                )
            except selenium.common.exceptions.TimeoutException as e:
                return ret
            
            self.driver.switch_to.frame(iframeElement)
            iframeContent = self.driver.page_source
            self.driver.switch_to.parent_frame()
            
            soup = BeautifulSoup(iframeContent, 'html.parser')
            body = soup.find('body')
            ret += self.ProcessNode(body)
        else:
            for child in node.children:
                ret += self.ProcessNode(child)
        return ret

    def ProcessForm(self, form_node):
        form_info = []
        form_info.append(f"Form:")
        form_info.append(f"- Action: {form_node.get('action', '')}")
        form_info.append(f"- Method: {form_node.get('method', 'GET')}")
        if form_node.get('name'):
            form_info.append(f"- Name: {form_node['name']}")
        if form_node.get('id'):
            form_info.append(f"- ID: {form_node['id']}")
        
        form_info.append("\nFields:")
        for i, field in enumerate(form_node.find_all(['input', 'select', 'textarea', 'button']), 1):
            form_info.append(f"{i}. {field.name.capitalize()}:")
            for attr in ['type', 'name', 'id', 'placeholder', 'required']:
                if field.get(attr):
                    form_info.append(f"   - {attr.capitalize()}: {field[attr]}")
            
            if field.name == 'select':
                form_info.append("   - Options:")
                for option in field.find_all('option'):
                    form_info.append(f"     * Value: {option.get('value', '')}, Text: {option.text.strip()}")
            
            if field.name == 'button' and field.text:
                form_info.append(f"   - Text: {field.text.strip()}")

        return "\n".join(form_info)