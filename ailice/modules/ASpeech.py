import queue
import string
import threading
import time
import numpy as np
import sounddevice as sd
from ailice.modules.speech.AAudioSource import audio_data_to_numpy
from ailice.modules.speech.ATTS_ChatTTS import T2S_ChatTTS
from ailice.modules.speech.ASTT_Whisper import S2T_WhisperLarge

from ailice.common.lightRPC import makeServer

def strip(txt: str) -> str:
    translation_table = str.maketrans("", "", string.whitespace)
    return txt.translate(translation_table)

t2s = None
s2t = None

class ASpeech():
    def __init__(self):
        self.textQue = queue.Queue(maxsize=100)
        self.audioQue = queue.Queue(maxsize=100)

        self.inputDone = True
        self.lock = threading.Lock()
        self.noTextLeft = True
        
        self.textProcessor = threading.Thread(target=self.ProcessText, daemon=True)
        self.textProcessor.start()
        self.audioProcessor = threading.Thread(target=self.ProcessAudio, daemon=True)
        self.audioProcessor.start()
        return
    
    def ModuleInfo(self):
        return {"NAME": "speech", "ACTIONS": {"SPEECH-TO-TEXT": {"func": "Speech2Text", "prompt": "Speech to text.", "type": "primary"},
                                              "TEXT-TO-SPEECH": {"func": "Text2Speech", "prompt": "Text to speech.", "type": "primary"},
                                              "GET-AUDIO": {"func": "GetAudio", "prompt": "Get text input from microphone.", "type": "primary"},
                                              "SPEAK": {"func": "Speak", "prompt": "Synthesize input text fragments into audio and play.", "type": "primary"},
                                              "SWITCH-TONE": {"func": "SwitchTone", "prompt": "Switch the TTS system to a new tone.", "type": "primary"}}}
    
    def PrepareModel(self):
        global s2t, t2s

        if None in [t2s, s2t]:
            t2s = T2S_ChatTTS()
            s2t = S2T_WhisperLarge()
        return
    
    def SetDevices(self, deviceMap: dict[str,str]):
        global s2t, t2s

        if "stt" in deviceMap:
            s2t.To(deviceMap['stt'])
        elif "tts" in deviceMap:
            t2s.To(deviceMap['tts'])
        return
    
    def Speech2Text(self, wav: list, sr: int) -> str:
        global s2t
        return s2t.recognize(audio_data_to_numpy((np.array(wav), sr)))

    def Text2Speech(self, txt: str) -> tuple[list, int]:
        global t2s
        
        if (None == txt) or ("" == strip(txt)):
            return ([1], 24000)
        audio, sr = t2s(txt)
        return audio.tolist(), sr
    
    def GetAudio(self) -> str:
        global s2t

        self.inputDone = True
        with self.lock:
            ret = s2t()
        return ret
    
    def Speak(self, txt: str):
        print("Speak(): ", txt)
        if (None == txt) or ("" == strip(txt)):
            return
        self.textQue.put(txt)
        self.inputDone = False
        return
    
    def SwitchTone(self) -> str:
        global t2s
        return t2s.SwitchTone()
    
    def ProcessText(self):
        global t2s
        while True:
            #The inter-thread synchronization issue here is more complex than it appears.
            self.noTextLeft = (self.inputDone and self.textQue.empty())
            text = self.textQue.get()
            try:
                self.audioQue.put(t2s(text))
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
    makeServer(ASpeech, dict(), args.addr, ["ModuleInfo", "PrepareModel", "Speech2Text", "Text2Speech", "GetAudio", "Speak", "SwitchTone", "SetDevices"]).Run()

if __name__ == '__main__':
    main()