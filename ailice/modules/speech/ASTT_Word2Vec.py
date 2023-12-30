import torch
from datasets import load_dataset
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

from ailice.modules.speech.AAudioSource import audio_data_to_numpy, AudioSourceSileroVAD


class S2T_Wave2Vec2():
    def __init__(self):
        self.LANG_ID = "zh-CN"
        #self.MODEL_ID = "jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn"
        self.MODEL_ID = "jonatasgrosman/wav2vec2-large-xlsr-53-english"
        self.SAMPLES = 10
        self.test_dataset = load_dataset("common_voice", self.LANG_ID, split=f"test[:{self.SAMPLES}]")

        self.processor = Wav2Vec2Processor.from_pretrained(self.MODEL_ID)
        self.model = Wav2Vec2ForCTC.from_pretrained(self.MODEL_ID)
        self.audio = AudioSourceSileroVAD()
        return

    def To(self, device: str):
        return
    
    def recognize_wav2vec2(self, wav):
        inputs = self.processor(wav, sampling_rate=16000, return_tensors="pt", padding=True)
        with torch.no_grad():
            logits = self.model(inputs.input_values, attention_mask=inputs.attention_mask).logits

        predicted_ids = torch.argmax(logits, dim=-1)
        predicted_sentences = self.processor.batch_decode(predicted_ids)
        print(predicted_sentences)
        return predicted_sentences[0]

    def __call__(self):
        said = ""
        while (said == ''):
            print("listening...")
            audio,sr = self.audio.get()
            print("got audio. processing...")
            try:
                said = self.recognize_wav2vec2(audio_data_to_numpy(audio, sr), sr=16000)
                print("audio recognized: ", said)
            except Exception as e:
                print("Exception: " + str(e))
                continue

        return said








