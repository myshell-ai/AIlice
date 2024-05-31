import importlib.util
import io

requirements = [x for x in ["pyautogui", "easyocr", "numpy"] if (None == importlib.util.find_spec(x))]
if 0 == len(requirements):
    import easyocr
    import pyautogui
    import numpy

from PIL import Image, ImageGrab
from ailice.common.lightRPC import makeServer
from ailice.common.ADataType import AImage

class AComputer():
    def __init__(self):
        if 0 == len(requirements):
            self.clicks = {"click": pyautogui.click, "double-click": pyautogui.doubleClick, "right-click": pyautogui.rightClick, "middle": pyautogui.middleClick}
            self.reader = easyocr.Reader(['en'])
        return
    
    def ModuleInfo(self):
        return {"NAME": "files", "ACTIONS": {"SCREENSHOT": {"func": "ScreenShot", "prompt": "Take a screenshot of the current screen.", "type": "primary"},
                                             "LOCATEANDCLICK": {"func": "LocateAndClick", "prompt": "Locate the control containing a piece of text on the screenshot and click on it. clickType is a string, and its value can only be one of 'click', 'double-click', 'right-click' or 'middle'.", "type": "primary"},
                                             "LOCATEANDSCROLL": {"func": "LocateAndScroll", "prompt": "Move to the position marked by the text and scroll the mouse wheel.", "type": "primary"},
                                             "TYPEWRITE": {"func": "TypeWrite", "prompt": "Simulate keyboard input for the string. Please ensure that the focus has been moved to the location where input is expected.", "type": "primary"},
                                             "READ-IMAGE": {"func": "ReadImage", "prompt": "Read the content of an image file into a variable.", "type": "primary"},
                                             "WRITE-IMAGE": {"func": "WriteImage", "prompt": "Write a variable of image type into a file.", "type": "primary"}}}
    
    def Locate(self, txt: str):
        image = ImageGrab.grab()
        results = self.reader.readtext(numpy.array(image.convert("L")), slope_ths=0.0, ycenter_ths=0.0, width_ths=0.0)
        for detection in results:
            bbox = detection[0]
            text = detection[1]
            if txt in text:
                x, y = int((bbox[0][0]+bbox[2][0])*0.5), int((bbox[0][1]+bbox[2][1])*0.5)
                return x, y, text
        return None
    
    def ScreenShot(self) -> AImage:
        imageByte = io.BytesIO()
        ImageGrab.grab().save(imageByte, format="JPEG")
        return AImage(data=imageByte.getvalue())
    
    def LocateAndClick(self, txt: str, clickType: str) -> str:
        if 0 != len(requirements):
            return f"python package(s) {[x for x in requirements]} not found. Please install it before using this feature."
        
        if clickType not in self.clicks:
            return f"LOCATEANDCLICK ERROR. clickType: {clickType} can only be one of 'click', 'double-click', 'right-click' or 'middle'."
        
        ret = self.Locate(txt)
        if None != ret:
            x, y, text = ret
            pyautogui.moveTo(x, y, duration=0.5)
            self.clicks[clickType]()
            return f"'''{text}''' at {x},{y} is clicked."
        else:
            return f"'''{txt}''' not found. It may be because the text has been segmented into different boxes by the OCR software. Please try a shorter and distinctive substring."

    def LocateAndScroll(self, txt: str, clicks: float) -> str:
        if 0 != len(requirements):
            return f"python package(s) {[x for x in requirements]} not found. Please install it before using this feature."
        
        ret = self.Locate(txt)
        if None != ret:
            x, y, text = ret
            pyautogui.moveTo(x, y, duration=0.5)
            pyautogui.scroll(clicks)
            return f"The mouse wheel has scrolled {clicks} times."
        else:
            return f"'''{txt}''' not found. It may be because the text has been segmented into different boxes by the OCR software. Please try a shorter and distinctive substring."
    
    def TypeWrite(self, txt: str) -> str:
        if 0 != len(requirements):
            return f"python package(s) {[x for x in requirements]} not found. Please install it before using this feature."
        
        pyautogui.typewrite(txt)
        return f"'''{txt}''' the string has already been typed."
    
    def ReadImage(self, path: str) -> AImage:
        try:
            image = Image.open(path)
            imageByte = io.BytesIO()
            image.save(imageByte, format='JPEG')
            return AImage(data=imageByte.getvalue())
        except Exception as e:
            print("ReadImage() excetption: ", e)
        return AImage(data=None)
    
    def WriteImage(self, image: AImage, path: str):
        try:
            Image.open(io.BytesIO(image.data)).save(path)
        except Exception as e:
            print("WriteImage() excetption: ", e)
        return

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--addr',type=str, help="The address where the service runs on.")
    args = parser.parse_args()
    makeServer(AComputer, dict(), args.addr, ["ModuleInfo", "ScreenShot", "LocateAndClick", "LocateAndScroll", "TypeWrite", "ReadImage", "WriteImage"]).Run()

if __name__ == '__main__':
    main()