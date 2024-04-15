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

def strip(txt: str) -> str:
    translation_table = str.maketrans("", "", string.whitespace)
    return txt.translate(translation_table)

class ASpeech():
    def __init__(self):
        self.textQue = queue.Queue(maxsize=100)
        self.audioQue = queue.Queue(maxsize=100)
        self.t2s = None
        self.s2t = None

        self.inputDone = True
        self.lock = threading.Lock()
        self.noTextLeft = True
        
        self.textProcessor = threading.Thread(target=self.ProcessText, daemon=True)
        self.textProcessor.start()
        self.audioProcessor = threading.Thread(target=self.ProcessAudio, daemon=True)
        self.audioProcessor.start()
        return
    
    def ModuleInfo(self):
        return {"NAME": "speech", "ACTIONS": {"SPEECH_TO_TEXT": {"func": "Speech2Text", "prompt": "Speech to text.", "type": "primary"},
                                              "TEXT_TO_SPEECH": {"func": "Text2Speech", "prompt": "Text to speech.", "type": "primary"},
                                              "GET_AUDIO": {"func": "GetAudio", "prompt": "Get text input from microphone.", "type": "primary"},
                                              "PLAY": {"func": "Play", "prompt": "Synthesize input text fragments into audio and play.", "type": "primary"}}}
    
    def PrepareModel(self):
        self.t2s = T2S_LJS()
        self.s2t = S2T_WhisperLarge()
        return
    
    def SetDevices(self, deviceMap: dict[str,str]):
        if "stt" in deviceMap:
            self.s2t.To(deviceMap['stt'])
        elif "tts" in deviceMap:
            self.t2s.To(deviceMap['tts'])
        return
    
    def Speech2Text(self, wav: np.ndarray, sr: int) -> str:
        return self.s2t.recognize(audio_data_to_numpy((wav, sr)))

    def Text2Speech(self, txt: str) -> tuple[np.ndarray, int]:
        if (None == txt) or ("" == strip(txt)):
            return (np.zeros(1), 24000)
        return self.t2s(txt)
    
    def GetAudio(self) -> str:
        self.inputDone = True
        with self.lock:
            ret = self.s2t()
        return ret
    
    def Play(self, txt: str):
        print("Play(): ", txt)
        if (None == txt) or ("" == strip(txt)):
            return
        self.textQue.put(txt)
        self.inputDone = False
        return
    
    def ProcessText(self):
        while True:
            #The inter-thread synchronization issue here is more complex than it appears.
            self.noTextLeft = (self.inputDone and self.textQue.empty())
            text = self.textQue.get()
            try:
                self.audioQue.put(self.t2s(text))
            except Exception as e:
                print('EXCEPTION in ProcessText(). continue. e: ',str(e))
                continue
    
    def ProcessAudio(self):
        while True:
            time.sleep(0.1)
            with self.lock:
                while not (self.inputDone and self.noTextLeft and self.audioQue.empty()):
                    audio,sr = self.audioQue.get()
                    sd.play(audio, sr)
                    sd.wait()

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--addr',type=str, help="The address where the service runs on.")
    args = parser.parse_args()
    makeServer(ASpeech, dict(), args.addr, ["ModuleInfo", "PrepareModel", "Speech2Text", "Text2Speech", "GetAudio", "Play", "SetDevices"]).Run()

if __name__ == '__main__':
    main()