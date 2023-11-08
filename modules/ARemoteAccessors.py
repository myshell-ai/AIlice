from common.lightRPC import makeClient

storage = makeClient("ipc:///tmp/AIliceStorage.ipc", ['Store', 'Query'], returnClass=True)()
browser = makeClient("ipc:///tmp/ABrowser.ipc", ['Browse', 'ScrollDown'], returnClass=True)()
arxiv = makeClient("ipc:///tmp/AArxiv.ipc", ['ArxivSearch'], returnClass=True)()
google = makeClient("ipc:///tmp/AGoogle.ipc", ['Google', 'ScrollDown'], returnClass=True)()
speech = makeClient("ipc:///tmp/ASpeech.ipc", ['GetAudio', 'Play', 'Enable'], returnClass=True)()
scripter = makeClient("tcp://127.0.0.1:2005", ['RunBash', 'ScrollUpBash', 'RunPython', 'ScrollUpPy'], returnClass=True)()