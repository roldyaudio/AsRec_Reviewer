import os
import subprocess
import sys
import importlib.metadata
import importlib.util

def ensure_pip():
    """Ensures pip is available by checking the module via subprocess."""
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"],
                       check=True, capture_output=True)
        print("✅ pip is already installed.")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️ pip not found. Installing with ensurepip...")
        subprocess.check_call([sys.executable, "-m", "ensurepip", "--upgrade"])
        print("✅ pip installed successfully.")

def install_pytorch_cuda_forced():
    """
    Forced installation of PyTorch with CUDA 12.4 support.
    This ensures 'import torch' works everywhere and uses GPU if available.
    """
    print("🔍 Checking PyTorch installation...")
    
    # Verificamos si torch ya está instalado
    torch_installed = importlib.util.find_spec("torch") is not None
    
    if torch_installed:
        import torch
        # Si ya está instalado y tiene soporte CUDA, no hacemos nada
        if torch.version.cuda:
            print(f"✅ PyTorch with CUDA {torch.version.cuda} is already installed.")
            return
        else:
            print("⚠️ PyTorch found but it's the CPU version. Upgrading to CUDA version...")
    else:
        print("📦 PyTorch not found. Starting installation...")

    # Comando para instalar la versión con CUDA 12.4
    # Usamos --upgrade para asegurar que si hay una versión CPU, la reemplace
    command = [
        sys.executable, "-m", "pip", "install", 
        "torch", "torchvision", "torchaudio", 
        "--index-url", "https://download.pytorch.org/whl/cu124",
        "--upgrade"
    ]

    try:
        print("🚀 Downloading PyTorch + CUDA (~2.5GB). Please wait...")
        subprocess.check_call(command)
        print("✨ PyTorch with CUDA support installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing PyTorch: {e}")
        sys.exit(1)

def check_ffmpeg_installed():
    """Checks if FFmpeg is available in the system PATH."""
    try:
        subprocess.run(["ffmpeg", "-version"],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def is_installed(req_string):
    """Checks if a package meets the required version."""
    try:
        from packaging.requirements import Requirement
    except ImportError:
        print("📦 Installing 'packaging' for version parsing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "packaging"], check=True)
        from packaging.requirements import Requirement

    try:
        req = Requirement(req_string)
        # Especial handling for torch to avoid re-installing over our CUDA version
        if req.name.lower() in ["torch", "torchvision", "torchaudio"]:
            if importlib.util.find_spec(req.name.lower()):
                return True, importlib.metadata.version(req.name.lower())

        dist_version = importlib.metadata.version(req.name)
        if not req.specifier:
            return True, dist_version
        if dist_version in req.specifier:
            return True, dist_version
        else:
            return False, dist_version
    except importlib.metadata.PackageNotFoundError:
        return False, None
    except Exception as e:
        print(f"❌ Error parsing {req_string}: {e}")
        return False, None

def install_requirements_in_directory(base_dir):
    """Walk through folders to find requirements.txt and manage installations."""
    found_any = False
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file == "requirements.txt":
                found_any = True
                req_path = os.path.join(root, file)
                print(f"\n🔍 Processing: {req_path}")

                try:
                    with open(req_path, 'r', encoding='utf-8') as f:
                        requirements = [line.strip() for line in f
                                        if line.strip() and not line.startswith(('#', '-r'))]
                except Exception as e:
                    print(f"❌ Failed to read {req_path}: {e}")
                    continue

                for req in requirements:
                    installed, current_v = is_installed(req)
                    if installed:
                        print(f"✅ {req} is satisfied.")
                    else:
                        print(f"📦 {req} not found or mismatch. Installing...")
                        result = subprocess.run([sys.executable, "-m", "pip", "install", req])
                        if result.returncode != 0:
                            print(f"❌ Failed to install {req}")
                            sys.exit(1)
    if not found_any:
        print(f"ℹ️ No requirements.txt files found in {base_dir}")

if __name__ == "__main__":
    if sys.version_info >= (3, 13):
        print("⚠️ Warning: Python 3.13+ detected.")

    print("🔧 Preparing environment...")
    ensure_pip()

    # 1. Forzar la instalación de PyTorch con soporte CUDA primero
    install_pytorch_cuda_forced()

    # 2. Procesar el resto de dependencias
    TARGET_DIR = r"C:/Apps/AsRec_Reviewer"

    if os.path.exists(TARGET_DIR):
        print(f"🚀 Scanning directory: {TARGET_DIR}")
        install_requirements_in_directory(TARGET_DIR)

        if not check_ffmpeg_installed():
            print("\n⚠️ FFmpeg NOT found! Please install it for audio processing.")

        print("\n✨ Setup completed successfully.")
    else:
        print(f"❌ Error: The directory '{TARGET_DIR}' was not found.")
