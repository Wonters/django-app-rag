#!/usr/bin/env python3
"""
Script d'installation pour django-app-rag avec hooks automatiques.
"""

from setuptools import setup, find_packages
from setuptools.command.develop import develop
from setuptools.command.install import install
import subprocess
import sys
import os
from pathlib import Path


class PostDevelopCommand(develop):
    """Commande personnalisée pour exécuter le hook après l'installation en mode développement."""
    
    def run(self):
        develop.run(self)
        self.execute_post_install()


class PostInstallCommand(install):
    """Commande personnalisée pour exécuter le hook après l'installation."""
    
    def run(self):
        install.run(self)
        self.execute_post_install()
    
    def execute_post_install(self):
        """Exécute le script d'installation des dépendances."""
        try:
            # Importer et exécuter le hook
            from django_app_rag.install_hooks import run_post_install
            run_post_install()
        except ImportError:
            print("⚠️  Impossible d'importer le module d'installation, exécution du script shell...")
            self.run_shell_script()
        except Exception as e:
            print(f"❌ Erreur lors de l'exécution du hook: {e}")
            self.run_shell_script()
    
    def run_shell_script(self):
        """Exécute directement le script shell si le hook Python échoue."""
        try:
            script_path = Path(__file__).parent / "install_dependencies.sh"
            if script_path.exists():
                print("🚀 Exécution directe du script shell...")
                if os.name == 'nt':  # Windows
                    print("🪟 Windows détecté - installation de Playwright uniquement")
                    subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
                    subprocess.run([sys.executable, "-m", "playwright", "install"], check=True)
                    print("✅ Playwright installé")
                else:
                    # Linux/macOS
                    os.chmod(script_path, 0o755)
                    subprocess.run([str(script_path)], check=True)
            else:
                print("❌ Script install_dependencies.sh non trouvé")
        except Exception as e:
            print(f"❌ Erreur lors de l'exécution du script shell: {e}")


# Lire le contenu du pyproject.toml pour les métadonnées
def read_pyproject_toml():
    """Lit les métadonnées depuis pyproject.toml."""
    import tomllib
    
    try:
        with open("pyproject.toml", "rb") as f:
            data = tomllib.load(f)
            return data.get("project", {})
    except ImportError:
        # Fallback pour Python < 3.11
        try:
            import tomli as tomllib
            with open("pyproject.toml", "rb") as f:
                data = tomllib.load(f)
                return data.get("project", {})
        except ImportError:
            print("⚠️  tomllib/tomli non disponible, utilisation des valeurs par défaut")
            return {}


# Lire les dépendances depuis requirements.txt
def read_requirements():
    """Lit les dépendances depuis requirements.txt."""
    try:
        with open("requirements.txt", "r") as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]
    except FileNotFoundError:
        return []


if __name__ == "__main__":
    # Lire les métadonnées depuis pyproject.toml
    project_data = read_pyproject_toml()
    
    setup(
        name=project_data.get("name", "django-rag-app"),
        version=project_data.get("version", "0.1.0"),
        description=project_data.get("description", "A Django application for RAG functionality"),
        long_description=open("README.md").read() if os.path.exists("README.md") else "",
        long_description_content_type="text/markdown",
        author=project_data.get("authors", [{}])[0].get("name", "Wonters"),
        author_email=project_data.get("authors", [{}])[0].get("email", "shift.python.software@gmail.com"),
        url=project_data.get("urls", {}).get("Homepage", ""),
        packages=find_packages(),
        python_requires=project_data.get("requires-python", ">=3.8"),
        install_requires=read_requirements(),
        classifiers=project_data.get("classifiers", []),
        cmdclass={
            'develop': PostDevelopCommand,
            'install': PostInstallCommand,
        },
        include_package_data=True,
        zip_safe=False,
    )
