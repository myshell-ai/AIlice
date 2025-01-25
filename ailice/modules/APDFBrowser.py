import os
import re
import shutil
import requests
import subprocess
import importlib.util
from pathlib import Path

OCROption = "None"
if (None != importlib.util.find_spec("marker")):
    OCROption = "marker"
elif (None != importlib.util.find_spec("pix2text")):
    from pix2text import Pix2Text
    OCROption = "pix2text"

from ailice.modules.AScrollablePage import AScrollablePage

class APDFBrowser(AScrollablePage):
    def __init__(self, pdfOutputDir: str, functions: dict[str, str]):
        super(APDFBrowser, self).__init__(functions=functions)
        self.pdfOutputDir = pdfOutputDir
        if "pix2text" == OCROption:
            self.p2t = Pix2Text.from_config()
        return
    
    def OCRPix2Text(self, pdfPath: str, outDir: str) -> str:
        return self.p2t.recognize_pdf(pdfPath).to_markdown(outDir)

    def OCRMarker(self, pdfPath: str, outDir: str) -> str:
        subprocess.run(["marker_single", f"{pdfPath}", "--output_dir", f"{outDir}", "--output_format", "markerdown"])
        pdfName = Path(pdfPath).stem

        with open(Path(outDir) / pdfName / f"{pdfName}.md", "r") as f:
            ret = f.read()
        ret = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', lambda match: f'![{match.group(1)}]({str(os.path.join(outDir, pdfName, match.group(2)))})', ret)
        with open(Path(outDir) / pdfName / f"{pdfName}.md", "w") as f:
            f.write(ret)
        return ret

    
    def Browse(self, url: str) -> str:
        if "None" == OCROption:
            self.LoadPage(f"python packages marker-pdf or pix2text not found. Please install one of them before using PDF OCR.", "BOTTOM")
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
            
            if "marker" == OCROption:
                result = self.OCRMarker(pdfPath, outDir)
            elif "pix2text" == OCROption:
                result = self.OCRPix2Text(pdfPath, outDir)
            self.LoadPage(result, "TOP")
        except Exception as e:
            self.LoadPage(f"PDF OCR Exception: {str(e)}.", "BOTTOM")
        return self()
    
    def GetFullText(self) -> str:
        return self.txt if (self.txt != None) else ""