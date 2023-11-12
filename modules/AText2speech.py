from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan
from datasets import load_dataset
import torch
import sounddevice as sd

from espnet2.bin.tts_inference import Text2Speech

from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan


from fairseq.checkpoint_utils import load_model_ensemble_and_task_from_hf_hub
from fairseq.models.text_to_speech.hub_interface import TTSHubInterface


class T2S_LJS():
    def __init__(self):
        self.model = Text2Speech.from_pretrained("espnet/kan-bayashi_ljspeech_vits")
        return
    
    def To(self, device: str):
        self.model = self.model.to(device)
        return
    
    def __call__(self, txt):
        return self.model(txt)['wav'].numpy(),22000
    

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

class T2S_Transformer():
    def __init__(self):
        self.device = "cuda"
        self.model, self.cfg, self.task = load_model_ensemble_and_task_from_hf_hub(
            "facebook/tts_transformer-zh-cv7_css10",
            arg_overrides={"vocoder": "hifigan", "fp16": False}
        )
        TTSHubInterface.update_cfg_with_data_cfg(self.cfg, self.task.data_cfg)
        self.generator = self.task.build_generator(self.model, self.cfg)
        self.model = self.model[0].to(self.device)
        return
    
    def To(self, device: str):
        self.model = self.model.to(device)
        self.device = device
        return
    
    def __call__(self, txt):
        sample = TTSHubInterface.get_model_input(self.task, txt)
        sample["net_input"]["src_tokens"] = sample["net_input"]["src_tokens"].to(self.device)
        sample["net_input"]["src_lengths"] = sample["net_input"]["src_lengths"].to(self.device)
        sample["speaker"] = sample["speaker"].to(self.device)
        wav, rate = TTSHubInterface.get_prediction(self.task, self.model, self.generator, sample)
        return wav.cpu().numpy(),rate

def play(audio, samplerate):
    sd.play(audio, samplerate)
    sd.wait()