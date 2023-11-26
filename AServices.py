import subprocess
import signal

from common.AConfig import config

services = {"storage": ("modules.AStorageChroma","aservices"),
            "web": ("modules.ABrowser","aservices"),
            "arxiv": ("modules.AArxiv","aservices"),
            "google": ("modules.AGoogle","aservices"),
            "duckduckgo": ("modules.ADuckDuckGo","aservices")
            }

processes = []

def StartServices():
    if config.localExecution:
        try:
            subprocess.run("docker stop scripter", shell=True, check=True)
        except Exception:
            pass
        services['scripter'] = ("modules.AScripter","aservices")
    else:
        subprocess.run("docker start scripter", shell=True, check=True)
    if config.speechOn:
        services['speech'] = ("modules.ASpeech","tts")
    for serviceName in services:
        pyFile, env = services[serviceName]
        cmd = f"conda run -n {env} python3 -m {pyFile}"
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