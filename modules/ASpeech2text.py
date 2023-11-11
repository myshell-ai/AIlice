import os
import time
import speech_recognition as sr
import simplejson
import numpy as np
import sounddevice as sd
from collections import deque

import torch
import librosa
from datasets import load_dataset
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
from transformers import WhisperProcessor, WhisperForConditionalGeneration

from vosk import SetLogLevel
SetLogLevel(-1)

def audio_data_to_numpy(audio_data, sr=16000):
    if tuple != type(audio_data):
        audio_array = np.frombuffer(audio_data.frame_data, dtype=np.int16)
        sr0 = audio_data.sample_rate
    else:
        audio_array, sr0 = audio_data
    ret = librosa.resample(y=audio_array.astype(np.float32), orig_sr=sr0, target_sr=sr)
    return ret

class AudioSourceSR():
    def __init__(self, sr=16000):
        return
    
    def get(self):
        r = sr.Recognizer()
        with sr.Microphone() as source:
            return r.listen(source, phrase_time_limit=3)
    
class AudioSourceSileroVAD():
    def __init__(self, sr=16000):
        self.model, self.utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                      model='silero_vad',
                                      force_reload=False,
                                      onnx=False)
        self.sr = sr
        self.buffer = deque(maxlen=self.sr * 60)
        return
    
    def get(self):
        (get_speech_timestamps,
        save_audio,
        read_audio,
        VADIterator,
        collect_chunks) = self.utils
        
        chunk_samples = 512
        vad_iterator = VADIterator(self.model)

        wav = []
        with sd.InputStream(samplerate=self.sr, channels=1, blocksize=chunk_samples, dtype=np.int16) as stream:
            currentTime = 0.0
            while(True):
                audio_chunk, overflowed = stream.read(chunk_samples)
                audio_chunk = audio_chunk.reshape((chunk_samples,))
                self.buffer.append(list(audio_chunk))
                currentTime += (float(len(audio_chunk))/float(self.sr))
                
                startTime, endTime = 0.0, 0.0
                speech_dict = vad_iterator(audio_chunk, return_seconds=True)
                if speech_dict:
                    if "start" in speech_dict:
                        print("<---", flush=True)
                        startTime = speech_dict["start"]
                    elif "end" in speech_dict:
                        print("--->")
                        endTime = speech_dict["end"]
                        frm = -int(((currentTime - startTime) * self.sr) // chunk_samples) - 3
                        to = -int(((currentTime - endTime) * self.sr) // chunk_samples)
                        wav = sum(list(self.buffer)[frm:to], [])
                        #sd.play(wav,16000)
                        #sd.wait()
                        vad_iterator.reset_states()
                        self.buffer.clear()
                        return np.array(wav),self.sr

class S2T_SpeechRecognition():
    def __init__(self):
        self.audio = AudioSourceSR()
        return
    
    def __call__(self):
        r = sr.Recognizer()
        said = ""
        while (said == ''):
            print("listening...")
            audio = self.audio.get()
            print("got audio. processing...")
            try:
                #said = simplejson.loads(r.recognize_vosk(audio))['text']
                said = r.recognize_google(audio)
                print("audio recognized: ", said)
            except Exception as e:
                print("Exception: " + str(e))
                continue
        return said

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

class S2T_WhisperLarge():
    def __init__(self):
        self.device = "cpu"
        self.processor = WhisperProcessor.from_pretrained("openai/whisper-large-v3")
        self.model = WhisperForConditionalGeneration.from_pretrained("openai/whisper-large-v3").to(self.device)
        self.model.config.forced_decoder_ids = None
        self.audio = AudioSourceSileroVAD()
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











