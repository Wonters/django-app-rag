# django-app-rag

**django-app-rag** est une application Django permettant d'intégrer facilement une fonctionnalité de Retrieval-Augmented Generation (RAG) dans un projet Django. Elle propose une API pour gérer des sources de documents, des questions/réponses, et des documents associés, ainsi qu'un front-end moderne basé sur Vue 3 et Vite.

## Fonctionnalités principales
- Gestion des sources de données (Notion, URL, Fichier)
- Modèles Questions, Réponses, Documents liés à une source
- API REST (DRF) pour manipuler ces objets
- Frontend moderne avec Vue 3 + Vite
- **Installation automatique des dépendances** (Playwright et Tesseract)

## Structure du projet
```
django-app-rag/
├── django_app_rag/
│   ├── models.py         # Modèles Django (Source, Questions, Answer, Documents)
│   ├── serializer.py     # Serializers DRF
│   ├── views.py          # Vue principale MainRAG (API)
│   ├── install_hooks.py  # Hooks d'installation automatique
│   └── ...
├── static/
│   ├── vite.config.js    # Config Vite pour Vue 3
│   └── frontend/
│       ├── main.js       # Entrée JS
│       ├── App.vue       # Composant racine Vue
│       └── style.css     # Styles globaux
├── install_dependencies.sh # Script d'installation des dépendances
├── setup.py              # Script d'installation alternatif
├── pyproject.toml        # Config package Python
├── requirements.txt      # Dépendances Python
└── README.md             # Ce fichier
```

## 🚀 Installation Automatique des Dépendances

Ce projet inclut un **système d'installation automatique** qui installe **Playwright** et **Tesseract** lors de l'installation du package.

### Installation Backend (Recommandée)

```bash
# Installation en mode développement avec dépendances automatiques
pip install -e .

# Ou installation normale
pip install .
```

Le script d'installation s'exécutera automatiquement après l'installation du package Python.

### Installation Alternative avec setup.py

```bash
# Installation en mode développement
python setup.py develop

# Ou installation normale
python setup.py install
```

## 🔧 Dépendances Installées Automatiquement

### Playwright
- **Navigateur web automatisé** pour le scraping et l'automatisation
- Installe automatiquement les navigateurs (Chromium, Firefox, WebKit)
- Compatible avec tous les systèmes d'exploitation

### Tesseract OCR
- **Moteur de reconnaissance optique de caractères**
- Support multilingue (français inclus)
- Installation automatique selon le système d'exploitation

## 🖥️ Support des Systèmes d'Exploitation

### Linux (Ubuntu/Debian, CentOS/RHEL, Fedora)
- Installation automatique via les gestionnaires de paquets système
- Support complet de Tesseract et Playwright

### macOS
- Installation via Homebrew (doit être installé)
- Support complet de Tesseract et Playwright

### Windows
- Installation automatique de Playwright uniquement
- Tesseract doit être installé manuellement depuis [UB-Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)

## 📋 Vérification de l'Installation

Après l'installation, vous pouvez vérifier que tout fonctionne :

```bash
# Vérifier Playwright
python -c "import playwright; print('Playwright installé')"

# Vérifier Tesseract
tesseract --version

# Vérifier les navigateurs Playwright
playwright --version
```

## 🛠️ Installation Manuelle (Si l'automatique échoue)

### Playwright
```bash
pip install playwright
playwright install
```

### Tesseract

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-fra
```

#### CentOS/RHEL
```bash
sudo yum install tesseract tesseract-langpack-fra
```

#### Fedora
```bash
sudo dnf install tesseract tesseract-langpack-fra
```

#### macOS
```bash
brew install tesseract tesseract-lang
```

#### Windows
Télécharger depuis [UB-Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)

## Installation des dépendances supplémentaires
1. **Installer PyTorch CPU**
   ```bash
   pip install --index-url https://download.pytorch.org/whl/cpu torch==2.4.1 --no-cache-dir
   ```

2. **Installer docling**
   ```bash
   pip install docling
   ```

## Installation frontend
1. **Aller dans le dossier static**
   ```bash
   cd static
   ```
2. **Installer les dépendances Node.js**
   ```bash
   npm install vue@next @vitejs/plugin-vue vite
   ```
3. **Lancer le serveur de développement**
   ```bash
   npm run dev
   ```
   Le front est accessible sur [http://localhost:5173](http://localhost:5173)

4. **Build de production**
   ```bash
   npm run build
   ```
   Les fichiers seront générés dans `static/dist`.

## 🔍 Dépannage

### Erreur de permissions
```bash
# Rendre le script exécutable
chmod +x install_dependencies.sh
```

### Erreur de dépendances système
- Vérifiez que vous avez les privilèges sudo (Linux)
- Vérifiez que Homebrew est installé (macOS)
- Mettez à jour vos gestionnaires de paquets

### Erreur Python
- Vérifiez que Python 3.8+ est installé
- Vérifiez que pip est à jour : `pip install --upgrade pip`

## 🎯 Utilisation dans le Code

Vous pouvez également déclencher l'installation manuellement depuis votre code :

```python
from django_app_rag.install_hooks import install_dependencies_manually

# Installer les dépendances
install_dependencies_manually()
```

## Utilisation
- L'API principale est accessible via la vue `MainRAG` (voir `views.py`).
- Le front Vue peut être intégré dans un template Django ou utilisé en mode SPA.

## Exemple d'API (GET)
```http
GET /api/rag/
{
  "message": "Bienvenue sur l'API RAG"
}
```

## Personnalisation
- Ajoutez vos endpoints, serializers, et composants Vue selon vos besoins RAG.
- Étendez les modèles pour gérer d'autres types de sources ou de documents.

## 📝 Logs d'Installation

Le script affiche des informations détaillées pendant l'installation :
- ✅ Succès
- ⚠️ Avertissements
- ❌ Erreurs
- 🔧 Instructions de dépannage

## 🤝 Contribution

Si vous rencontrez des problèmes d'installation sur votre système, n'hésitez pas à :
1. Vérifier les logs d'erreur
2. Tester l'installation manuelle
3. Ouvrir une issue avec les détails de votre système

## Licence
MIT

---
**Auteur :** Wonters / shift.python.software@gmail.com
