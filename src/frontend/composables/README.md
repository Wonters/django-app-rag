# Composables Vue

Ce dossier contient les composables réutilisables pour l'application Vue.

## useErrorHandler

Composable pour centraliser la gestion d'erreurs, les notifications et les confirmations.

### Installation

```javascript
import { useErrorHandler } from './composables/useErrorHandler.js';
```

### Utilisation

```javascript
const {
  notifications,
  confirmationModal,
  showSuccess,
  showError,
  showWarning,
  showInfo,
  confirmDelete,
  handleApiError,
  logger
} = useErrorHandler();
```

### API

#### Notifications

```javascript
// Notification de succès (disparaît après 3s)
showSuccess('Opération réussie !');

// Notification d'erreur (disparaît après 7s)
showError('Une erreur est survenue', error);

// Notification d'avertissement (disparaît après 5s)
showWarning('Attention !');

// Notification d'information (disparaît après 4s)
showInfo('Information importante');
```

#### Confirmations

```javascript
// Confirmation de suppression simple
confirmDelete('Nom de l\'élément', async () => {
  // Logique de suppression
  await deleteItem();
  showSuccess('Élément supprimé !');
});

// Confirmation personnalisée
showConfirmation({
  title: 'Confirmation',
  message: 'Êtes-vous sûr ?',
  confirmText: 'Oui',
  cancelText: 'Non',
  onConfirm: () => {
    // Action de confirmation
  },
  onCancel: () => {
    // Action d'annulation
  }
});
```

#### Gestion d'erreurs API

```javascript
// Gestion automatique des erreurs HTTP
try {
  const response = await apiCall();
} catch (error) {
  handleApiError(error, 'Message d\'erreur par défaut');
}

// Gestion avec try/catch automatique
const result = await handleAsyncAction(
  () => apiCall(),
  'Message d\'erreur personnalisé'
);
```

#### Logger conditionnel

```javascript
// Logs uniquement en développement
logger.log('Debug info');
logger.warn('Warning message');

// Logs toujours affichés (erreurs)
logger.error('Error message');
```

### Intégration dans un composant

```vue
<template>
  <div>
    <!-- Votre contenu -->
    
    <!-- Notifications toast -->
    <NotificationToast 
      :notifications="notifications"
      @remove="removeNotification"
    />
    
    <!-- Modale de confirmation -->
    <ConfirmationModal 
      :confirmation-modal="confirmationModal"
      @confirm="handleConfirm"
      @cancel="handleCancel"
    />
  </div>
</template>

<script setup>
import { useErrorHandler } from './composables/useErrorHandler.js';
import NotificationToast from './components/NotificationToast.vue';
import ConfirmationModal from './components/ConfirmationModal.vue';

const {
  notifications,
  confirmationModal,
  showSuccess,
  showError,
  confirmDelete,
  removeNotification
} = useErrorHandler();

// Exemple d'utilisation
async function deleteItem(id) {
  confirmDelete('cet élément', async () => {
    try {
      await api.delete(`/items/${id}`);
      showSuccess('Élément supprimé !');
    } catch (error) {
      showError('Erreur lors de la suppression');
    }
  });
}
</script>
```

## useDataTable

Composable pour gérer les tableaux DataTables.

### Utilisation

```javascript
const { tableRef, initDataTable, destroyDataTable } = useDataTable({
  pageLength: 10,
  order: [[0, 'asc']]
});
```

## useTooltips

Composable pour gérer les tooltips Bootstrap.

### Utilisation

```javascript
const { initTooltips, destroyTooltips } = useTooltips();
```

## Migration depuis l'ancien système

### Remplacer alert()

```javascript
// ❌ Ancien
alert('Erreur !');

// ✅ Nouveau
showError('Erreur !');
```

### Remplacer confirm()

```javascript
// ❌ Ancien
if (confirm('Êtes-vous sûr ?')) {
  deleteItem();
}

// ✅ Nouveau
confirmDelete('Nom de l\'élément', () => {
  deleteItem();
});
```

### Remplacer console.log()

```javascript
// ❌ Ancien
console.log('Debug info');

// ✅ Nouveau
logger.log('Debug info'); // Seulement en développement
```

## Avantages

- ✅ **Centralisé** : Toute la gestion d'erreurs au même endroit
- ✅ **Cohérent** : Interface utilisateur uniforme
- ✅ **Maintenable** : Facile à modifier et étendre
- ✅ **Production-ready** : Logs conditionnels et gestion d'erreurs robuste
- ✅ **Accessible** : Notifications et modales accessibles
- ✅ **Responsive** : Fonctionne sur tous les écrans 