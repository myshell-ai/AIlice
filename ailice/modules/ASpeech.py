import queue
import string
import threading
import sounddevice as sd
from modules.speech.ATTS_LJS import T2S_LJS
from modules.speech.ASTT_Whisper import S2T_WhisperLarge

from common.lightRPC import makeServer

def strip(txt: str) -> str:
    translation_table = str.maketrans("", "", string.whitespace)
    return txt.translate(translation_table)

class ASpeech():
    def __init__(self):
        self.textQue = queue.Queue(maxsize=100)
        self.audioQue = queue.Queue(maxsize=100)
        self.t2s = T2S_LJS()
        self.s2t = S2T_WhisperLarge()

        self.inputDone = True
        self.lock = threading.Lock()
        self.noTextLeft = True
        
        self.textProcessor = threading.Thread(target=self.ProcessText, daemon=True)
        self.textProcessor.start()
        self.audioProcessor = threading.Thread(target=self.ProcessAudio, daemon=True)
        self.audioProcessor.start()
        return
    
    def ModuleInfo(self):
        return {"NAME": "speech", "ACTIONS": {"GETAUDIO": {"sig": "GetAudio()->str", "prompt": "Get text input from microphone."},
                                              "PLAY": {"sig": "Play(txt:str)->None", "prompt": "Synthesize input text fragments into audio and play."}}}
    
    def SetDevices(self, deviceMap: dict[str,str]):
        if "stt" in deviceMap:
            self.s2t.To(deviceMap['stt'])
        elif "tts" in deviceMap:
            self.t2s.To(deviceMap['tts'])
        return
    
    def GetAudio(self):
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
            with self.lock:
                while not (self.inputDone and self.noTextLeft and self.audioQue.empty()):
                    audio,sr = self.audioQue.get()
                    sd.play(audio, sr)
                    sd.wait()

speech = ASpeech()
makeServer(speech, "ipc:///tmp/ASpeech.ipc", ["ModuleInfo", "GetAudio", "Play", "SetDevices"]).Run()