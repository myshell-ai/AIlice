from termcolor import colored
import queue

class ALogger():
    def __init__(self, speech):
        self.colorMap = {'CONTEXT': 'blue', 'USER': 'green', 'ASSISTANT': 'green', 'SYSTEM': 'yellow', 'OUTPUT': 'green'}
        self.depth = -1
        self.speech = speech
        self.queue = queue.Queue()
        return
    
    def SinkPrint(self, channel: str, txt: str = None, action: str = ''):
        if 'open' == action:
            print(colored(channel + ": ", self.colorMap[channel]), txt, end="", flush=True)
        elif 'append' == action:
            print(txt, end="", flush=True)
        elif 'close' == action:
            print(txt, end="", flush=True)
            print("")
        else:
            print(colored(channel + ": ", self.colorMap[channel]), txt)
        return
    
    def SinkSpeech(self, channel: str, txt: str = None, action: str = ''):
        if 'open' == action:
            self.speech.Play(txt)
        elif 'append' == action:
            self.speech.Play(txt)
        elif 'close' == action:
            self.speech.Play(txt)
            self.speech.Play(None)#end flag.
        else:
            self.speech.Play(txt)
        return
    
    def SinkQueue(self, channel: str, txt: str = None, action: str = ''):
        if 'open' == action:
            self.txtBuf = {"channel": channel, "txt": txt}
        elif 'append' == action:
            assert self.txtBuf['channel'] == channel, "assert self.txtBuf['channel'] == channel FAILED."
            self.txtBuf['txt'] += txt
        elif 'close' == action:
            assert self.txtBuf['channel'] == channel, "assert self.txtBuf['channel'] == channel FAILED."
            self.txtBuf['txt'] += txt
            self.queue.put((channel, self.txtBuf['txt']))
        else:
            self.queue.put((channel, txt))
        return

    def Receiver(self, channel: str, txt: str = None, action: str = ''):
        braketMap = {"<": 1, ">": -1}
        self.depth += (braketMap[channel] if channel in braketMap else 0)
        
        if (channel in ["ASSISTANT", "SYSTEM"]):
            self.SinkPrint(channel=channel, txt=txt, action=action)
        if ((channel in ["ASSISTANT"]) and (0 == self.depth)):
            self.SinkSpeech(channel=channel, txt=txt, action=action)
        if ((channel in ["OUTPUT"]) and (1 == self.depth)) or\
           (((channel in ["ASSISTANT"]) and (0 == self.depth))):
            self.SinkQueue(channel=channel, txt=txt, action=action)
        if (channel in [">"]) and (-1 == self.depth):
            self.SinkQueue(channel=channel, txt=None, action=None)
        return