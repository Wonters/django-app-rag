<template>
  <div class="mb-4">
    <div class="card">
      <div class="card-header d-flex justify-content-between align-items-center">
        <h5 class="mb-0">{{ $t('Collections') }}</h5>
        <button class="btn btn-success btn-sm" @click="$emit('create')">
          <i class="bi bi-plus-lg"></i> {{ $t('Nouvelle collection') }}
        </button>
      </div>
      <div class="card-body">
        <div class="row">
          <div 
            v-for="collection in collections" 
            :key="collection.id"
            class="col-md-3 col-lg-2 mb-3"
          >
            <div 
              class="card h-100 collection-card"
              :class="{ 'border-primary': selectedCollection && selectedCollection.id === collection.id }"
              @click="$emit('select', collection)"
              style="cursor: pointer; transition: all 0.2s ease;"
            >
              <div class="card-body text-center p-3">
                <div class="mb-2">
                  <i class="bi bi-collection display-6 text-primary"></i>
                </div>
                <h6 class="card-title mb-1 text-truncate" :title="collection.title">
                  {{ collection.title }}
                </h6>
                <small class="text-muted d-block text-truncate" :title="collection.description || $t('Aucune description')">
                  {{ collection.description || $t('Aucune description') }}
                </small>
                <div class="mt-2">
                  <span class="badge bg-primary rounded-pill">{{ collection.sources_count || 0 }}</span>
                </div>
              </div>
              <div class="card-footer p-2 bg-transparent border-top-0">
                <div class="d-flex justify-content-center gap-1">
                  <!-- Bouton d'initialisation -->
                  <button 
                    class="btn btn-outline-primary btn-sm" 
                    @click.stop="initializeCollection(collection)"
                    :disabled="collection.initializationStatus === 'running' || collection.initializationStatus === 'pending'"
                    :class="{
                      'btn-outline-success': collection.initializationStatus === 'completed',
                      'btn-outline-danger': collection.initializationStatus === 'failed' || collection.initializationStatus === 'error' || collection.initializationStatus === 'timeout',
                      'btn-outline-warning': collection.initializationStatus === 'unknown'
                    }"
                    :title="$t('L\'installation va récupérer les données des différentes sources, effectuer des analyse de qualité et formater les données pour pouvoir les exploiter')"
                    data-bs-toggle="tooltip"
                    data-bs-placement="top"
                  >
                    <i v-if="collection.initializationStatus === 'running' || collection.initializationStatus === 'pending'" 
                       class="fas fa-spinner fa-spin"></i>
                    <i v-else-if="collection.initializationStatus === 'completed'" 
                       class="fas fa-check"></i>
                    <i v-else-if="collection.initializationStatus === 'failed' || collection.initializationStatus === 'error'" 
                       class="fas fa-exclamation-triangle"></i>
                    <i v-else-if="collection.initializationStatus === 'timeout'" 
                       class="fas fa-clock"></i>
                    <i v-else-if="collection.initializationStatus === 'unknown'" 
                       class="fas fa-question"></i>
                    <i v-else class="fas fa-play"></i>
                  </button>
                  
                  <button 
                    class="btn btn-outline-secondary btn-sm" 
                    @click.stop="$emit('edit', collection)" 
                    :title="$t('Edit', 1)"
                  >
                    <i class="bi bi-pencil"></i>
                  </button>
                  <button 
                    class="btn btn-outline-danger btn-sm" 
                    @click.stop="$emit('delete', collection.id)" 
                    :title="$t('Delete', 1)"
                  >
                    <i class="bi bi-trash"></i>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Message si aucune collection -->
        <div v-if="collections.length === 0" class="text-center text-muted py-4">
          <i class="bi bi-collection display-1"></i>
          <p class="mt-3">{{ $t('Aucune collection créée') }}</p>
          <button class="btn btn-primary" @click="$emit('create')">
            {{ $t('Créer votre première collection') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue';
import { launchCollectionInitialization } from '../services/tasks.js';
import { usePollingState } from '../composables/usePollingState.js';
import { useErrorHandler } from '../composables/useErrorHandler.js';

const props = defineProps({
  collections: {
    type: Array,
    default: () => []
  },
  selectedCollection: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['select', 'edit', 'delete', 'create']);

// Utilisation du composable de gestion des pollings
const {
  addActivePolling,
  removeActivePolling,
  updatePollingStatus
} = usePollingState();

// Utilisation du composable d'erreur
const { showSuccess, showError, logger } = useErrorHandler();

// Fonction pour initialiser une collection
const initializeCollection = async (collection) => {
  try {
    logger.log('Lancement de l\'initialisation de la collection:', collection.id);
    
    // Mettre à jour le statut de la collection
    collection.initializationStatus = 'pending';
    
    // Ajouter le polling au système de gestion d'état
    const taskId = `collection_init_${collection.id}_${Date.now()}`;
    addActivePolling(collection.id, 'initialization', taskId, {
      maxAttempts: 60,
      interval: 5000,
      timeoutMessage: 'L\'initialisation de la collection prend trop de temps'
    });

    // Lancer la tâche d'initialisation avec la nouvelle signature
    await launchCollectionInitialization(collection.id, {
      onStatusUpdate: (status, data) => {
        logger.log(`Statut d'initialisation mis à jour pour la collection ${collection.id}:`, status);
        collection.initializationStatus = status;
        // Mettre à jour le statut du polling
        updatePollingStatus(collection.id, 'initialization', status);
      },
      onSuccess: (data) => {
        logger.log('Initialisation de la collection terminée avec succès:', data);
        collection.initializationStatus = 'completed';
        // Supprimer le polling du système
        removeActivePolling(collection.id, 'initialization');
        showSuccess('Collection initialisée avec succès !');
      },
      onError: (error, data) => {
        logger.error('Erreur lors de l\'initialisation de la collection:', error);
        collection.initializationStatus = 'failed';
        // Supprimer le polling du système
        removeActivePolling(collection.id, 'initialization');
        showError('Erreur lors de l\'initialisation de la collection');
      },
      onComplete: (finalStatus, data) => {
        logger.log(`Initialisation de la collection ${collection.id} terminée avec le statut:`, finalStatus);
        collection.initializationStatus = finalStatus;
        // S'assurer que le polling est supprimé
        removeActivePolling(collection.id, 'initialization');
      }
    });

  } catch (error) {
    logger.error('Erreur lors du lancement de l\'initialisation:', error);
    collection.initializationStatus = 'failed';
    // Supprimer le polling en cas d'erreur
    removeActivePolling(collection.id, 'initialization');
    showError('Erreur lors du lancement de l\'initialisation');
  }
};

// Initialiser les tooltips Bootstrap
onMounted(() => {
  // Initialiser tous les tooltips
  const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
  tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });
  
  // Initialiser l'état d'initialisation des collections
  initializeCollectionsStatus();
});

// Fonction pour initialiser l'état d'initialisation des collections
const initializeCollectionsStatus = () => {
  props.collections.forEach(collection => {
    if (!collection.hasOwnProperty('initializationStatus')) {
      collection.initializationStatus = 'idle';
    }
  });
};
</script>

<style scoped>
.collection-card {
  border: 2px solid transparent;
  transition: all 0.3s ease;
}

.collection-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border-color: #e9ecef;
}

.collection-card.border-primary {
  border-color: #0d6efd !important;
  box-shadow: 0 0 0 0.2rem rgba(13, 110, 253, 0.25);
}

.collection-card .card-body {
  min-height: 120px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.collection-card .card-title {
  font-size: 0.9rem;
  font-weight: 600;
  line-height: 1.2;
}

.collection-card .text-muted {
  font-size: 0.75rem;
  line-height: 1.2;
}

.collection-card .badge {
  font-size: 0.7rem;
}

.collection-card .btn-sm {
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .col-md-3.col-lg-2 {
    flex: 0 0 50%;
    max-width: 50%;
  }
}

@media (max-width: 576px) {
  .col-md-3.col-lg-2 {
    flex: 0 0 100%;
    max-width: 100%;
  }
}
</style> 