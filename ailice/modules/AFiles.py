import io
from PIL import Image
from ailice.common.lightRPC import makeServer
from ailice.common.ADataType import AImage

class AFiles():
    def __init__(self):
        return
    
    def ModuleInfo(self):
        return {"NAME": "files", "ACTIONS": {"READIMAGE": {"func": "ReadImage", "prompt": "Read the content of an image file into a variable."},
                                             "WRITEIMAGE": {"func": "WriteImage", "prompt": "Write a variable of image type into a file."}}}
    
    def ReadImage(self, path: str) -> AImage:
        try:
            image = Image.open(path)
            imageByte = io.BytesIO()
            image.save(imageByte, format='JPEG')
            return AImage(format="jpg", data=imageByte.getvalue())
        except Exception as e:
            print("ReadImage() excetption: ", e)
        return AImage(format=None, data=None)
    
    def WriteImage(self, image: AImage, path: str):
        try:
            Image.open(io.BytesIO(image.Data())).save(path)
        except Exception as e:
            print("WriteImage() excetption: ", e)
        return

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--addr',type=str, help="The address where the service runs on.")
    args = parser.parse_args()
    makeServer(AFiles, dict(), args.addr, ["ModuleInfo", "ReadImage", "WriteImage"]).Run()

if __name__ == '__main__':
    main()