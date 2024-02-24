import numpy as np
import sounddevice as sd
import torch
import librosa
from collections import deque


def audio_data_to_numpy(audio_data, sr=16000):
    if tuple != type(audio_data):
        audio_array = np.frombuffer(audio_data.frame_data, dtype=np.int16)
        sr0 = audio_data.sample_rate
    else:
        audio_array, sr0 = audio_data
    ret = librosa.resample(y=audio_array.astype(np.float32), orig_sr=sr0, target_sr=sr)
    return ret
    
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