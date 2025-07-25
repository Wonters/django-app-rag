# django-app-rag

**django-app-rag** est une application Django permettant d'intégrer facilement une fonctionnalité de Retrieval-Augmented Generation (RAG) dans un projet Django. Elle propose une API pour gérer des sources de documents, des questions/réponses, et des documents associés, ainsi qu'un front-end moderne basé sur Vue 3 et Vite.

## Fonctionnalités principales
- Gestion des sources de données (Notion, URL, Fichier)
- Modèles Questions, Réponses, Documents liés à une source
- API REST (DRF) pour manipuler ces objets
- Frontend moderne avec Vue 3 + Vite

## Structure du projet
```
django-app-rag/
├── django_app_rag/
│   ├── models.py         # Modèles Django (Source, Questions, Answer, Documents)
│   ├── serializer.py     # Serializers DRF
│   ├── views.py          # Vue principale MainRAG (API)
│   └── ...
├── static/
│   ├── vite.config.js    # Config Vite pour Vue 3
│   └── frontend/
│       ├── main.js       # Entrée JS
│       ├── App.vue       # Composant racine Vue
│       └── style.css     # Styles globaux
├── pyproject.toml        # Config package Python
├── requirements.txt      # Dépendances Python
└── README.md             # Ce fichier
```

## Installation backend
1. **Installer les dépendances Python**
   ```bash
   pip install -r requirements.txt
   playwright install 
   ```
2. **Ajouter l'app à `INSTALLED_APPS` dans `settings.py`**
   ```python
   INSTALLED_APPS = [
       ...
       'django_app_rag',
   ]
   ```
3. **Créer les tables**
   ```bash
   python manage.py makemigrations django_app_rag
   python manage.py migrate
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

## Licence
MIT

---
**Auteur :** Wonters / shift.python.software@gmail.com
