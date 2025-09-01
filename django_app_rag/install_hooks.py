"""
Hooks d'installation pour django-app-rag.
Exécute automatiquement le script d'installation des dépendances après l'installation du package.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path


def run_post_install():
    """
    Hook exécuté après l'installation du package.
    Lance le script d'installation des dépendances (Playwright et Tesseract).
    """
    try:
        # Obtenir le chemin du répertoire d'installation
        package_dir = Path(__file__).parent.parent
        script_path = package_dir / "install_dependencies.sh"
        
        print("🚀 Exécution du script d'installation des dépendances...")
        print(f"📁 Script trouvé: {script_path}")
        
        # Vérifier que le script existe
        if not script_path.exists():
            print("❌ Script install_dependencies.sh non trouvé")
            return
        
        # Rendre le script exécutable (au cas où)
        os.chmod(script_path, 0o755)
        
        # Détecter le système d'exploitation
        system = platform.system().lower()
        
        if system == "windows":
            # Sur Windows, utiliser PowerShell ou cmd
            print("🪟 Système Windows détecté")
            print("⚠️  L'installation automatique de Tesseract n'est pas supportée sur Windows")
            print("   Veuillez installer Tesseract manuellement depuis: https://github.com/UB-Mannheim/tesseract/wiki")
            
            # Installer seulement Playwright sur Windows
            print("🎭 Installation de Playwright...")
            subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
            subprocess.run([sys.executable, "-m", "playwright", "install"], check=True)
            print("✅ Playwright installé avec succès")
            
        else:
            # Sur Linux/macOS, exécuter le script shell
            print(f"🐧 Système {system} détecté")
            
            # Exécuter le script shell
            result = subprocess.run(
                [str(script_path)],
                cwd=package_dir,
                capture_output=True,
                text=True,
                shell=True
            )
            
            # Afficher la sortie
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print("⚠️  Erreurs lors de l'exécution:", result.stderr)
            
            if result.returncode == 0:
                print("✅ Script d'installation exécuté avec succès")
            else:
                print(f"⚠️  Script d'installation terminé avec le code de sortie: {result.returncode}")
        
        print("🎉 Installation des dépendances terminée!")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'exécution du hook d'installation: {e}")
        print("🔧 Veuillez installer manuellement Playwright et Tesseract:")
        print("   - Playwright: pip install playwright && playwright install")
        print("   - Tesseract: https://tesseract-ocr.github.io/tessdoc/Installation.html")


# Fonction alternative pour l'installation manuelle
def install_dependencies_manually():
    """
    Fonction pour installer manuellement les dépendances.
    Peut être appelée depuis le code si nécessaire.
    """
    print("🔧 Installation manuelle des dépendances...")
    
    try:
        # Installer Playwright
        print("🎭 Installation de Playwright...")
        subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
        subprocess.run([sys.executable, "-m", "playwright", "install"], check=True)
        print("✅ Playwright installé avec succès")
        
        # Afficher les instructions pour Tesseract
        system = platform.system().lower()
        if system == "windows":
            print("⚠️  Tesseract doit être installé manuellement sur Windows")
            print("   Télécharger depuis: https://github.com/UB-Mannheim/tesseract/wiki")
        else:
            print("📝 Tesseract doit être installé via le gestionnaire de paquets du système:")
            if system == "darwin":  # macOS
                print("   brew install tesseract tesseract-lang")
            else:  # Linux
                print("   sudo apt-get install tesseract-ocr tesseract-ocr-fra  # Ubuntu/Debian")
                print("   sudo yum install tesseract tesseract-langpack-fra      # CentOS/RHEL")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de l'installation de Playwright: {e}")
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")


if __name__ == "__main__":
    # Permet d'exécuter le script directement pour tester
    run_post_install()
