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
    
    def __call__(self, txt):
        return self.model(txt)['wav'].numpy(),22000
    

class T2S_T5():
    def __init__(self):
        self.processor = SpeechT5Processor.from_pretrained("microsoft/speecht5_tts")
        self.model = SpeechT5ForTextToSpeech.from_pretrained("microsoft/speecht5_tts").cuda()
        self.vocoder = SpeechT5HifiGan.from_pretrained("microsoft/speecht5_hifigan").cuda()
        return

    def __call__(self, txt):
        inputs = self.processor(text=txt, return_tensors="pt")
        embeddingsDataset = load_dataset("Matthijs/cmu-arctic-xvectors", split="validation")
        speakerEmbeddings = torch.tensor(embeddingsDataset[7306]["xvector"]).unsqueeze(0)

        speech = self.model.generate_speech(inputs["input_ids"].cuda(), speakerEmbeddings.cuda(), vocoder=self.vocoder)
        return speech.cpu().numpy(),16000

class T2S_Transformer():
    def __init__(self):
        self.model, self.cfg, self.task = load_model_ensemble_and_task_from_hf_hub(
            "facebook/tts_transformer-zh-cv7_css10",
            arg_overrides={"vocoder": "hifigan", "fp16": False}
        )
        TTSHubInterface.update_cfg_with_data_cfg(self.cfg, self.task.data_cfg)
        self.generator = self.task.build_generator(self.model, self.cfg)
        self.model = self.model[0].cuda()
        return
    
    def __call__(self, txt):
        sample = TTSHubInterface.get_model_input(self.task, txt)
        sample["net_input"]["src_tokens"] = sample["net_input"]["src_tokens"].cuda()
        sample["net_input"]["src_lengths"] = sample["net_input"]["src_lengths"].cuda()
        sample["speaker"] = sample["speaker"].cuda()
        wav, rate = TTSHubInterface.get_prediction(self.task, self.model, self.generator, sample)
        return wav.cpu().numpy(),rate

def play(audio, samplerate):
    sd.play(audio, samplerate)
    sd.wait()