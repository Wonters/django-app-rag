# Services Frontend - Documentation

## Vue d'ensemble

Ce dossier contient les services frontend pour la gestion des tâches et des appels API. Les services ont été refactorisés pour une meilleure séparation des responsabilités et une réutilisabilité accrue.

## Fichiers

### apiService.js
Service centralisé pour gérer tous les appels HTTP avec gestion automatique du CSRF token.

### tasks.js
Service pour la gestion des tâches asynchrones avec polling automatique.

## Utilisation

### Initialisation (optionnelle)

Pour utiliser le logger intelligent de `useErrorHandler`, configurez-le dans votre composant Vue :

```javascript
// Dans votre composant principal ou App.vue
import { useErrorHandler } from '../composables/useErrorHandler.js';
import { setLogger } from '../services/tasks.js';

export default {
  setup() {
    const { logger } = useErrorHandler();
    setLogger(logger);
    
    return {
      // ... vos propriétés
    };
  }
}
```

**Note :** Si vous n'appelez pas `setLogger()`, les fonctions utiliseront automatiquement `console.log`, `console.warn`, et `console.error`.

### Import des services

```javascript
import apiService from './services/apiService.js';
import { 
    launchTask, 
    pollTaskStatus, 
    launchTaskAndPoll,
    launchCollectionInitialization,
    launchQAAnalysis 
} from './services/tasks.js';
```

### 1. Gestion des tâches génériques

#### Lancer une tâche simple
```javascript
try {
    const result = await launchTask('/api/tasks/', { 
        action: 'process_data',
        data: { /* ... */ }
    });
    console.log('Tâche lancée:', result.taskId);
} catch (error) {
    console.error('Erreur:', error.message);
}
```

#### Lancer et surveiller une tâche
```javascript
try {
    const result = await launchTaskAndPoll('/api/tasks/', {
        action: 'process_data',
        data: { /* ... */ }
    }, {
        onStatusUpdate: (status, data) => {
            console.log('Statut mis à jour:', status);
        },
        onSuccess: (data) => {
            console.log('Tâche terminée avec succès!');
        },
        onError: (error, data) => {
            console.error('Erreur:', error.message);
        }
    });
} catch (error) {
    console.error('Erreur:', error.message);
}
```

### 2. Initialisation de collection

```javascript
try {
    await launchCollectionInitialization(collectionId, {
        onStatusUpdate: (status, data) => {
            // Mettre à jour l'interface utilisateur
            updateCollectionStatus(collectionId, status);
        },
        onSuccess: (data) => {
            // Afficher un message de succès
            showSuccessMessage('Collection initialisée avec succès');
        },
        onError: (error, data) => {
            // Afficher l'erreur
            showErrorMessage('Erreur lors de l\'initialisation: ' + error.message);
        }
    });
} catch (error) {
    console.error('Erreur:', error.message);
}
```

### 3. Analyse QA

```javascript
try {
    await launchQAAnalysis(source, '/api/qa/analyze/', {
        onStatusUpdate: (status, data) => {
            // Mettre à jour le statut de la source
            source.qa_status = status;
            updateSourceDisplay(source);
        },
        onSuccess: (data) => {
            // Traitement en cas de succès
            console.log('Analyse QA terminée');
        },
        onError: (error, data) => {
            // Gestion des erreurs
            console.error('Erreur QA:', error.message);
        }
    });
} catch (error) {
    console.error('Erreur:', error.message);
}
```

### 4. Polling personnalisé

```javascript
try {
    const result = await pollTaskStatus(taskId, '/api/tasks/status/', {
        maxAttempts: 120,        // 10 minutes
        interval: 3000,          // Vérifier toutes les 3 secondes
        timeoutMessage: 'La tâche prend trop de temps',
        onStatusUpdate: (status, data) => {
            // Mise à jour en temps réel
            updateProgressBar(status);
        }
    });
} catch (error) {
    console.error('Erreur de polling:', error.message);
}
```

## Configuration

### Options de polling par défaut

```javascript
const DEFAULT_POLLING_CONFIG = {
    maxAttempts: 60,        // 5 minutes max
    interval: 5000,         // 5 secondes entre vérifications
    timeoutMessage: 'La tâche prend trop de temps'
};
```

### Callbacks disponibles

#### Pour les tâches génériques (`launchTask`, `pollTaskStatus`, `launchTaskAndPoll`)
- `onStatusUpdate(status, data)`: Appelé à chaque mise à jour du statut
- `onSuccess(data)`: Appelé en cas de succès
- `onError(error, data)`: Appelé en cas d'erreur
- `onComplete(finalStatus, data)`: Appelé à la fin (succès ou échec)

#### Pour `launchQAAnalysis` (spécifique aux sources)
- `onStatusUpdate(source, status, data)`: Appelé à chaque mise à jour du statut
- `onSuccess(data, source)`: Appelé en cas de succès
- `onError(error, source, data)`: Appelé en cas d'erreur
- `onComplete(source, finalStatus, data)`: Appelé à la fin (succès ou échec)

