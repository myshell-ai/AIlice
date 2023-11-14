from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan
from datasets import load_dataset
import torch



class T2S_T5():
    def __init__(self):
        self.device = "cuda"
        self.processor = SpeechT5Processor.from_pretrained("microsoft/speecht5_tts")
        self.model = SpeechT5ForTextToSpeech.from_pretrained("microsoft/speecht5_tts").to(self.device)
        self.vocoder = SpeechT5HifiGan.from_pretrained("microsoft/speecht5_hifigan").to(self.device)
        return

    def To(self, device: str):
        self.model = self.model.to(device)
        self.vocoder = self.vocoder.to(device)
        self.device = device
        return
    
    def __call__(self, txt):
        inputs = self.processor(text=txt, return_tensors="pt")
        embeddingsDataset = load_dataset("Matthijs/cmu-arctic-xvectors", split="validation")
        speakerEmbeddings = torch.tensor(embeddingsDataset[7306]["xvector"]).unsqueeze(0)

        speech = self.model.generate_speech(inputs["input_ids"].to(self.device), speakerEmbeddings.to(self.device), vocoder=self.vocoder)
        return speech.cpu().numpy(),16000
