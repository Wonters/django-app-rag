# Guide de Test - Système de Persistance des Pollings

Ce guide explique comment tester le système de persistance des pollings pour s'assurer qu'il fonctionne correctement.

## Tests à effectuer

### 1. Test de persistance lors de la navigation

**Objectif :** Vérifier que les pollings continuent lors de la navigation entre les vues.

**Étapes :**
1. Sélectionner une collection
2. Lancer une analyse QA ou une indexation sur une source
3. Attendre que le statut passe à "running"
4. Cliquer sur "Voir détails" pour aller à la vue détail
5. Revenir à la liste des sources
6. **Résultat attendu :** Le polling doit toujours être actif et le statut "running" doit être préservé

### 2. Test de persistance lors du rechargement de page

**Objectif :** Vérifier que les pollings survivent au rechargement de la page.

**Étapes :**
1. Lancer une analyse QA ou une indexation
2. Attendre que le statut passe à "running"
3. Recharger la page (F5 ou Ctrl+R)
4. **Résultat attendu :** 
   - L'indicateur de polling doit apparaître en haut à droite
   - Le statut "running" doit être préservé
   - Le polling doit continuer normalement

### 3. Test de l'indicateur de polling

**Objectif :** Vérifier que l'interface utilisateur affiche correctement les pollings actifs.

**Étapes :**
1. Lancer plusieurs analyses QA et indexations
2. Vérifier que l'indicateur apparaît en haut à droite
3. Cliquer sur la flèche pour voir les détails
4. **Résultat attendu :**
   - L'indicateur doit afficher le nombre de tâches en cours
   - Les détails doivent lister toutes les tâches actives
   - Chaque tâche doit afficher son statut et sa durée

### 4. Test de gestion des pollings

**Objectif :** Vérifier que l'utilisateur peut arrêter les pollings.

**Étapes :**
1. Lancer plusieurs pollings
2. Ouvrir les détails de l'indicateur
3. Cliquer sur le bouton d'arrêt d'une tâche spécifique
4. Cliquer sur "Arrêter tout"
5. **Résultat attendu :**
   - La tâche spécifique doit s'arrêter
   - Toutes les tâches doivent s'arrêter avec "Arrêter tout"
   - L'indicateur doit disparaître quand aucune tâche n'est active

### 5. Test de changement de collection

**Objectif :** Vérifier que les pollings sont préservés lors du changement de collection.

**Étapes :**
1. Lancer des pollings dans une collection
2. Changer de collection
3. Revenir à la collection originale
4. **Résultat attendu :** Les pollings doivent toujours être actifs

### 6. Test de nettoyage automatique

**Objectif :** Vérifier que les pollings expirés sont automatiquement nettoyés.

**Étapes :**
1. Lancer un polling
2. Attendre qu'il se termine (succès ou échec)
3. Vérifier que l'indicateur disparaît
4. **Résultat attendu :** L'indicateur doit disparaître automatiquement

## Tests de régression

### Test de performance

**Objectif :** Vérifier que le système n'impacte pas les performances.

**Étapes :**
1. Lancer de nombreux pollings simultanément
2. Naviguer rapidement entre les vues
3. Recharger la page plusieurs fois
4. **Résultat attendu :** L'application doit rester fluide

### Test de mémoire

**Objectif :** Vérifier qu'il n'y a pas de fuites mémoire.

**Étapes :**
1. Lancer et arrêter de nombreux pollings
2. Naviguer entre les vues
3. Recharger la page
4. **Résultat attendu :** Pas de fuites mémoire détectables

## Tests d'erreur

### Test de localStorage désactivé

**Objectif :** Vérifier que l'application fonctionne même sans localStorage.

**Étapes :**
1. Désactiver le localStorage dans les outils de développement
2. Lancer des pollings
3. Naviguer entre les vues
4. **Résultat attendu :** L'application doit fonctionner, mais sans persistance

### Test de localStorage corrompu

**Objectif :** Vérifier que l'application récupère d'un localStorage corrompu.

**Étapes :**
1. Corrompre manuellement les données dans le localStorage
2. Recharger la page
3. **Résultat attendu :** L'application doit démarrer normalement et nettoyer les données corrompues

## Vérifications dans la console

### Logs à surveiller

```javascript
// Logs de succès
"Polling ajouté: sourceId_qa"
"Statut mis à jour pour sourceId_qa: running"
"État des pollings sauvegardé dans le localStorage"
"État des pollings restauré depuis le localStorage"

// Logs d'erreur (à éviter)
"Erreur lors de la sauvegarde de l'état des pollings"
"Erreur lors du chargement de l'état des pollings"
```

### Commandes de débogage

```javascript
// Dans la console du navigateur
// Vérifier l'état des pollings
console.log('Pollings actifs:', window.pollingStateManager?.activePollings);

// Vérifier le localStorage
console.log('localStorage:', localStorage.getItem('django_rag_polling_state'));

// Nettoyer manuellement
localStorage.removeItem('django_rag_polling_state');
```

## Scénarios de test complexes

### Scénario 1 : Utilisateur impatient

1. Lancer une analyse QA
2. Immédiatement aller voir les détails
3. Revenir à la liste
4. Recharger la page
5. Lancer une autre analyse
6. Changer de collection
7. Revenir et vérifier que tout fonctionne

### Scénario 2 : Multi-tâches

1. Lancer 5 analyses QA simultanément
2. Lancer 3 indexations
3. Naviguer entre les vues
4. Recharger la page
5. Vérifier que tous les pollings sont préservés

### Scénario 3 : Session longue

1. Lancer des pollings
2. Laisser la page ouverte pendant 30+ minutes
3. Vérifier que les pollings expirés sont nettoyés
4. Lancer de nouveaux pollings
5. Vérifier que tout fonctionne normalement

## Critères de succès

- ✅ Les pollings survivent à la navigation
- ✅ Les pollings survivent au rechargement de page
- ✅ L'indicateur affiche correctement les tâches actives
- ✅ L'utilisateur peut arrêter les pollings
- ✅ Pas de fuites mémoire
- ✅ Performance acceptable
- ✅ Gestion d'erreur robuste
- ✅ Nettoyage automatique des pollings expirés

## Problèmes connus et solutions

### Problème : L'indicateur ne disparaît pas
**Solution :** Vérifier que les callbacks `onComplete` sont bien appelés

### Problème : Les pollings ne se restaurent pas
**Solution :** Vérifier que le localStorage n'est pas corrompu et que les timestamps sont valides

### Problème : Performance dégradée
**Solution :** Vérifier qu'il n'y a pas trop de pollings simultanés et que le nettoyage fonctionne

## Support

En cas de problème, vérifier :
1. Les logs dans la console
2. L'état du localStorage
3. Les erreurs réseau
4. La configuration des pollings
