import os
import requests
from ailice.modules.AScrollablePage import AScrollablePage

class ATextBrowser(AScrollablePage):
    def __init__(self, functions: dict[str, str]):
        super(ATextBrowser, self).__init__(functions=functions)
        return
    
    def Browse(self, url: str) -> str:
        if os.path.exists(url):
            try:
                with open(url, 'r', encoding='utf-8') as f:
                    self.LoadPage(f.read(), "TOP")
                    return self()
            except Exception as e:
                self.LoadPage(f"Exception: {str(e)}.", "BOTTOM")
                return self()
        else:
            response = requests.get(url)
            if response.status_code != 200:
                return f"Error: can not download pdf file. HTTP err code: {response.status_code}"
            if 'text' not in response.headers.get('Content-Type', ''):
                return "The url returned non-text content and cannot be browsed."
            self.LoadPage(response.content, "TOP")
            return self()

    
    def GetFullText(self) -> str:
        return self.txt if (self.txt != None) else ""