import os
import subprocess
import sys
import importlib.metadata

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
        subprocess.check_call([sys.executable, "-m", "pip", "install", "packaging"])
        from packaging.requirements import Requirement

    try:
        req = Requirement(req_string)
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

def install_torch_universal():
    """
    Instala PyTorch y soporte DirectML para que funcione en cualquier GPU (NVIDIA/AMD/Intel).
    Si ya están instalados, los salta.
    """
    # Definimos los paquetes base para que funcione en cualquier PC
    # 'torch-directml' permite usar GPUs AMD e Intel en Windows
    packages = ["torch==2.5.1", "torchvision", "torchaudio", "torch-directml"]
    
    print("\n🔍 Verificando entorno de procesamiento (PyTorch + DirectML)...")
    
    to_install = []
    for pkg in packages:
        installed, version = is_installed(pkg)
        if not installed:
            to_install.append(pkg)
    
    if not to_install:
        print("✅ PyTorch y aceleradores ya están instalados.")
        return

    # Si necesitamos instalar algo, detectamos si hay NVIDIA para usar su repo oficial
    # De lo contrario, usamos el estándar de PyPI que es más compatible
    has_nvidia = False
    try:
        subprocess.run(["nvidia-smi"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        has_nvidia = True
    except:
        pass

    install_cmd = [sys.executable, "-m", "pip", "install"] + to_install
    
    if has_nvidia:
        # Si tiene NVIDIA, añadimos el index de CUDA por si acaso, pero sin forzar el +cu121
        install_cmd += ["--extra-index-url", "https://download.pytorch.org/whl/cu121"]
    
    print(f"📦 Instalando dependencias de hardware: {', '.join(to_install)}...")
    try:
        subprocess.check_call(install_cmd)
        print("✅ Hardware configurado correctamente.")
    except subprocess.CalledProcessError:
        print("❌ Error instalando librerías de procesamiento.")
        sys.exit(1)

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
                    # Saltamos torch si aparece en el txt para manejarlo con nuestra función especial
                    if "torch" in req.lower():
                        continue
                        
                    installed, current_v = is_installed(req)
                    if installed:
                        print(f"✅ {req} is already satisfied.")
                    elif current_v:
                        print(f"⚠️ Conflict for {req}: installed {current_v}. Skipping.")
                    else:
                        print(f"📦 Installing {req}...")
                        result = subprocess.run([sys.executable, "-m", "pip", "install", req])
                        if result.returncode != 0:
                            print(f"❌ Failed to install {req}")
                            sys.exit(1)

if __name__ == "__main__":
    if sys.version_info >= (3, 13):
        print("⚠️ Warning: Python 3.13+ detected. 'pydub' might fail due to missing 'audioop'.")

    print("🔧 Initializing setup...")
    ensure_pip()

    TARGET_DIR = r"C:/Apps/AsRec_Reviewer"

    if os.path.exists(TARGET_DIR):
        print(f"🚀 Target directory: {TARGET_DIR}")
        
        # Primero instalamos Torch de forma inteligente
        install_torch_universal()
        
        # Luego el resto de dependencias
        install_requirements_in_directory(TARGET_DIR)

        if not check_ffmpeg_installed():
            print("\n⚠️ FFmpeg NOT found! Please install it for audio processing.")

        print("\n✨ Setup completed successfully.")
    else:
        print(f"❌ Error: {TARGET_DIR} not found.")
