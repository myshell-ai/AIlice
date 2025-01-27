import os
import subprocess
import sys
def detect_hardware():
    hardwares = []
    try:
        subprocess.run(["nvidia-smi"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        hardwares.append("cuda")
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    try:
        subprocess.run(["rocminfo"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        hardwares.append("rocm")
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    try:
        subprocess.run(["vulkaninfo"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        hardwares.append("vulkan")
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return hardwares

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--hardware',type=str,default=None, help="Specify preferred hardware, options include: cuda/rocm/vulkan.")
    kwargs = vars(parser.parse_args())

    hardwares = detect_hardware()
    print(f"Detected {'/'.join(hardwares)} support.")
    
    if (kwargs["hardware"] is None) and (len(hardwares) > 0):
        hardware = hardwares[0]
    elif (kwargs["hardware"] in hardwares):
        hardware = kwargs["hardware"]
    
    if hardware == "cuda":
        os.environ["CMAKE_ARGS"] = "-DGGML_CUDA=on -DLLAVA_BUILD=off"
        print("Using CUDA for installation.")
    elif hardware == "rocm":
        os.environ["CMAKE_ARGS"] = "-DGGML_HIPBLAS=on -DLLAVA_BUILD=off"
        print("Using HIPBLAS for installation.")
    elif hardware == "vulkan":
        os.environ["CMAKE_ARGS"] = "-DGGML_VULKAN=on -DLLAVA_BUILD=off"
        print("Using Vulkan for installation.")
    else:
        print("No compatible hardware detected. Exiting.")
        sys.exit(0)
    
    os.environ["FORCE_CMAKE"] = "1"
    subprocess.run([sys.executable, "-m", "pip", "install", "llama-cpp-python", "--force-reinstall", "--upgrade", "--no-cache-dir"])
if __name__ == "__main__":
    main()