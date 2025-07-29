from termcolor import colored
import queue
import copy
from queue import Empty

class KMsgQue():
    def __init__(self):
        self.colorMap = {'CONTEXT': 'blue', 'USER': 'green', 'ASSISTANT': 'green', 'SYSTEM': 'yellow', 'OUTPUT': 'green'}
        self.depth = -1
        self.buffer = []
        self.queue = queue.Queue()
        return
    
    def ParseChannel(self, channel: str) -> tuple[str]:
        if channel in ["<", ">"]:
            return channel, ""
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
    
    def SinkBuffer(self, channel: str, txt: str = None, action: str = ''):
        if (">" == channel):
            if (-1 == self.depth):
                self.queue.put({'message': '', 'role': '', 'action': '', 'msgType': ''})
        elif ("<" == channel):
            return
        else:
            self.queue.put({'message': txt, 'role': channel, 'action': action, 'msgType': 'internal' if (self.depth > 0) or (self.ParseChannel(channel)[0] == 'SYSTEM') else 'user-ailice'})
        return

    def Load(self, messages: list):
        self.buffer = copy.deepcopy(messages)
        return
    
    def Get(self, timeout=None, getBuffer = False):
        if getBuffer:
            return copy.deepcopy(self.buffer)
        else:
            msg = self.queue.get(timeout=timeout)
            msg['isRoundEnd'] = ((self.depth == -1) and (msg['role'] == ''))
            if not msg['isRoundEnd']:
                self.buffer.append(msg)
            return msg
    
    def Receiver(self, channel: str, txt: str = None, action: str = ''):
        braketMap = {"<": 1, ">": -1}
        self.depth += (braketMap[channel] if channel in braketMap else 0)
        
        channelType, _ = self.ParseChannel(channel)
        if (channelType in ["ASSISTANT", "SYSTEM"]):
            self.SinkPrint(channel=channel, txt=txt, action=action)
        if ((channelType in ["ASSISTANT", "SYSTEM", ">"]) or (("USER" == channelType) and (self.depth == 0))):
            self.SinkBuffer(channel=channel, txt=txt, action=action)
        return
    