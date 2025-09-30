<template>
  <div v-if="hasActivePollings" class="polling-status-indicator">
    <div class="alert alert-info d-flex align-items-center" role="alert">
      <div class="spinner-border spinner-border-sm me-2" role="status">
        <span class="visually-hidden">{{ $t('Chargement...') }}</span>
      </div>
      <div class="flex-grow-1">
        <strong>{{ $t('Tâches en cours') }}:</strong>
        <span class="ms-1">{{ activePollingsCount }} {{ $t('tâche(s) en cours') }}</span>
      </div>
      <button 
        class="btn btn-sm btn-outline-secondary" 
        @click="showDetails = !showDetails"
        :title="$t('Voir les détails')"
      >
        <i class="bi" :class="showDetails ? 'bi-chevron-up' : 'bi-chevron-down'"></i>
      </button>
    </div>

    <!-- Détails des pollings actifs -->
    <div v-if="showDetails" class="polling-details mt-2">
      <div class="card">
        <div class="card-header d-flex justify-content-between align-items-center">
          <h6 class="mb-0">{{ $t('Détails des tâches en cours') }}</h6>
          <button 
            class="btn btn-sm btn-outline-danger" 
            @click="clearAllPollings"
            :title="$t('Arrêter toutes les tâches')"
          >
            <i class="bi bi-stop-circle"></i> {{ $t('Arrêter tout') }}
          </button>
        </div>
        <div class="card-body">
          <div v-if="activePollingsList.length === 0" class="text-muted text-center py-2">
            {{ $t('Aucune tâche en cours') }}
          </div>
          <div v-else>
            <div 
              v-for="polling in activePollingsList" 
              :key="`${polling.sourceId}_${polling.taskType}`"
              class="polling-item d-flex justify-content-between align-items-center mb-2 p-2 border rounded"
            >
              <div class="polling-info">
                <div class="fw-bold">
                  {{ $t('Source') }} {{ polling.sourceId }} - {{ getTaskTypeLabel(polling.taskType) }}
                </div>
                <div class="text-muted small">
                  {{ $t('Statut') }}: 
                  <span class="badge" :class="getStatusBadgeClass(polling.status)">
                    {{ getStatusLabel(polling.status) }}
                  </span>
                </div>
                <div class="text-muted small">
                  {{ $t('Démarré il y a') }}: {{ formatDuration(Date.now() - polling.startTime) }}
                </div>
              </div>
              <div class="polling-actions">
                <button 
                  class="btn btn-sm btn-outline-danger" 
                  @click="stopPolling(polling.sourceId, polling.taskType)"
                  :title="$t('Arrêter cette tâche')"
                >
                  <i class="bi bi-stop-circle"></i>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { usePollingState } from '../composables/usePollingState.js';
import { useErrorHandler } from '../composables/useErrorHandler.js';

const { t } = useI18n();
const { logger, showSuccess, showError } = useErrorHandler();

const {
  activePollings,
  removeActivePolling,
  clearAllPollings: clearAllPollingsState
} = usePollingState();

const showDetails = ref(false);

// Computed properties
const hasActivePollings = computed(() => {
  return activePollings.value.size > 0;
});

const activePollingsCount = computed(() => {
  return activePollings.value.size;
});

const activePollingsList = computed(() => {
  return Array.from(activePollings.value.values());
});

// Fonctions utilitaires
function getTaskTypeLabel(taskType) {
  switch (taskType) {
    case 'qa':
      return t('Analyse QA');
    case 'indexing':
      return t('Indexation');
    case 'initialization':
      return t('Initialisation');
    default:
      return taskType;
  }
}

function getStatusLabel(status) {
  switch (status) {
    case 'pending':
      return t('En attente');
    case 'running':
      return t('En cours');
    case 'completed':
      return t('Terminé');
    case 'failed':
      return t('Échoué');
    default:
      return status;
  }
}

function getStatusBadgeClass(status) {
  switch (status) {
    case 'pending':
      return 'bg-warning';
    case 'running':
      return 'bg-info';
    case 'completed':
      return 'bg-success';
    case 'failed':
      return 'bg-danger';
    default:
      return 'bg-secondary';
  }
}

function formatDuration(milliseconds) {
  const seconds = Math.floor(milliseconds / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);

  if (hours > 0) {
    return `${hours}h ${minutes % 60}m`;
  } else if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`;
  } else {
    return `${seconds}s`;
  }
}

// Fonctions d'action
function stopPolling(sourceId, taskType) {
  try {
    removeActivePolling(sourceId, taskType);
    showSuccess(t('Tâche arrêtée avec succès'));
    logger.log(`Polling arrêté pour la source ${sourceId}, type ${taskType}`);
  } catch (error) {
    logger.error('Erreur lors de l\'arrêt du polling:', error);
    showError(t('Erreur lors de l\'arrêt de la tâche'));
  }
}

function clearAllPollings() {
  try {
    clearAllPollingsState();
    showDetails.value = false;
    showSuccess(t('Toutes les tâches ont été arrêtées'));
    logger.log('Tous les pollings ont été arrêtés');
  } catch (error) {
    logger.error('Erreur lors de l\'arrêt de tous les pollings:', error);
    showError(t('Erreur lors de l\'arrêt des tâches'));
  }
}
</script>

<style scoped>
.polling-status-indicator {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 1050;
  max-width: 400px;
  min-width: 300px;
}

.polling-details {
  max-height: 400px;
  overflow-y: auto;
}

.polling-item {
  background-color: #f8f9fa;
  transition: background-color 0.2s;
}

.polling-item:hover {
  background-color: #e9ecef;
}

.polling-info {
  flex-grow: 1;
}

.polling-actions {
  flex-shrink: 0;
}

/* Animation pour le spinner */
.spinner-border-sm {
  width: 1rem;
  height: 1rem;
}

/* Responsive */
@media (max-width: 768px) {
  .polling-status-indicator {
    position: relative;
    top: auto;
    right: auto;
    max-width: 100%;
    margin-bottom: 1rem;
  }
}
</style>
