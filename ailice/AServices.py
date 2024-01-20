import os
import sys
import subprocess
import signal
import psutil

from ailice.common.AConfig import config

processes = []

def StartServices():
    for process in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if process.info['cmdline'] and ('ailice.modules' in ' '.join(process.info['cmdline'])):
                print(f"killing proc with PID {process.info['pid']}")
                process.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
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