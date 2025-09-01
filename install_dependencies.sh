#!/bin/bash

# Script d'installation des dépendances pour django-app-rag
# Installe Playwright et Tesseract

set -e  # Arrêter le script en cas d'erreur

echo "🚀 Installation des dépendances pour django-app-rag..."
echo "=================================================="

# Fonction pour détecter le système d'exploitation
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

# Fonction pour installer Tesseract selon le système d'exploitation
install_tesseract() {
    local os=$1
    echo "📝 Installation de Tesseract OCR..."
    
    case $os in
        "linux")
            if command -v apt-get &> /dev/null; then
                echo "📦 Installation via apt-get (Ubuntu/Debian)..."
                sudo apt-get update
                sudo apt-get install -y tesseract-ocr tesseract-ocr-fra
            elif command -v yum &> /dev/null; then
                echo "📦 Installation via yum (CentOS/RHEL)..."
                sudo yum install -y tesseract tesseract-langpack-fra
            elif command -v dnf &> /dev/null; then
                echo "📦 Installation via dnf (Fedora)..."
                sudo dnf install -y tesseract tesseract-langpack-fra
            else
                echo "❌ Gestionnaire de paquets non reconnu. Veuillez installer Tesseract manuellement."
                return 1
            fi
            ;;
        "macos")
            if command -v brew &> /dev/null; then
                echo "🍺 Installation via Homebrew..."
                brew install tesseract tesseract-lang
            else
                echo "❌ Homebrew non installé. Veuillez installer Homebrew puis Tesseract manuellement."
                echo "   Installer Homebrew: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
                return 1
            fi
            ;;
        "windows")
            echo "❌ Installation de Tesseract sur Windows non automatisée."
            echo "   Veuillez télécharger et installer Tesseract depuis: https://github.com/UB-Mannheim/tesseract/wiki"
            return 1
            ;;
        *)
            echo "❌ Système d'exploitation non reconnu: $os"
            return 1
            ;;
    esac
    
    # Vérifier l'installation
    if command -v tesseract &> /dev/null; then
        echo "✅ Tesseract installé avec succès: $(tesseract --version | head -n1)"
    else
        echo "❌ Échec de l'installation de Tesseract"
        return 1
    fi
}

# Fonction pour installer Playwright
install_playwright() {
    echo "🎭 Installation de Playwright..."
    
    # Vérifier si Python et pip sont disponibles
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python3 n'est pas installé ou n'est pas dans le PATH"
        return 1
    fi
    
    if ! command -v pip3 &> /dev/null; then
        echo "❌ pip3 n'est pas installé ou n'est pas dans le PATH"
        return 1
    fi
    
    # Installer Playwright via pip
    echo "📦 Installation de Playwright via pip..."
    pip3 install playwright
    
    # Installer les navigateurs
    echo "🌐 Installation des navigateurs Playwright..."
    python3 -m playwright install
    
    # Vérifier l'installation
    if python3 -c "import playwright; print('✅ Playwright installé avec succès')" 2>/dev/null; then
        echo "✅ Playwright installé avec succès"
    else
        echo "❌ Échec de l'installation de Playwright"
        return 1
    fi
}

# Fonction principale
main() {
    local os=$(detect_os)
    echo "🖥️  Système d'exploitation détecté: $os"
    
    # Vérifier les privilèges sudo sur Linux
    if [[ "$os" == "linux" ]]; then
        if ! sudo -n true 2>/dev/null; then
            echo "🔐 Privilèges sudo requis pour l'installation de Tesseract"
            echo "   Veuillez entrer votre mot de passe si demandé"
        fi
    fi
    
    # Installer Tesseract
    if install_tesseract "$os"; then
        echo "✅ Tesseract installé avec succès"
    else
        echo "⚠️  Échec de l'installation de Tesseract - veuillez l'installer manuellement"
    fi
    
    # Installer Playwright
    if install_playwright; then
        echo "✅ Playwright installé avec succès"
    else
        echo "⚠️  Échec de l'installation de Playwright - veuillez l'installer manuellement"
    fi
    
    echo ""
    echo "🎉 Installation terminée!"
    echo "📋 Vérification des installations:"
    
    # Vérifications finales
    if command -v tesseract &> /dev/null; then
        echo "   ✅ Tesseract: $(tesseract --version | head -n1)"
    else
        echo "   ❌ Tesseract: Non installé"
    fi
    
    if python3 -c "import playwright" 2>/dev/null; then
        echo "   ✅ Playwright: Installé"
    else
        echo "   ❌ Playwright: Non installé"
    fi
    
    echo ""
    echo "🔧 Si des installations ont échoué, veuillez les installer manuellement:"
    echo "   - Tesseract: https://tesseract-ocr.github.io/tessdoc/Installation.html"
    echo "   - Playwright: https://playwright.dev/python/docs/intro"
}

# Exécuter le script principal
main "$@"
