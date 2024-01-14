import os
import sys
import subprocess
import signal

from ailice.common.AConfig import config

processes = []

def StartServices():
    os.system("ps aux | grep ailice.modules | awk '{print $2}' | xargs kill")
    if config.localExecution:
        config.services['scripter'] = {"cmd": "docker stop scripter; python3 -m ailice.modules.AScripter", "addr": "tcp://127.0.0.1:59000"}
    else:
        try:
            subprocess.run("docker -v", shell=True, check=True)
        except Exception:
            print("It looks like docker is not installed correctly. If you do not plan to use other virtual environments to execute scripts, please ensure that docker is installed correctly or use --localExecution to execute locally.")
    
    for serviceName, cfg in config.services.items():
        if ("speech" == serviceName) and not config.speechOn:
            continue
        if ("cmd" not in cfg) or ("" == cfg['cmd'].strip()):
            print(f"{serviceName}'s cmd is not configured and will attempt to connect {cfg['addr']} directly.")
            continue
        p = subprocess.Popen(cfg['cmd'], shell=True, cwd=None, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        processes.append(p)
        print(serviceName," started.")
    signal.signal(signal.SIGINT, TerminateSubprocess)
    signal.signal(signal.SIGTERM, TerminateSubprocess)

def TerminateSubprocess(signum=None, frame=None):
    for p in processes:
        if p.poll() is None:
            p.terminate()
            p.wait()
    sys.exit(0)