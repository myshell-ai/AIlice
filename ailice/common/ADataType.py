import io
import base64
import mimetypes
import requests
from urllib.parse import urlparse
from PIL import Image

def GuessMediaType(pathOrUrl: str) -> str:
    mimetype, _ = mimetypes.guess_type(pathOrUrl)
    if None != mimetype:
        return mimetype
    r=requests.head(pathOrUrl)
    return r.headers.get("content-type")

class AImage():
    def __init__(self, format: str, data: bytes):
        self.format = format
        self.data = data
        return
    
    def __str__(self) -> str:
        return f"< AImage object in {self.format} format. >"
    
    def ToJson(self):
        return {'format': self.format, 'data': base64.b64encode(self.data).decode('utf-8')}
    
    def Convert(self, format: str):
        if format == self.format:
            return self
        imageBytes = io.BytesIO()
        Image.open(io.BytesIO(self.data)).save(imageBytes, format=format)
        return AImage(format=format, data=imageBytes.getvalue())
    
    def Standardize(self):
        return self.Convert(format="JPEG")

class AImageLocation():
    def __init__(self, urlOrPath: str):
        self.urlOrPath = urlOrPath
        return
    
    def IsURL(self, ident: str) -> bool:
        return urlparse(ident).scheme != ''
    
    def GetImage(self, ident: str) -> Image:
        if self.IsURL(ident):
            response = requests.get(ident)
            imageBytes = io.BytesIO(response.content)
            return Image.open(imageBytes)
        else:
            return Image.open(ident)

    def Standardize(self):
        image = self.GetImage(self.urlOrPath)
        imageByte = io.BytesIO()
        image.save(imageByte, format='JPEG')
        return AImage(format="JPEG", data=imageByte.getvalue())

typeInfo = {AImage: {"modal": "image", "tag": False},
            AImageLocation: {"modal": "image", "tag": True}}
