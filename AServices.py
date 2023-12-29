import subprocess
import signal

from common.AConfig import config

processes = []

def StartServices():
    if config.localExecution:
        config.services['scripter'] = {"cmd": "docker stop scripter; conda run -n aservices python3 -m modules.AScripter", "addr": "tcp://127.0.0.1:2005"}
    else:
        try:
            subprocess.run("docker -v", shell=True, check=True)
        except Exception:
            print("It looks like docker is not installed correctly. Please confirm whether you have installed docker. If you want to run the scripter locally, please use the --localExecution option.")
            exit(1)
    
    for serviceName, cfg in config.services.items():
        if ("speech" == serviceName) and not config.speechOn:
            continue
        p = subprocess.Popen(cfg['cmd'], shell=True, cwd=None)
        processes.append(p)
        print(serviceName," started.")
    signal.signal(signal.SIGINT, TerminateSubprocess)
    signal.signal(signal.SIGTERM, TerminateSubprocess)

def TerminateSubprocess(signum, frame):
    for p in processes:
        if p.poll() is None:
            p.terminate()
    exit(1)