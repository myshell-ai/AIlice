import queue
import string
import threading
from modules.AText2speech import T2S_LJS,T2S_Transformer,play
from modules.ASpeech2text import S2T_SpeechRecognition,S2T_Wave2Vec2,S2T_WhisperLargeV2

from common.lightRPC import makeServer

def strip(txt: str) -> str:
    translation_table = str.maketrans("", "", string.whitespace)
    return txt.translate(translation_table)

class ASpeech():
    def __init__(self):
        self.enabled = True
        self.textQue = queue.Queue(maxsize=100)
        self.audioQue = queue.Queue(maxsize=100)
        self.t2s = T2S_LJS()
        self.s2t = S2T_WhisperLargeV2()

        self.inputDone = True
        self.lock = threading.Lock()
        
        self.textProcessor = threading.Thread(target=self.ProcessText, daemon=True)
        self.textProcessor.start()
        self.audioProcessor = threading.Thread(target=self.ProcessAudio, daemon=True)
        self.audioProcessor.start()
        return
    
    def Enable(self, enable):
        self.enabled = enable
        return
    
    def GetAudio(self):
        if not self.enabled:
            return ""
        self.inputDone = True
        with self.lock:
            ret = self.s2t()
        return ret
    
    def Play(self, txt: str):
        if not self.enabled:
            return
        print("Play(): ", txt)
        if (None == txt) or ("" == strip(txt)):
            return
        self.textQue.put(txt)
        self.inputDone = False
        return
    
    def ProcessText(self):
        while True:
            text = self.textQue.get()
            try:
                self.audioQue.put(self.t2s(text))
            except Exception as e:
                print('EXCEPTION in ProcessText(). continue. e: ',str(e))
                continue
    
    def ProcessAudio(self):
        while True:
            with self.lock:
                while not (self.inputDone and self.textQue.empty() and self.audioQue.empty()):
                    audio,sr = self.audioQue.get()
                    play(audio,sr)



speech = ASpeech()
makeServer(speech, "ipc:///tmp/ASpeech.ipc").Run()