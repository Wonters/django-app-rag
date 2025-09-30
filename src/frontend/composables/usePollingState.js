import { ref, reactive, computed, watch } from 'vue';
import { logger } from './useErrorHandler.js';
import { usePollingPersistence } from './usePollingPersistence.js';

/**
 * Store global pour gérer l'état des pollings
 * Permet de persister les pollings en cours lors de la navigation
 */
class PollingStateManager {
  constructor() {
    // Map des pollings actifs par source ID
    this.activePollings = reactive(new Map());
    
    // Map des statuts des sources par collection
    this.sourceStatuses = reactive(new Map());
    
    // Map des timers de polling
    this.pollingTimers = new Map();
    
    // Configuration par défaut
    this.defaultConfig = {
      maxAttempts: 60,
      interval: 5000,
      timeoutMessage: 'La tâche prend trop de temps'
    };

    // Initialiser la persistance
    this.persistence = usePollingPersistence();
    this.initializeFromStorage();
    this.setupAutoSave();
  }

  /**
   * Ajouter un polling actif
   * @param {string} sourceId - ID de la source
   * @param {string} taskType - Type de tâche ('qa' ou 'indexing')
   * @param {string} taskId - ID de la tâche
   * @param {Object} config - Configuration du polling
   */
  addActivePolling(sourceId, taskType, taskId, config = {}) {
    const key = `${sourceId}_${taskType}`;
    const pollingConfig = { ...this.defaultConfig, ...config };
    
    this.activePollings.set(key, {
      sourceId,
      taskType,
      taskId,
      config: pollingConfig,
      startTime: Date.now(),
      attempts: 0,
      status: 'pending'
    });
    
    logger.log(`Polling ajouté: ${key}`, { taskId, config: pollingConfig });
  }

  /**
   * Supprimer un polling actif
   * @param {string} sourceId - ID de la source
   * @param {string} taskType - Type de tâche
   */
  removeActivePolling(sourceId, taskType) {
    const key = `${sourceId}_${taskType}`;
    const polling = this.activePollings.get(key);
    
    if (polling) {
      // Nettoyer le timer s'il existe
      const timerKey = `${sourceId}_${taskType}`;
      if (this.pollingTimers.has(timerKey)) {
        clearTimeout(this.pollingTimers.get(timerKey));
        this.pollingTimers.delete(timerKey);
      }
      
      this.activePollings.delete(key);
      logger.log(`Polling supprimé: ${key}`);
    }
  }

  /**
   * Mettre à jour le statut d'un polling
   * @param {string} sourceId - ID de la source
   * @param {string} taskType - Type de tâche
   * @param {string} status - Nouveau statut
   */
  updatePollingStatus(sourceId, taskType, status) {
    const key = `${sourceId}_${taskType}`;
    const polling = this.activePollings.get(key);
    
    if (polling) {
      polling.status = status;
      polling.lastUpdate = Date.now();
      
      // Mettre à jour le statut de la source
      this.updateSourceStatus(sourceId, taskType, status);
      
      logger.log(`Statut mis à jour pour ${key}: ${status}`);
    }
  }

  /**
   * Mettre à jour le statut d'une source
   * @param {string} sourceId - ID de la source
   * @param {string} taskType - Type de tâche
   * @param {string} status - Nouveau statut
   */
  updateSourceStatus(sourceId, taskType, status) {
    if (!this.sourceStatuses.has(sourceId)) {
      this.sourceStatuses.set(sourceId, {
        qa_status: null,
        indexing_status: null,
        lastUpdate: Date.now()
      });
    }
    
    const sourceStatus = this.sourceStatuses.get(sourceId);
    sourceStatus[`${taskType}_status`] = status;
    sourceStatus.lastUpdate = Date.now();
    
    logger.log(`Statut de source mis à jour: ${sourceId}.${taskType}_status = ${status}`);
  }

  /**
   * Obtenir le statut d'une source
   * @param {string} sourceId - ID de la source
   * @param {string} taskType - Type de tâche
   * @returns {string|null} - Statut de la source
   */
  getSourceStatus(sourceId, taskType) {
    const sourceStatus = this.sourceStatuses.get(sourceId);
    return sourceStatus ? sourceStatus[`${taskType}_status`] : null;
  }

  /**
   * Obtenir tous les pollings actifs
   * @returns {Array} - Liste des pollings actifs
   */
  getActivePollings() {
    return Array.from(this.activePollings.values());
  }

  /**
   * Vérifier si une source a un polling actif
   * @param {string} sourceId - ID de la source
   * @param {string} taskType - Type de tâche
   * @returns {boolean} - True si un polling est actif
   */
  hasActivePolling(sourceId, taskType) {
    const key = `${sourceId}_${taskType}`;
    return this.activePollings.has(key);
  }

  /**
   * Obtenir les statuts de toutes les sources d'une collection
   * @param {number} collectionId - ID de la collection
   * @returns {Object} - Map des statuts par source ID
   */
  getCollectionSourceStatuses(collectionId) {
    const statuses = {};
    for (const [sourceId, sourceStatus] of this.sourceStatuses.entries()) {
      // Ici on pourrait filtrer par collection si nécessaire
      statuses[sourceId] = sourceStatus;
    }
    return statuses;
  }

