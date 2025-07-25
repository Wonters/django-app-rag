import { ref } from 'vue';
import { useI18n } from 'vue-i18n';

export function useErrorHandler() {
  const { t } = useI18n();
  
  // État pour les notifications
  const notifications = ref([]);
  const confirmationModal = ref({
    show: false,
    title: '',
    message: '',
    confirmText: '',
    cancelText: '',
    onConfirm: null,
    onCancel: null
  });

  // Configuration
  const isDev = process.env.NODE_ENV === 'development';
  
  // Logger conditionnel
  const logger = {
    log: (...args) => isDev && console.log(...args),
    warn: (...args) => isDev && console.warn(...args),
    error: (...args) => console.error(...args) // Toujours log les erreurs
  };

  /**
   * Afficher une notification toast
   */
  function showNotification(message, type = 'info', duration = 5000) {
    const id = Date.now();
    const notification = {
      id,
      message,
      type, // 'success', 'error', 'warning', 'info'
      show: true
    };
    
    notifications.value.push(notification);
    
    // Auto-remove après la durée spécifiée
    setTimeout(() => {
      removeNotification(id);
    }, duration);
    
    return id;
  }

  /**
   * Supprimer une notification
   */
  function removeNotification(id) {
    const index = notifications.value.findIndex(n => n.id === id);
    if (index > -1) {
      notifications.value.splice(index, 1);
    }
  }

  /**
   * Afficher une notification de succès
   */
  function showSuccess(message, duration = 3000) {
    return showNotification(message, 'success', duration);
  }

  /**
   * Afficher une notification d'erreur
   */
  function showError(message, error = null, duration = 7000) {
    logger.error(message, error);
    return showNotification(message, 'error', duration);
  }

  /**
   * Afficher une notification d'avertissement
   */
  function showWarning(message, duration = 5000) {
    return showNotification(message, 'warning', duration);
  }

  /**
   * Afficher une notification d'information
   */
  function showInfo(message, duration = 4000) {
    return showNotification(message, 'info', duration);
  }

  /**
   * Afficher une modale de confirmation
   */
  function showConfirmation(options) {
    const {
      title = t('Confirmation'),
      message,
      confirmText = t('Confirmer'),
      cancelText = t('Annuler'),
      onConfirm,
      onCancel
    } = options;

    confirmationModal.value = {
      show: true,
      title,
      message,
      confirmText,
      cancelText,
      onConfirm: () => {
        confirmationModal.value.show = false;
        if (onConfirm) onConfirm();
      },
      onCancel: () => {
        confirmationModal.value.show = false;
        if (onCancel) onCancel();
      }
    };
  }

  /**
   * Gérer une erreur d'API
   */
  function handleApiError(error, defaultMessage = null) {
    let message = defaultMessage || t('Une erreur est survenue');
    
    if (error.response) {
      // Erreur HTTP avec réponse
      const status = error.response.status;
      const data = error.response.data;
      
      switch (status) {
        case 400:
          message = data?.message || t('Données invalides');
          break;
        case 401:
          message = t('Non autorisé');
          break;
        case 403:
          message = t('Accès interdit');
          break;
        case 404:
          message = t('Ressource non trouvée');
          break;
        case 422:
          message = data?.message || t('Données invalides');
          break;
        case 500:
          message = t('Erreur serveur');
          break;
        default:
          message = data?.message || t('Erreur serveur');
      }
    } else if (error.request) {
      // Erreur réseau
      message = t('Erreur de connexion');
    } else {
      // Autre erreur
      message = error.message || message;
    }
    
    showError(message, error);
    return message;
  }

  /**
   * Confirmation de suppression
   */
  function confirmDelete(itemName, onConfirm) {
    showConfirmation({
      title: t('Confirmer la suppression'),
      message: t('Êtes-vous sûr de vouloir supprimer') + ` "${itemName}" ?`,
      confirmText: t('Supprimer'),
      cancelText: t('Annuler'),
      onConfirm
    });
  }

  /**
   * Gérer une action avec try/catch automatique
   */
  async function handleAsyncAction(action, errorMessage = null) {
    try {
      return await action();
    } catch (error) {
      handleApiError(error, errorMessage);
      throw error; // Re-throw pour permettre la gestion locale si nécessaire
    }
  }

  return {
    // État
    notifications,
    confirmationModal,
    
    // Méthodes de notification
    showNotification,
    removeNotification,
    showSuccess,
    showError,
    showWarning,
    showInfo,
    
    // Méthodes de confirmation
    showConfirmation,
    confirmDelete,
    
    // Gestion d'erreurs
    handleApiError,
    handleAsyncAction,
    
    // Logger
    logger
  };
} 