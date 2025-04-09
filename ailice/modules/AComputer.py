import os
import importlib.util
import io
import re
import typing
import urllib.parse
import datetime
import mimetypes
import requests

requirements = [x for x in ["pyautogui", "easyocr", "numpy"] if (None == importlib.util.find_spec(x))]
if 0 == len(requirements):
    import easyocr
    import pyautogui
    import numpy

from PIL import Image, ImageGrab
from ailice.common.lightRPC import makeServer
from ailice.common.ADataType import AImage, AImageLocation

class AComputer():
    def __init__(self):
        if 0 == len(requirements):
            self.clicks = {"click": pyautogui.click, "double-click": pyautogui.doubleClick, "right-click": pyautogui.rightClick, "middle": pyautogui.middleClick}
            self.reader = easyocr.Reader(['en'])
        return
    
    def ModuleInfo(self):
        return {"NAME": "computer", "ACTIONS": {"SCREENSHOT": {"func": "ScreenShot", "prompt": "Take a screenshot of the current screen.", "type": "primary"},
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
            return AImageLocation(urlOrPath=path).Standardize()
        except Exception as e:
            print("ReadImage() excetption: ", e)
        return AImage(data=None)
    
    def WriteImage(self, image: AImage, path: str) -> str:
        try:
            Image.open(io.BytesIO(image.data)).save(path)
            return f"The image has been written to {path}."
        except Exception as e:
            print("WriteImage() excetption: ", e)
            return f"WriteImage() excetption: {str(e)}"
        return
    
    def WriteFile(self, data: bytes, path: str) -> str:
        try:
            directory = os.path.dirname(path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            
            with open(path, "wb") as file:
                file.write(data)
            return f"The file has been written to {path}."
        except Exception as e:
            print("WriteFile() excetption: ", e)
            return f"WriteFile() excetption: {str(e)}"
        return

    def Proxy(self, href: str, method: str, headers: dict={}, body: dict={}, params: dict={}) -> typing.Generator:
        if os.path.exists(href):
            filePath = os.path.abspath(href)
            fileSize = os.path.getsize(filePath)
            fileName = os.path.basename(filePath)
            
            contentType, encoding = mimetypes.guess_type(filePath)
            if contentType is None:
                contentType = 'application/octet-stream'
            
            startByte = 0
            endByte = fileSize - 1
            statusCode = 200
            
            if headers and 'Range' in headers:
                rangeHeader = headers['Range']
                rangeMatch = re.match(r'bytes=(\d+)-(\d*)', rangeHeader)
                if rangeMatch:
                    startByte = int(rangeMatch.group(1))
                    if rangeMatch.group(2):
                        endByte = min(int(rangeMatch.group(2)), fileSize - 1)
                    statusCode = 206  # Partial Content
            
            responseHeaders = {
                'Content-Type': contentType,
                'Content-Length': str(endByte - startByte + 1),
                'Accept-Ranges': 'bytes',
                'Content-Disposition': f'inline; filename="{urllib.parse.quote(fileName)}"; filename*=UTF-8\'\'{urllib.parse.quote(fileName)}',
                'Last-Modified': datetime.datetime.fromtimestamp(os.stat(filePath).st_mtime, tz=datetime.timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
            }
            
            if statusCode == 206:
                responseHeaders['Content-Range'] = f'bytes {startByte}-{endByte}/{fileSize}'
            
            responseInfo = {
                'status_code': statusCode,
                'headers': responseHeaders
            }
            
            yield responseInfo
            
            if method.upper() != 'HEAD':
                def content_generator():
                    with open(filePath, 'rb') as file:
                        if startByte > 0:
                            file.seek(startByte)
                        bytesToRead = endByte - startByte + 1
                        bytesRead = 0
                        
                        while bytesRead < bytesToRead:
                            chunkSize = min(262144, bytesToRead - bytesRead)
                            chunk = file.read(chunkSize)
                            if not chunk:
                                break
                            bytesRead += len(chunk)
                            yield chunk
                
                yield from content_generator()
        else:
            req = requests.request(
                method=method,
                url=href,
                headers=headers,
                data=body,
                params=params,
                stream=True
            )
            
            responseInfo = {
                'status_code': req.status_code,
                'headers': dict(req.headers)
            }
            
            yield responseInfo

            if method.upper() != 'HEAD':
                def content_generator():
                    try:
                        for chunk in req.iter_content(chunk_size=262144):
                            if chunk:
                                yield chunk
                    finally:
                        req.close()
                
                yield from content_generator()
    
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--addr',type=str, help="The address where the service runs on.")
    args = parser.parse_args()
    makeServer(AComputer, dict(), args.addr, ["ModuleInfo", "ScreenShot", "LocateAndClick", "LocateAndScroll", "TypeWrite", "ReadImage", "WriteImage", "WriteFile", "Proxy"]).Run()

if __name__ == '__main__':
    main()