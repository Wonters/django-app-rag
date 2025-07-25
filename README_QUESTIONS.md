# Gestion des Questions - RAG Django

## Vue d'ensemble

Ce module ajoute la possibilité de gérer des questions liées aux sources dans l'application RAG Django. Les utilisateurs peuvent maintenant :

1. **Voir les détails d'une source** avec toutes ses informations
2. **Ajouter des questions** à une source spécifique
3. **Modifier des questions** existantes
4. **Supprimer des questions**
5. **Voir les réponses** générées pour chaque question

## Architecture

### Composants Vue.js

#### `SourceDetail.vue`
- Page principale de détail d'une source
- Affiche les informations de la source
- Gère la liste des questions
- Permet d'ajouter/modifier des questions
- **Navigation fluide** : Pas de rechargement de page

#### `QuestionList.vue`
- Composant d'affichage de la liste des questions
- Interface accordéon pour afficher les questions et réponses
- Actions d'édition et suppression
- Gestion des états de chargement des réponses

#### `QuestionForm.vue`
- Modal pour ajouter/modifier des questions
- Formulaire intégré via iframe
- Gestion des paramètres de source

### Backend Django

#### Modèles
- `Question` : Modèle pour stocker les questions
  - `title` : Titre de la question
  - `field` : Contenu détaillé de la question
  - `source` : Relation vers la source parente

#### Vues
- `QuestionFormView` : Formulaire de création/modification de questions
- `QuestionModelViewSet` : API REST pour les questions

#### URLs
- `/question/add/` : Formulaire d'ajout de question
- `/question/<pk>/edit/` : Formulaire de modification de question
- `/api/questions/` : API REST des questions

## Utilisation

### Navigation
1. Depuis la liste des sources, cliquer sur le bouton "Voir détails" (icône œil)
2. La page de détail s'affiche avec les informations de la source (navigation Vue.js)
3. Cliquer sur "Ajouter une question" pour créer une nouvelle question

### Ajout d'une question
1. Cliquer sur "Ajouter une question"
2. Remplir le formulaire :
   - **Titre** : Titre court de la question
   - **Contenu** : Description détaillée de la question
3. Cliquer sur "Ajouter"

### Modification d'une question
1. Dans la liste des questions, cliquer sur l'icône crayon
2. Modifier les champs souhaités
3. Cliquer sur "Modifier"

### Suppression d'une question
1. Dans la liste des questions, cliquer sur l'icône poubelle
2. Confirmer la suppression

## Configuration

### Variables JavaScript requises
Les URLs suivantes doivent être définies dans le template principal :

```javascript
window.QUESTION_FORM_URL = "{% url 'django_app_rag:question-add' %}";
window.QUESTION_API_URL = "{% url 'django_app_rag:questions-list' %}";
```

### Traductions
Les clés de traduction suivantes sont utilisées :

**Français** (`fr.json`) :
- "Détails de la source"
- "Questions et réponses"
- "Ajouter une question"
- "Modifier la question"
- etc.

**Anglais** (`en.json`) :
- "Source details"
- "Questions and answers"
- "Add a question"
- "Edit question"
- etc.

## API REST

### Questions
- `GET /api/questions/` : Liste toutes les questions
- `GET /api/questions/?source=<id>` : Questions d'une source spécifique
- `POST /api/questions/` : Créer une nouvelle question
- `PUT /api/questions/<id>/` : Modifier une question
- `DELETE /api/questions/<id>/` : Supprimer une question

### Format des données
```json
{
  "id": 1,
  "title": "Titre de la question",
  "field": "Contenu détaillé de la question",
  "source": 1,
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

## Avantages de l'approche Vue.js

1. **Navigation fluide** : Pas de rechargement de page lors de la navigation
2. **État partagé** : Les données des sources sont déjà chargées
3. **Interface cohérente** : Même design et comportement que le reste de l'app
4. **Performance** : Navigation plus rapide
5. **Maintenance** : Un seul endroit à maintenir pour l'interface

## Développement

### Ajout de nouvelles fonctionnalités
1. Créer les composants Vue.js dans `static/frontend/`
2. Ajouter les vues Django dans `views.py` (si nécessaire)
3. Définir les URLs dans `urls.py` (si nécessaire)
4. Mettre à jour les traductions
5. Tester l'intégration

### Tests
- Tester l'ajout de questions
- Tester la modification de questions
- Tester la suppression de questions
- Tester la navigation entre les vues
- Tester les traductions FR/EN 