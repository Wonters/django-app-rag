# Système de Persistance des Pollings

Ce document explique comment le système de persistance des pollings fonctionne dans l'application Django RAG.

## Vue d'ensemble

Le système de persistance des pollings permet de :
- Maintenir l'état des pollings en cours lors de la navigation entre les vues
- Sauvegarder l'état des pollings dans le localStorage pour survivre aux rechargements de page
- Afficher un indicateur visuel des tâches en cours
- Permettre à l'utilisateur de gérer les pollings actifs

## Architecture

### Composants principaux

1. **`usePollingState.js`** - Composable principal pour gérer l'état global des pollings
2. **`usePollingPersistence.js`** - Composable pour la persistance dans le localStorage
3. **`PollingStatusIndicator.vue`** - Composant d'interface pour afficher et gérer les pollings
4. **Modifications dans `SourceList.vue`** - Intégration du système de polling

### Flux de données

```
SourceList.vue
    ↓ (lance un polling)
usePollingState.js
    ↓ (sauvegarde automatique)
usePollingPersistence.js
    ↓ (stockage)
localStorage
```

## Utilisation

### Dans un composant Vue

```javascript
import { usePollingState } from '../composables/usePollingState.js';

const {
  addActivePolling,
  removeActivePolling,
  updatePollingStatus,
  hasActivePolling,
  updateSourceStatus,
  getSourceStatus,
  applySourceStatuses
} = usePollingState();

// Lancer un polling
addActivePolling(sourceId, 'qa', taskId, config);

// Mettre à jour le statut
updatePollingStatus(sourceId, 'qa', 'running');

// Vérifier si un polling est actif
if (hasActivePolling(sourceId, 'qa')) {
  // Polling en cours
}

// Appliquer les statuts sauvegardés aux sources
const sourcesWithStatus = applySourceStatuses(sources);
```

### Types de tâches supportées

- `qa` - Analyse QA
- `indexing` - Indexation

### Statuts supportés

- `pending` - En attente
- `running` - En cours
- `completed` - Terminé
- `failed` - Échoué

## Fonctionnalités

### Persistance automatique

- L'état des pollings est automatiquement sauvegardé dans le localStorage
- La sauvegarde se déclenche à chaque modification de l'état
- L'état est restauré automatiquement au chargement de la page

### Gestion de l'expiration

- Les pollings sauvegardés expirent après 30 minutes
- Les pollings expirés sont automatiquement nettoyés
- Le localStorage est nettoyé automatiquement en cas d'erreur

### Interface utilisateur

- Indicateur visuel des tâches en cours (coin supérieur droit)
- Détails des pollings actifs avec possibilité d'arrêt
- Bouton pour arrêter toutes les tâches en cours

## Configuration

### Configuration par défaut

```javascript
const defaultConfig = {
  maxAttempts: 60,        // 5 minutes max (60 * 5 secondes)
  interval: 5000,         // Vérifier toutes les 5 secondes
  timeoutMessage: 'La tâche prend trop de temps'
};
```

### Personnalisation

```javascript
// Ajouter un polling avec configuration personnalisée
addActivePolling(sourceId, 'qa', taskId, {
  maxAttempts: 120,       // 10 minutes
  interval: 3000,         // 3 secondes
  timeoutMessage: 'Analyse QA trop longue'
});
```

## Gestion des erreurs

### Erreurs de localStorage

- En cas d'erreur de lecture/écriture, le système continue de fonctionner
- Les erreurs sont loggées mais n'interrompent pas l'application
- Le localStorage est nettoyé en cas d'erreur de parsing

### Erreurs de polling

- Les pollings échoués sont marqués avec le statut `failed`
- L'utilisateur peut relancer les tâches échouées
- Les erreurs sont affichées via le système de notifications

## Nettoyage

### Nettoyage automatique

- Les pollings expirés sont automatiquement supprimés
- Le localStorage est nettoyé lors des erreurs
- Les timers sont nettoyés lors du démontage des composants

### Nettoyage manuel

```javascript
// Nettoyer tous les pollings
clearAllPollings();

// Nettoyer le localStorage
clearStorage();

// Nettoyer les pollings expirés
cleanupExpiredPollings(30 * 60 * 1000); // 30 minutes
```

## Débogage

### Logs

Le système génère des logs détaillés pour :
- Ajout/suppression de pollings
- Mise à jour des statuts
- Sauvegarde/restauration depuis le localStorage
- Erreurs et nettoyage

### Inspection de l'état

```javascript
// Obtenir tous les pollings actifs
const activePollings = getActivePollings();

// Obtenir les statuts d'une collection
const statuses = getCollectionSourceStatuses(collectionId);

// Vérifier l'état du localStorage
const hasValidState = hasValidPollingState();
const stateInfo = getPollingStateInfo();
```

## Bonnes pratiques

1. **Toujours nettoyer les pollings** lors du démontage des composants
2. **Vérifier l'état avant de lancer** un nouveau polling
3. **Gérer les erreurs** de manière appropriée
4. **Tester la persistance** en rechargeant la page
5. **Surveiller les logs** pour détecter les problèmes

## Limitations

- Les pollings ne survivent pas à la fermeture du navigateur
- La persistance est limitée par la taille du localStorage
- Les pollings expirés ne sont pas automatiquement relancés
- Le système ne gère pas les pollings inter-collections

## Évolutions futures

- Support des Web Workers pour les pollings en arrière-plan
- Synchronisation entre onglets
- Persistance côté serveur
- Gestion des pollings inter-collections
- Interface de gestion avancée des pollings
