from transformers import WhisperProcessor, WhisperForConditionalGeneration

from modules.speech.AAudioSource import audio_data_to_numpy, AudioSourceSileroVAD


class S2T_WhisperLarge():
    def __init__(self):
        self.device = "cpu"
        self.processor = WhisperProcessor.from_pretrained("openai/whisper-large-v3")
        self.model = WhisperForConditionalGeneration.from_pretrained("openai/whisper-large-v3").to(self.device)
        self.model.config.forced_decoder_ids = None
        self.audio = AudioSourceSileroVAD()
        return
    
    def To(self, device: str):
        self.model = self.model.to(device)
        self.device = device
        return
    
    def __call__(self):
        said = ""
        while (said == ''):
            print("listening...")
            audio,sr = self.audio.get()
            print("got audio. processing...")
            try:
                said = self.recognize(audio_data_to_numpy((audio, sr), sr=16000))
                print("audio recognized: ", said)
            except Exception as e:
                print("Exception: " + str(e))
                continue
        return said
    
    def recognize(self, audio):
        input_features = self.processor(audio, sampling_rate=16000, return_tensors="pt").input_features 

        # generate token ids
        predicted_ids = self.model.generate(input_features.to(self.device))
        # decode token ids to text
        transcription = self.processor.batch_decode(predicted_ids.cpu(), skip_special_tokens=True)
        return transcription[0]











