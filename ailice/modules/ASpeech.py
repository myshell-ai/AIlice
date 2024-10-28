import queue
import string
import threading
import time
import numpy as np
import sounddevice as sd
from ailice.modules.speech.AAudioSource import audio_data_to_numpy
from ailice.modules.speech.ATTS_LJS import T2S_LJS
from ailice.modules.speech.ASTT_Whisper import S2T_WhisperLarge

from ailice.common.lightRPC import makeServer

class ASpeech:
    def __init__(self):
        self.text_queue = queue.Queue(maxsize=100)
        self.audio_queue = queue.Queue(maxsize=100)
        self.t2s = None
        self.s2t = None

        self.input_done = True
        self.lock = threading.Lock()
        self.no_text_left = True
        
        self.text_processor = threading.Thread(target=self.process_text, daemon=True)
        self.text_processor.start()
        self.audio_processor = threading.Thread(target=self.process_audio, daemon=True)
        self.audio_processor.start()
        return
    
    def module_info(self):
        return {"NAME": "speech", "ACTIONS": {"SPEECH-TO-TEXT": {"func": "speech2text", "prompt": "Speech to text.", "type": "primary"},
                                              "TEXT-TO-SPEECH": {"func": "text2speech", "prompt": "Text to speech.", "type": "primary"},
                                              "GET-AUDIO": {"func": "get_audio", "prompt": "Get text input from microphone.", "type": "primary"},
                                              "PLAY": {"func": "play", "prompt": "Synthesize input text fragments into audio and play.", "type": "primary"}}}
    
    def prepare_model(self):
        if None in [self.t2s, self.s2t]:
            self.t2s = T2S_LJS()
            self.s2t = S2T_WhisperLarge()
        return
    
    def set_devices(self, device_map: dict[str,str]):
        if "stt" in device_map:
            self.s2t.to(device_map['stt'])
        elif "tts" in device_map:
            self.t2s.to(device_map['tts'])
        return
    
    def speech2text(self, wav: np.ndarray, sr: int) -> str:
        return self.s2t.recognize(audio_data_to_numpy((wav, sr)))

    def text2speech(self, txt: str) -> tuple[np.ndarray, int]:
        if (None == txt) or ("" == self.strip(txt)):
            return (np.zeros(1), 24000)
        return self.t2s(txt)
    
    def get_audio(self) -> str:
        self.input_done = True
        with self.lock:
            ret = self.s2t()
        return ret
    
    def play(self, txt: str):
        print("Play(): ", txt)
        if (None == txt) or ("" == self.strip(txt)):
            return
        self.text_queue.put(txt)
        self.input_done = False
        return
    
    def process_text(self):
        while True:
            #The inter-thread synchronization issue here is more complex than it appears.
            self.no_text_left = (self.input_done and self.text_queue.empty())
            text = self.text_queue.get()
            try:
                self.audio_queue.put(self.t2s(text))
            except Exception as e:
                print('EXCEPTION in ProcessText(). continue. e: ',str(e))
                continue
    
    def process_audio(self):
        while True:
            time.sleep(0.1)
            with self.lock:
                while not (self.input_done and self.no_text_left and self.audio_queue.empty()):
                    audio,sr = self.audio_queue.get()
                    sd.play(audio, sr)
                    sd.wait()
    
    def strip(self, txt: str) -> str:
        translation_table = str.maketrans("", "", string.whitespace)
        return txt.translate(translation_table)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--addr',type=str, help="The address where the service runs on.")
    args = parser.parse_args()
    makeServer(ASpeech, dict(), args.addr, ["module_info", "prepare_model", "speech2text", "text2speech", "get_audio", "play", "set_devices"]).Run()

if __name__ == '__main__':
    main()
