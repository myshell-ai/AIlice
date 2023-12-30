import speech_recognition as sr
from vosk import SetLogLevel
SetLogLevel(-1)

from ailice.modules.speech.AAudioSource import AudioSourceSR


class S2T_SpeechRecognition():
    def __init__(self):
        self.audio = AudioSourceSR()
        return
    
    def To(self, device: str):
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
