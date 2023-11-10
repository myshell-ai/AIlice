import subprocess
import signal

services = {"storage": ("modules/AStorageChroma.py","aservices"),
            "web": ("modules/ABrowser.py","aservices"),
            "arxiv": ("modules/AArxiv.py","aservices"),
            "google": ("modules/AGoogle.py","aservices"),
            "duckduckgo": ("modules/ADuckDuckGo.py","aservices"),
            #"scripter": ("modules/AScripter.py","aservices"),
            "speech": ("modules/ASpeech.py","tts")
            }

processes = []

def StartServices():
    for serviceName in services:
        pyFile, env = services[serviceName]
        cmd = f"conda run -n {env} python3 {pyFile}"
        p = subprocess.Popen(cmd, shell=True, cwd=None)
        processes.append(p)
        print(serviceName," started.")
    signal.signal(signal.SIGINT, TerminateSubprocess)
    signal.signal(signal.SIGTERM, TerminateSubprocess)

def TerminateSubprocess(signum, frame):
    for p in processes:
        if p.poll() is None:
            p.terminate()
    exit(1)