import os
import subprocess
import sys

def detect_hardware():
    try:
        subprocess.run(["nvidia-smi"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return "cuda"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    try:
        subprocess.run(["rocminfo"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return "rocm"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    try:
        subprocess.run(["vulkaninfo"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return "vulkan"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return None

def main():
    hardware = detect_hardware()
    
    if hardware == "cuda":
        os.environ["CMAKE_ARGS"] = "-DGGML_CUDA=on -DLLAVA_BUILD=off"
        print("Detected Nvidia CUDA GPU. Using CUDA for installation.")
    elif hardware == "rocm":
        os.environ["CMAKE_ARGS"] = "-DGGML_HIPBLAS=on -DLLAVA_BUILD=off"
        print("Detected AMD ROCM GPU. Using HIPBLAS for installation.")
    elif hardware == "vulkan":
        os.environ["CMAKE_ARGS"] = "-DGGML_VULKAN=on -DLLAVA_BUILD=off"
        print("Detected Vulkan support. Using Vulkan for installation.")
    else:
        print("No compatible hardware detected. Exiting.")
        sys.exit(1)

    os.environ["FORCE_CMAKE"] = "1"

    subprocess.run([sys.executable, "-m", "pip", "install", "llama-cpp-python", "--force-reinstall", "--upgrade", "--no-cache-dir"])

if __name__ == "__main__":
    main()