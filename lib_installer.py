import os
import subprocess
import sys
import importlib.metadata
import importlib.util
from typing import Iterable, Optional, Set

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

def _requirement_name(req_string: str) -> str:
    try:
        from packaging.requirements import Requirement
    except ImportError:
        return req_string.split("==", 1)[0].split(">=", 1)[0].split("<=", 1)[0].strip().lower()

    return Requirement(req_string).name.lower()


def install_requirements_in_directory(
    base_dir,
    skip_packages: Optional[Iterable[str]] = None,
    only_packages: Optional[Iterable[str]] = None,
):
    """Walk through folders to find requirements.txt and manage installations."""
    skip_packages_set: Set[str] = {pkg.lower() for pkg in (skip_packages or [])}
    only_packages_set: Optional[Set[str]] = (
        {pkg.lower() for pkg in only_packages} if only_packages is not None else None
    )
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
                    package_name = _requirement_name(req)
                    if package_name in skip_packages_set:
                        print(f"⏭️ Skipping optional local dependency: {req}")
                        continue
                    if only_packages_set is not None and package_name not in only_packages_set:
                        continue

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

    target_dir = os.path.dirname(os.path.abspath(__file__))
    local_stt_dependencies = {"openai-whisper", "pydub", "torch", "torchvision", "torchaudio"}
    install_whisper_local = os.getenv("INSTALL_WHISPER_LOCAL", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
        "si",
        "sí",
    }

    if os.path.exists(target_dir):
        print(f"🚀 Scanning directory: {target_dir}")
        if install_whisper_local:
            install_pytorch_cuda_forced()

        install_requirements_in_directory(
            target_dir,
            skip_packages=None if install_whisper_local else local_stt_dependencies,
        )

        if install_whisper_local and not check_ffmpeg_installed():
            print("\n⚠️ FFmpeg NOT found! Please install it for local Whisper audio processing.")
        elif not install_whisper_local:
            print("ℹ️ Local Whisper dependencies skipped. Set INSTALL_WHISPER_LOCAL=1 to install them.")

        print("\n✨ Setup completed successfully.")
    else:
        print(f"❌ Error: The directory '{target_dir}' was not found.")