  /**
   * Nettoyer les pollings expirés
   * @param {number} maxAge - Âge maximum en millisecondes (défaut: 30 minutes)
   */
  cleanupExpiredPollings(maxAge = 30 * 60 * 1000) {
    const now = Date.now();
    const expiredKeys = [];
    
    for (const [key, polling] of this.activePollings.entries()) {
      if (now - polling.startTime > maxAge) {
        expiredKeys.push(key);
      }
    }
    
    expiredKeys.forEach(key => {
      const polling = this.activePollings.get(key);
      if (polling) {
        this.removeActivePolling(polling.sourceId, polling.taskType);
        logger.log(`Polling expiré supprimé: ${key}`);
      }
    });
  }

  /**
   * Nettoyer tous les pollings
   */
  clearAllPollings() {
    // Nettoyer tous les timers
    for (const timer of this.pollingTimers.values()) {
      clearTimeout(timer);
    }
    this.pollingTimers.clear();
    
    // Nettoyer les pollings actifs
    this.activePollings.clear();
    
    logger.log('Tous les pollings ont été nettoyés');
  }

  /**
   * Restaurer les statuts des sources depuis les données
   * @param {Array} sources - Liste des sources avec leurs statuts
   */
  restoreSourceStatuses(sources) {
    sources.forEach(source => {
      if (source.id) {
        this.sourceStatuses.set(source.id, {
          qa_status: source.qa_status || null,
          indexing_status: source.indexing_status || null,
          lastUpdate: Date.now()
        });
      }
    });
    
    logger.log(`Statuts restaurés pour ${sources.length} sources`);
  }

  /**
   * Appliquer les statuts sauvegardés aux sources
   * @param {Array} sources - Liste des sources à mettre à jour
   * @returns {Array} - Sources avec les statuts mis à jour
   */
  applySourceStatuses(sources) {
    return sources.map(source => {
      const savedStatus = this.sourceStatuses.get(source.id);
      if (savedStatus) {
        return {
          ...source,
          qa_status: savedStatus.qa_status || source.qa_status,
          indexing_status: savedStatus.indexing_status || source.indexing_status
        };
      }
      return source;
    });
  }

  /**
   * Initialiser l'état depuis le localStorage
   */
  initializeFromStorage() {
    const savedState = this.persistence.loadPollingState();
    if (savedState) {
      // Restaurer les pollings actifs
      for (const [key, polling] of savedState.activePollings) {
        this.activePollings.set(key, polling);
      }
      
      // Restaurer les statuts des sources
      for (const [sourceId, status] of savedState.sourceStatuses) {
        this.sourceStatuses.set(sourceId, status);
      }
      
      logger.log('État des pollings restauré depuis le localStorage');
    }
  }

  /**
   * Configurer la sauvegarde automatique
   */
  setupAutoSave() {
    // Sauvegarder automatiquement quand l'état change
    watch(
      [this.activePollings, this.sourceStatuses],
      () => {
        this.saveToStorage();
      },
      { deep: true }
    );
  }

  /**
   * Sauvegarder l'état dans le localStorage
   */
  saveToStorage() {
    this.persistence.savePollingState({
      activePollings: this.activePollings,
      sourceStatuses: this.sourceStatuses
    });
  }

  /**
   * Nettoyer l'état du localStorage
   */
  clearStorage() {
    this.persistence.clearPollingState();
  }
}

// Instance globale du gestionnaire d'état
const pollingStateManager = new PollingStateManager();

/**
 * Composable pour utiliser le gestionnaire d'état des pollings
 * @returns {Object} - Interface du gestionnaire d'état
 */
export function usePollingState() {
  return {
    // Gestion des pollings actifs
    addActivePolling: (sourceId, taskType, taskId, config) => 
      pollingStateManager.addActivePolling(sourceId, taskType, taskId, config),
    
    removeActivePolling: (sourceId, taskType) => 
      pollingStateManager.removeActivePolling(sourceId, taskType),
    
    updatePollingStatus: (sourceId, taskType, status) => 
      pollingStateManager.updatePollingStatus(sourceId, taskType, status),
    
    hasActivePolling: (sourceId, taskType) => 
      pollingStateManager.hasActivePolling(sourceId, taskType),
    
    getActivePollings: () => 
      pollingStateManager.getActivePollings(),
    
    // Gestion des statuts des sources
    updateSourceStatus: (sourceId, taskType, status) => 
      pollingStateManager.updateSourceStatus(sourceId, taskType, status),
    
    getSourceStatus: (sourceId, taskType) => 
      pollingStateManager.getSourceStatus(sourceId, taskType),
    
    getCollectionSourceStatuses: (collectionId) => 
      pollingStateManager.getCollectionSourceStatuses(collectionId),
    
    // Utilitaires
    restoreSourceStatuses: (sources) => 
      pollingStateManager.restoreSourceStatuses(sources),
    
    applySourceStatuses: (sources) => 
      pollingStateManager.applySourceStatuses(sources),
    
    cleanupExpiredPollings: (maxAge) => 
      pollingStateManager.cleanupExpiredPollings(maxAge),
    
    clearAllPollings: () => 
      pollingStateManager.clearAllPollings(),
    
    // Persistance
    saveToStorage: () => 
      pollingStateManager.saveToStorage(),
    
    clearStorage: () => 
      pollingStateManager.clearStorage(),
    
    // État réactif
    activePollings: computed(() => pollingStateManager.activePollings),
    sourceStatuses: computed(() => pollingStateManager.sourceStatuses)
  };
}

export default usePollingState;
