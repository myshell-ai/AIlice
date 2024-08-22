from termcolor import colored
import queue

from ailice.common.AConfig import config

class ALogger():
    def __init__(self, speech):
        self.colorMap = {'CONTEXT': 'blue', 'USER': 'green', 'ASSISTANT': 'green', 'SYSTEM': 'yellow', 'OUTPUT': 'green'}
        self.depth = -1
        self.speech = speech
        self.queue = queue.Queue()
        return
    
    def ParseChannel(self, channel: str) -> tuple[str]:
        l = channel.find("_")
        channelType, agentName = channel[:l], channel[l+1:]
        return channelType, agentName
    
    def SinkPrint(self, channel: str, txt: str = None, action: str = ''):
        channelType, agentName = self.ParseChannel(channel)
        if 'open' == action:
            print(colored(channel + ": ", self.colorMap[channelType]), txt, end="", flush=True)
        elif 'append' == action:
            print(txt, end="", flush=True)
        elif 'close' == action:
            print(txt, end="", flush=True)
            print("")
        else:
            print(colored(channel + ": ", self.colorMap[channelType]), txt)
        return
    
    def SinkSpeech(self, channel: str, txt: str = None, action: str = ''):
        if self.speech:
            self.speech.Play(txt)
        return
    
    def SinkQueue(self, channel: str, txt: str = None, action: str = ''):
        self.queue.put((channel, txt, action))
        return

    def Receiver(self, channel: str, txt: str = None, action: str = ''):
        braketMap = {"<": 1, ">": -1}
        self.depth += (braketMap[channel] if channel in braketMap else 0)
        
        channelType, _ = self.ParseChannel(channel)
        if (channelType in ["ASSISTANT", "SYSTEM"]):
            self.SinkPrint(channel=channel, txt=txt, action=action)
        if config.speechOn and ((channelType in ["ASSISTANT"]) and (0 == self.depth)):
            self.SinkSpeech(channel=channel, txt=txt, action=action)
        if ((channelType in ["OUTPUT"]) and (1 == self.depth)) or\
           (((channelType in ["ASSISTANT"]) and (0 == self.depth))):
            self.SinkQueue(channel=channel, txt=txt, action=action)
        if (channel in [">"]) and (-1 == self.depth):
            self.SinkQueue(channel=channel, txt=None, action=None)
        return
    
class ALoggerSection:
    def __init__(self, recv):
        self.recv = recv
        return
    
    def __enter__(self):
        self.recv("<")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.recv(">")
        return False
    
    def __call__(self, channel: str, txt: str = None, action: str = ""):
        return self.recv(channel, txt, action)
    
class ALoggerMsg:
    def __init__(self, recv, channel):
        self.recv = recv
        self.channel = channel
        return
    
    def __enter__(self):
        self.recv(channel = self.channel, txt = "", action = "open")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.recv(channel = self.channel, txt = "", action = "close")
        return False
    
    def __call__(self, txt: str):
        return self.recv(channel = self.channel, txt = txt, action = "append")
    