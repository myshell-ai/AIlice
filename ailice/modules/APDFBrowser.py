import os
import shutil
import requests
import importlib.util

requirements = [x for x in ["pix2text"] if (None == importlib.util.find_spec(x))]
if 0 == len(requirements):
    from pix2text import Pix2Text
from ailice.modules.AScrollablePage import AScrollablePage

class APDFBrowser(AScrollablePage):
    def __init__(self, pdfOutputDir: str, functions: dict[str, str]):
        super(APDFBrowser, self).__init__(functions=functions)
        self.pdfOutputDir = pdfOutputDir
        if 0 == len(requirements):
            self.p2t = Pix2Text.from_config()
        return
    
    def Browse(self, url: str) -> str:
        if 0 != len(requirements):
            self.LoadPage(f"python packages {[x for x in requirements]} not found. Please install it before using PDF OCR.", "BOTTOM")
            return self()
        try:
            fullName = url.split('/')[-1]
            fileName = fullName[:fullName.rfind('.')]
            outDir = f"{self.pdfOutputDir}/{fileName}"
            os.makedirs(outDir, exist_ok=True)
            
            pdfPath = f"{outDir}/{fullName}"
            if os.path.exists(url):
                shutil.copy(url, pdfPath)
            else:
                response = requests.get(url)
                if response.status_code == 200:
                    with open(pdfPath, "wb") as pdf_file:
                        pdf_file.write(response.content)
                else:
                    print("can not download pdf file. HTTP err code:", response.status_code)
            result = self.p2t.recognize_pdf(pdfPath)
            self.LoadPage(result.to_markdown(outDir), "TOP")
        except Exception as e:
            self.LoadPage(f"PDF OCR Exception: {str(e)}.", "BOTTOM")
        return self()
    
    def GetFullText(self) -> str:
        return self.txt if (self.txt != None) else ""