**Note :** Les signatures sont différentes pour permettre un accès direct à l'objet source dans les callbacks.

## Gestion des erreurs et logging

Toutes les fonctions utilisent des Promises et peuvent être utilisées avec try/catch. Le service utilise le logger de `useErrorHandler` pour une gestion intelligente des logs :

### Logging intelligent
- **En développement** : Tous les logs sont affichés
- **En production** : Seuls les erreurs sont loggées
- **Logs conditionnels** : `logger.log()`, `logger.warn()`, `logger.error()`

### Gestion des erreurs serveur
- **Erreurs 500+** : Arrêt immédiat du polling avec notification d'erreur
- **Erreurs 4xx** : Tentatives de retry selon la configuration
- **Gestion automatique** : Le service détecte et gère les erreurs serveur

```javascript
try {
    const result = await launchTask('/api/tasks/', data);
    // Traitement du succès
} catch (error) {
    // Gestion de l'erreur
    logger.error('Erreur lors du lancement de la tâche:', error);
    showErrorMessage(error.message);
}
```

### Utilisation du logger
```javascript
// Dans votre composant Vue
import { useErrorHandler } from '../composables/useErrorHandler.js';
import { setLogger } from '../services/tasks.js';

export default {
  setup() {
    const { logger } = useErrorHandler();
    
    // Configurer le logger personnalisé pour les tâches
    setLogger(logger);
    
    // Maintenant toutes les fonctions de tâches utiliseront ce logger
    return {
      // ... vos autres propriétés
    };
  }
}
```

**Alternative : Utilisation automatique du logger par défaut**
Si vous n'appelez pas `setLogger()`, les fonctions utiliseront automatiquement `console.log`, `console.warn`, et `console.error`.

## Avantages de la refactorisation

1. **Séparation des responsabilités** : `apiService.js` gère les appels HTTP, `tasks.js` gère la logique métier
2. **Réutilisabilité** : Fonctions génériques utilisables dans différents contextes
3. **Maintenabilité** : Code plus clair et mieux structuré
4. **Gestion d'erreurs** : Gestion centralisée et cohérente des erreurs
5. **Flexibilité** : Callbacks personnalisables pour différents cas d'usage
6. **Tests** : Plus facile à tester avec des fonctions pures et des dépendances injectées
7. **Logging intelligent** : Utilisation du logger de `useErrorHandler` avec gestion conditionnelle selon l'environnement

## Migration depuis l'ancien code

Si vous utilisez l'ancien code, voici comment migrer :

### Avant (ancien code)
```javascript
launchCollectionInitialization(collectionId, collection, originalText);
```

### Après (nouveau code)
```javascript
launchCollectionInitialization(collectionId, {
    onStatusUpdate: (status, data) => {
        // Mettre à jour l'interface
    },
    onSuccess: (data) => {
        // Gérer le succès
    }
});
```

## Exemple d'utilisation complète

Voici un exemple complet d'utilisation dans un composant Vue :

```vue
<template>
  <div>
    <button @click="initializeCollection">Initialiser la collection</button>
    <button @click="analyzeSource">Analyser la source</button>
  </div>
</template>

<script>
import { useErrorHandler } from '../composables/useErrorHandler.js';
import { setLogger, launchCollectionInitialization, launchQAAnalysis } from '../services/tasks.js';

export default {
  setup() {
    const { logger, showSuccess, showError } = useErrorHandler();
    
    // Configurer le logger pour les tâches
    setLogger(logger);
    
    const initializeCollection = async () => {
      try {
        await launchCollectionInitialization(123, {
          onStatusUpdate: (status, data) => {
            console.log('Statut:', status);
          },
          onSuccess: (data) => {
            showSuccess('Collection initialisée avec succès !');
          },
          onError: (error, data) => {
            showError('Erreur lors de l\'initialisation: ' + error.message);
          }
        });
      } catch (error) {
        showError('Erreur:', error.message);
      }
    };
    
    const analyzeSource = async () => {
      try {
        const source = { id: 456 };
        await launchQAAnalysis(source, '/api/qa/analyze/', {
          onStatusUpdate: (source, status, data) => {
            console.log('Statut mis à jour:', status);
          },
          onSuccess: (data, source) => {
            showSuccess('Analyse QA terminée !');
          },
          onError: (error, source, data) => {
            showError('Erreur QA:', error.message);
          },
          onComplete: (source, finalStatus, data) => {
            console.log('Analyse terminée avec le statut:', finalStatus);
          }
        });
      } catch (error) {
        showError('Erreur:', error.message);
      }
    };
    
    return {
      initializeCollection,
      analyzeSource
    };
  }
}
</script>
```

## Support

Pour toute question ou problème, consultez la documentation des fonctions individuelles dans le code source.
