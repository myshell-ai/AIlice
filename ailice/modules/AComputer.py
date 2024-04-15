import io
from PIL import Image, ImageGrab
from ailice.common.lightRPC import makeServer
from ailice.common.ADataType import AImage

class AComputer():
    def __init__(self):
        return
    
    def ModuleInfo(self):
        return {"NAME": "files", "ACTIONS": {"SCREENSHOT": {"func": "ScreenShot", "prompt": "Take a screenshot of the current screen.", "type": "primary"},
                                             "READ_IMAGE": {"func": "ReadImage", "prompt": "Read the content of an image file into a variable.", "type": "primary"},
                                             "WRITE_IMAGE": {"func": "WriteImage", "prompt": "Write a variable of image type into a file.", "type": "primary"}}}
    
    def ScreenShot(self) -> AImage:
        imageByte = io.BytesIO()
        ImageGrab.grab().save(imageByte, format="JPEG")
        return AImage(format="JPEG", data=imageByte.getvalue())
    
    def ReadImage(self, path: str) -> AImage:
        try:
            image = Image.open(path)
            imageByte = io.BytesIO()
            image.save(imageByte, format='JPEG')
            return AImage(format="JPEG", data=imageByte.getvalue())
        except Exception as e:
            print("ReadImage() excetption: ", e)
        return AImage(format=None, data=None)
    
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
    makeServer(AComputer, dict(), args.addr, ["ModuleInfo", "ScreenShot", "ReadImage", "WriteImage"]).Run()

if __name__ == '__main__':
    main()