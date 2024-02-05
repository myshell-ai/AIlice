import base64

class AImage():
    def __init__(self, format: str, data: bytes):
        self.format = format
        self.data = data
        return
    
    def __str__(self) -> str:
        return f"AImage object in {self.format} format."
    
    def ToJson(self):
        return {'format': self.format, 'data': base64.b64encode(self.data).decode('utf-8')}
    
    def Format(self) -> str:
        return self.format
    
    def Data(self) -> bytes:
        return self.data

typeMap = {AImage: "image"}
