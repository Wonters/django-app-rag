import { ref, watch } from 'vue';
import { logger } from './useErrorHandler.js';

/**
 * Composable pour gérer la persistance des pollings dans le localStorage
 * Permet de sauvegarder et restaurer l'état des pollings lors du rechargement de la page
 */
export function usePollingPersistence() {
  const STORAGE_KEY = 'django_rag_polling_state';
  const MAX_STORAGE_AGE = 30 * 60 * 1000; // 30 minutes

  /**
   * Sauvegarder l'état des pollings dans le localStorage
   * @param {Object} pollingState - État des pollings à sauvegarder
   */
  function savePollingState(pollingState) {
    try {
      const stateToSave = {
        timestamp: Date.now(),
        activePollings: Array.from(pollingState.activePollings.entries()),
        sourceStatuses: Array.from(pollingState.sourceStatuses.entries())
      };
      
      localStorage.setItem(STORAGE_KEY, JSON.stringify(stateToSave));
      logger.log('État des pollings sauvegardé dans le localStorage');
    } catch (error) {
      logger.error('Erreur lors de la sauvegarde de l\'état des pollings:', error);
    }
  }

  /**
   * Charger l'état des pollings depuis le localStorage
   * @returns {Object|null} - État des pollings ou null si non trouvé/expiré
   */
  function loadPollingState() {
    try {
      const savedState = localStorage.getItem(STORAGE_KEY);
      if (!savedState) {
        logger.log('Aucun état de polling sauvegardé trouvé');
        return null;
      }

      const parsedState = JSON.parse(savedState);
      
      // Vérifier si l'état n'est pas trop ancien
      if (Date.now() - parsedState.timestamp > MAX_STORAGE_AGE) {
        logger.log('État des pollings expiré, suppression du localStorage');
        localStorage.removeItem(STORAGE_KEY);
        return null;
      }

      // Reconstruire les Maps
      const restoredState = {
        activePollings: new Map(parsedState.activePollings),
        sourceStatuses: new Map(parsedState.sourceStatuses)
      };

      logger.log('État des pollings restauré depuis le localStorage');
      return restoredState;
    } catch (error) {
      logger.error('Erreur lors du chargement de l\'état des pollings:', error);
      // En cas d'erreur, nettoyer le localStorage
      localStorage.removeItem(STORAGE_KEY);
      return null;
    }
  }

  /**
   * Nettoyer l'état des pollings du localStorage
   */
  function clearPollingState() {
    try {
      localStorage.removeItem(STORAGE_KEY);
      logger.log('État des pollings supprimé du localStorage');
    } catch (error) {
      logger.error('Erreur lors de la suppression de l\'état des pollings:', error);
    }
  }

  /**
   * Vérifier si un état de polling est sauvegardé
   * @returns {boolean} - True si un état est sauvegardé et valide
   */
  function hasValidPollingState() {
    try {
      const savedState = localStorage.getItem(STORAGE_KEY);
      if (!savedState) return false;

      const parsedState = JSON.parse(savedState);
      return Date.now() - parsedState.timestamp <= MAX_STORAGE_AGE;
    } catch (error) {
      return false;
    }
  }

  /**
   * Obtenir des informations sur l'état sauvegardé
   * @returns {Object|null} - Informations sur l'état sauvegardé
   */
  function getPollingStateInfo() {
    try {
      const savedState = localStorage.getItem(STORAGE_KEY);
      if (!savedState) return null;

      const parsedState = JSON.parse(savedState);
      const age = Date.now() - parsedState.timestamp;
      
      return {
        timestamp: parsedState.timestamp,
        age: age,
        isExpired: age > MAX_STORAGE_AGE,
        activePollingsCount: parsedState.activePollings.length,
        sourceStatusesCount: parsedState.sourceStatuses.length
      };
    } catch (error) {
      return null;
    }
  }

  return {
    savePollingState,
    loadPollingState,
    clearPollingState,
    hasValidPollingState,
    getPollingStateInfo
  };
}

export default usePollingPersistence;
