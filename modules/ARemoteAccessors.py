from common.lightRPC import makeClient

storage = makeClient("ipc:///tmp/AIliceStorage.ipc", ['Store', 'Query'], returnClass=True)()
browser = makeClient("ipc:///tmp/ABrowser.ipc", ['Browse', 'ScrollDown'], returnClass=True)()
arxiv = makeClient("ipc:///tmp/AArxiv.ipc", ['ArxivSearch', 'ScrollDown'], returnClass=True)()
google = makeClient("ipc:///tmp/AGoogle.ipc", ['Google', 'ScrollDown'], returnClass=True)()
duckduckgo = makeClient("ipc:///tmp/ADuckDuckGo.ipc", ['DuckDuckGo', 'ScrollDown'], returnClass=True)()
speech = makeClient("ipc:///tmp/ASpeech.ipc", ['GetAudio', 'Play', 'SetDevices'], returnClass=True)()
scripter = makeClient("tcp://127.0.0.1:2005", ['RunBash', 'ScrollUpBash', 'RunPython', 'ScrollUpPy'], returnClass=True)()