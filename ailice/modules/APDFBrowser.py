import os
import shutil
import subprocess
import requests
from ailice.modules.AScrollablePage import AScrollablePage

class APDFBrowser(AScrollablePage):
    def __init__(self, pdfOutputDir: str):
        super(APDFBrowser, self).__init__({"SCROLLDOWN": "SCROLLDOWN", "SEARCHDOWN": "SEARCHDOWN", "SEARCHUP": "SEARCHUP"})
        self.pdfOutputDir = pdfOutputDir
        return
    
    def Browse(self, url: str) -> str:
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
        
        cmd = f"nougat {pdfPath} -o {outDir}"
        result = subprocess.run([cmd], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True)
        try:    
            with open(f"{outDir}/{fileName}.mmd", mode='rt') as txt_file:
                self.LoadPage(txt_file.read(), "TOP")
        except Exception as e:
            self.LoadPage(f"Exception: {str(e)}. Perhaps it is caused by nougat's failure to do pdf ocr. nougat returned: {str(result)}", "BOTTOM")
        return self()
    
    def GetFullText(self, url: str) -> str:
        return self.txt if (self.txt != None) else ""