import os
import sys
import subprocess
import signal
import psutil
import logging

from ailice.common.AConfig import config

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def start_services():
    """
    Start services defined in the config file.
    """
    # Kill existing processes
    for process in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if process.info['cmdline'] and ('ailice.modules' in ' '.join(process.info['cmdline'])):
                logging.info(f"Killing process with PID {process.info['pid']}")
                process.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    # Start new processes
    processes = []
    for service_name, cfg in config.services.items():
        if ("speech" == service_name) and not config.speechOn:
            continue
        if ("cmd" not in cfg) or ("" == cfg['cmd'].strip()):
            logging.warning(f"{service_name}'s cmd is not configured and will attempt to connect {cfg['addr']} directly.")
            continue
        try:
            p = subprocess.Popen(cfg['cmd'], shell=True, cwd=None, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            processes.append(p)
            logging.info(f"{service_name} started.")
        except Exception as e:
            logging.error(f"Failed to start {service_name}: {e}")

    # Set up signal handlers
    def terminate_subprocess(signum=None, frame=None):
        """
        Terminate subprocesses and exit.
        """
        for p in processes:
            if p.poll() is None:
                p.terminate()
                p.wait()
        sys.exit(0)

    signal.signal(signal.SIGINT, terminate_subprocess)
    signal.signal(signal.SIGTERM, terminate_subprocess)

    return processes

def main():
    """
    Main entry point.
    """
    processes = start_services()
    while True:
        # Keep the main process running
        pass

if __name__ == "__main__":
    main()
