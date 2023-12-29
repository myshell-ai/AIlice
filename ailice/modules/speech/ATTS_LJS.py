from espnet2.bin.tts_inference import Text2Speech

class T2S_LJS():
    def __init__(self):
        self.model = Text2Speech.from_pretrained("espnet/kan-bayashi_ljspeech_vits")
        return
    
    def To(self, device: str):
        self.model = self.model.to(device)
        return
    
    def __call__(self, txt):
        return self.model(txt)['wav'].numpy(),22000
    