#!/usr/bin/env python3

import os
import subprocess
import sys
import time

import torch


def launch_workers_and_ui():
    if os.environ.get("SKIP_MULTIPLE_WORKERS") or not torch.cuda.is_available():
        cmd = [sys.executable, "-m", "visionatrix", "run", "--ui"]
        os.execvpe(cmd[0], cmd, os.environ)

    total_gpus = torch.cuda.device_count()
    print(f"Detected {total_gpus} GPU(s).", flush=True)

    if total_gpus < 1:
        print("No GPUs found despite CUDA being available. Launching UI on CPU.", flush=True)
        cmd = [sys.executable, "-m", "visionatrix", "run", "--ui"]
        os.execvpe(cmd[0], cmd, os.environ)

    for idx in range(1, total_gpus):
        print(f"Launching WORKER on GPU {idx}.", flush=True)
        env_worker = os.environ.copy()
        env_worker["CUDA_VISIBLE_DEVICES"] = str(idx)
        worker_cmd = [sys.executable, "-m", "visionatrix", "run", "--mode=WORKER"]
        subprocess.Popen(worker_cmd, env=env_worker)
        print("Sleeping for 15 seconds before next launch...", flush=True)
        time.sleep(15)

    print("Launching Visionatrix on GPU 0.", flush=True)
    env_ui = os.environ.copy()
    env_ui["CUDA_VISIBLE_DEVICES"] = "0"
    ui_cmd = [sys.executable, "-m", "visionatrix", "run", "--ui"]
    os.execvpe(ui_cmd[0], ui_cmd, env_ui)


if __name__ == "__main__":
    launch_workers_and_ui()
