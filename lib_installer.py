import os
import subprocess
import sys
import importlib.metadata
import time

# --- CONFIGURACIÓN ---
TARGET_DIR = r"C:\Apps\AsRec_Reviewer"
MAIN_SCRIPT = os.path.join(TARGET_DIR, "main.py")

def ensure_pip():
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"],
                       check=True, capture_output=True)
        print("✅ pip está listo.")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️ pip no encontrado. Instalando...")
        subprocess.check_call([sys.executable, "-m", "ensurepip", "--upgrade"])

def is_installed(req_string):
    try:
        from packaging.requirements import Requirement
    except ImportError:
        print("📦 Instalando 'packaging'...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "packaging"])
        from packaging.requirements import Requirement

    try:
        req = Requirement(req_string)
        dist_version = importlib.metadata.version(req.name)
        if not req.specifier or dist_version in req.specifier:
            return True, dist_version
        return False, dist_version
    except importlib.metadata.PackageNotFoundError:
        return False, None

def install_torch_universal():
    # Incluimos 'packaging' en la lista por si acaso
    packages = ["torch==2.5.1", "torchvision", "torchaudio", "torch-directml", "packaging"]
    
    print("\n🔍 Verificando entorno PyTorch + DirectML...")
    to_install = [pkg for pkg in packages if not is_installed(pkg)[0]]
    
    if not to_install:
        print("✅ PyTorch y aceleradores ya están instalados.")
        return

    has_nvidia = False
    try:
        subprocess.run(["nvidia-smi"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        has_nvidia = True
        print("🎮 GPU NVIDIA detectada.")
    except:
        print("🖥️ Usando configuración de GPU genérica (DirectML).")

    install_cmd = [sys.executable, "-m", "pip", "install"] + to_install
    if has_nvidia:
        install_cmd += ["--extra-index-url", "https://download.pytorch.org/whl/cu121"]
    
    print(f"📦 Instalando: {', '.join(to_install)}...")
    subprocess.check_call(install_cmd)

def install_requirements(base_dir):
    for root, _, files in os.walk(base_dir):
        if "requirements.txt" in files:
            req_path = os.path.join(root, "requirements.txt")
            print(f"\n🔍 Procesando dependencias en: {req_path}")
            
            with open(req_path, 'r', encoding='utf-8') as f:
                reqs = [l.strip() for l in f if l.strip() and not l.startswith(('#', '-r'))]
            
            for req in reqs:
                if "torch" in req.lower(): continue # Ya lo manejamos arriba
                
                installed, _ = is_installed(req)
                if not installed:
                    print(f"📦 Instalando {req}...")
                    subprocess.check_call([sys.executable, "-m", "pip", "install", req])
                else:
                    print(f"✅ {req} OK.")

def run_main_app():
    """Lanza el script principal en un proceso nuevo para que reconozca los paquetes."""
    if os.path.exists(MAIN_SCRIPT):
        print(f"\n🚀 ¡Todo listo! Iniciando aplicación: {MAIN_SCRIPT}")
        print("-" * 50)
        # Usamos subprocess.Popen para que el proceso sea independiente
        subprocess.Popen([sys.executable, MAIN_SCRIPT], creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)
    else:
        print(f"❌ Error: No se encontró {MAIN_SCRIPT}")

if __name__ == "__main__":
    print("=== INSTALADOR AUTOMÁTICO ASREC REVIEWER ===")
    
    if not os.path.exists(TARGET_DIR):
        print(f"❌ Error: El directorio {TARGET_DIR} no existe.")
        sys.exit(1)

    try:
        ensure_pip()
        install_torch_universal()
        install_requirements(TARGET_DIR)
        
        print("\n✨ Configuración completada con éxito.")
        
        # El truco final: lanzar la app
        run_main_app()
        
        print("\n👋 Puedes cerrar esta ventana. La aplicación se está ejecutando.")
        time.sleep(3) # Pausa para que el usuario lea el éxito
        
    except Exception as e:
        print(f"\n❌ Error crítico durante la instalación: {e}")
        input("Presiona ENTER para salir...")
