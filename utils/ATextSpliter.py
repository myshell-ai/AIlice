import re
from modules.ARemoteAccessors import speech 

def sentences_split(paragraph):
    for sent in re.findall(u'[^?。；，\.\?\;\,]+[?。；，\.\?\;\,]?', paragraph, flags=re.U):
        yield sent

def try_play(txt: str, tail=False):
    if not tail:
        sentences = [x for x in sentences_split(txt)]
        if 2 <= len(sentences):
            if "" != sentences[0].strip():
                print(sentences[0], end="", flush=True)
                speech.play(sentences[0])
            return len(sentences[0])
        else:
            return 0
    else:
        print(txt, end="", flush=True)
        speech.play(txt)
        speech.play(None)#end flag.