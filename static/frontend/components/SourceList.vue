<template>
  <div>
    <!-- Vue principale (liste des documents) -->
    <div>
      <div class="mb-3 text-end">
        <button class="btn btn-success" @click="showUpload = true">
          <i class="bi bi-plus-lg"></i> {{ $t('Ajouter un document') }}
        </button>
      </div>
      
      <!-- Formulaire d'ajout -->
      <SourceForm :show="showUpload" :form-url="sourceFormUrl" @close="closeUploadForm" @success="handleSourceSuccess" />
      
      <!-- Formulaire d'édition -->
      <SourceForm :show="showEdit" :form-url="editFormUrl" @close="closeEditForm" @success="handleSourceSuccess" />
      
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
      
      <!-- Tableau des documents -->
      <div class="table-responsive">
        <table class="table table-striped table-hover">
          <thead class="table-dark">
            <tr>
              <th>{{ $t('ID', 2) }}</th>
              <th>{{ $t('Source name', 2) }}</th>
              <th>{{ $t('Type', 2) }}</th>
              <th>{{ $t('Questions', 2) }}</th>
              <th>{{ $t('Answers', 2) }}</th>
              <th>{{ $t('Actions', 2) }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="source in sources" :key="source.id">
              <td>{{ source.id }}</td>
              <td>
                <a :href="source.link" target="_blank" class="text-decoration-none">{{ source.title }}</a>
              </td>
              <td>
                <span class="badge bg-secondary">{{ source.type }}</span>
              </td>
              <td>
                <span class="badge bg-primary">{{ source.questions_count || 0 }}</span>
              </td>
              <td>
                <span class="badge bg-success">{{ source.answers_count || 0 }}</span>
              </td>
              <td>
                <div class="btn-group" role="group">
                  <button class="btn btn-outline-danger btn-sm" @click="deleteSource(source.id)" :title="$t('Delete')">
                    <i class="bi bi-trash"></i>
                  </button>
                  <button class="btn btn-outline-primary btn-sm" @click="editSource(source.id)" :title="$t('Edit')">
                    <i class="bi bi-pencil"></i>
                  </button>
                  <button class="btn btn-outline-info btn-sm" @click="viewSourceDetails(source)" :title="$t('Voir détails')">
                    <i class="bi bi-eye"></i>
                  </button>
                  <button 
                    class="btn btn-sm" 
                    :class="{
                      'btn-outline-success': !source.qa_status || source.qa_status === 'completed',
                      'btn-outline-warning': source.qa_status === 'failed',
                      'btn-outline-info': source.qa_status === 'pending',
                      'btn-success': source.qa_status === 'running'
                    }"
                    @click="handleQAAnalysis(source)" 
                    :title="getQATooltip(source.qa_status)"
                    :disabled="source.qa_status === 'running' || source.qa_status === 'pending'"
                    data-bs-toggle="tooltip"
                    data-bs-placement="top"
                  >
                    <!-- Spinner pour running -->
                    <span v-if="source.qa_status === 'running'" class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                    
                    <!-- Icône pour pending -->
                    <i v-else-if="source.qa_status === 'pending'" class="bi bi-clock"></i>
                    
                    <!-- Icône warning pour failed -->
                    <i v-else-if="source.qa_status === 'failed'" class="bi bi-exclamation-triangle"></i>
                    
                    <!-- Icône robot pour completed ou pas de statut -->
                    <i v-else class="bi bi-robot"></i>
                  </button>
                  
                  <!-- Bouton d'indexation de la source -->
                  <button 
                    class="btn btn-sm" 
                    :class="{
                      'btn-outline-secondary': !source.indexing_status || source.indexing_status === 'completed',
                      'btn-outline-warning': source.indexing_status === 'failed',
                      'btn-outline-info': source.indexing_status === 'pending',
                      'btn-secondary': source.indexing_status === 'running'
                    }"
                    @click="handleSourceIndexing(source)" 
                    :title="getIndexingTooltip(source.indexing_status)"
                    :disabled="source.indexing_status === 'running' || source.indexing_status === 'pending'"
                    data-bs-toggle="tooltip"
                    data-bs-placement="top"
                  >
                    <!-- Spinner pour running -->
                    <span v-if="source.indexing_status === 'running'" class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                    
                    <!-- Icône pour pending -->
                    <i v-else-if="source.indexing_status === 'pending'" class="bi bi-clock"></i>
                    
                    <!-- Icône warning pour failed -->
                    <i v-else-if="source.indexing_status === 'failed'" class="bi bi-exclamation-triangle"></i>
                    
                    <!-- Icône database pour completed ou pas de statut -->
                    <i v-else class="bi bi-database"></i>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        
        <!-- Message si aucun document -->
        <div v-if="sources.length === 0" class="text-center text-muted py-5">
          <i class="bi bi-file-text display-1"></i>
          <p class="mt-3">{{ $t('Aucun document dans cette collection') }}</p>
          <button class="btn btn-primary" @click="showUpload = true">
            {{ $t('Ajouter le premier document') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed, nextTick } from 'vue';
import { useI18n } from 'vue-i18n';
import SourceForm from './SourceForm.vue';
import NotificationToast from './NotificationToast.vue';
import ConfirmationModal from './ConfirmationModal.vue';
import apiService from '../services/apiService.js';
import { launchQAAnalysis } from '../services/tasks.js';
import { useErrorHandler } from '../composables/useErrorHandler.js';
import { useTooltips } from '../composables/useTooltips';
import { SOURCE_API_URL, SOURCE_FORM_URL, SOURCE_EDIT_URL, QA_API_URL } from '../config/api.js';

const { t } = useI18n();

// Utilisation du composable d'erreur
const {
  notifications,
  confirmationModal,
  showSuccess,
  showError,
  showWarning,
  showInfo,
  confirmDelete,
  handleApiError,
  removeNotification,
  logger
} = useErrorHandler();

// Utilisation du composable de tooltips
const { initTooltips, destroyTooltips } = useTooltips();

// Props
const props = defineProps({
  collectionId: {
    type: Number,
    required: false,
    default: null
  },
  selectedCollection: {
    type: Object,
    required: false,
    default: null
  }
});

const emit = defineEmits(['refresh', 'view-details']);

// Gestionnaires d'événements pour les composants UI
function handleConfirm() {
  // Cette fonction sera appelée par la modale de confirmation
  // La logique spécifique est gérée dans les callbacks de confirmDelete
}

function handleCancel() {
  // Cette fonction sera appelée quand l'utilisateur annule une confirmation
  // Pas d'action nécessaire ici
}

// État local simplifié
const sources = ref([]);
const showUpload = ref(false);
const showEdit = ref(false);
const editFormUrl = ref('');

// URLs depuis la configuration centralisée
const sourceFormUrl = computed(() => {
  let url = SOURCE_FORM_URL;
  if (props.collectionId) {
    const separator = url.includes('?') ? '&' : '?';
    url += `${separator}collection=${props.collectionId}`;
  }
  return url;
});

// Fonctions simplifiées
async function fetchSources() {
  try {
    let url = SOURCE_API_URL;
    
    if (props.collectionId) {
      url += `?collection=${props.collectionId}`;
    }
    
    const response = await apiService.get(url);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    sources.value = Array.isArray(data) ? data : (data.results || []);
    
    logger.log('Sources fetched successfully:', sources.value.length);
  } catch (error) {
    logger.error('Erreur lors du chargement des sources:', error);
    showError(t('Erreur lors du chargement des sources'));
    sources.value = [];
  }
}

// Fonction pour rafraîchir les données et réinitialiser les tooltips
async function refreshDataAndTooltips() {
  try {
    // Détruire les tooltips existants
    destroyTooltips();
    
    await fetchSources();
    
    // Réinitialiser les tooltips après le rechargement
    await nextTick();
    initTooltips();
  } catch (error) {
    logger.error('Erreur lors du rafraîchissement des données et tooltips:', error);
  }
}

// Fonction pour rafraîchir le statut d'indexation d'une source
async function refreshSourceIndexingStatus(source) {
  try {
    // Utiliser l'API des sources existante pour récupérer les données mises à jour
    const response = await fetch(`/rag_app/api/sources/${source.id}/`);
    
    if (response.ok) {
      const result = await response.json();
      const sourceIndex = sources.value.findIndex(s => s.id === source.id);
      if (sourceIndex !== -1) {
        // Mettre à jour le statut d'indexation
        sources.value[sourceIndex].indexing_status = result.indexing_status;
        logger.log(`Statut d'indexation mis à jour pour la source ${source.id}: ${result.indexing_status}`);
      }
    }
  } catch (error) {
    logger.error('Erreur lors de la vérification du statut d\'indexation:', error);
  }
}

function closeUploadForm() {
  showUpload.value = false;
}

function closeEditForm() {
  showEdit.value = false;
}

async function handleSourceSuccess() {
  try {
    logger.log('Source added/updated successfully, reloading data...');
    
    // Fermer les popups
    showUpload.value = false;
    showEdit.value = false;
    
    // Rafraîchir les données et tooltips
    await refreshDataAndTooltips();
    
    // Émettre un événement pour notifier le parent
    emit('refresh');
    
    // Afficher un message de succès
    showSuccess(t('Document ajouté/modifié avec succès'));
    
  } catch (error) {
    logger.error('Error in handleSourceSuccess:', error);
    showError(t('Erreur lors de la mise à jour des données'));
  }
}

function editSource(id) {
  try {
    editFormUrl.value = SOURCE_EDIT_URL.replace('__pk__', id);
    showEdit.value = true;
  } catch (error) {
    logger.error('Error in editSource:', error);
    showError(t('Erreur lors de l\'ouverture du formulaire d\'édition'));
  }
}

function deleteSource(id) {
  const source = sources.value.find(s => s.id === id);
  const sourceName = source?.title || 'ce document';
  
  confirmDelete(sourceName, async () => {
    try {
      const response = await apiService.deleteWithCsrfFetch(`${SOURCE_API_URL}${id}/`);
      
      if (response.ok) {
        await fetchSources();
        showSuccess(t('Document supprimé avec succès'));
      } else {
        showError(t('Erreur lors de la suppression du document'));
      }
    } catch (error) {
      handleApiError(error, t('Erreur lors de la suppression du document'));
    }
  });
}

function viewSourceDetails(source) {
  try {
    logger.log('Emitting view-details event for source:', source.id);
    emit('view-details', source);
  } catch (error) {
    logger.error('Error emitting view-details event:', error);
    showError(t('Erreur lors de l\'ouverture des détails'));
  }
}

function getQATooltip(qaStatus) {
  switch (qaStatus) {
    case 'running':
      return t('Analyse en cours... Veuillez patienter');
    case 'pending':
      return t('Tâche en attente de traitement dans la file d\'attente');
    case 'failed':
      return t('Analyse échouée - Cliquez pour relancer l\'analyse');
    case 'completed':
      return t('Analyse terminée avec succès - Cliquez pour relancer si nécessaire');
    default:
      return t('Lancer l\'analyse avec IA pour cette source');
  }
}

function getIndexingTooltip(indexingStatus) {
  switch (indexingStatus) {
    case 'running':
      return t('Indexation en cours... Veuillez patienter');
    case 'pending':
      return t('Tâche d\'indexation en attente de traitement');
    case 'failed':
      return t('Indexation échouée - Cliquez pour relancer l\'indexation');
    case 'completed':
      return t('Source déjà indexée - Cliquez pour réindexer si nécessaire');
    default:
      return t('Indexer cette source dans la base de connaissances');
  }
}

async function handleQAAnalysis(source) {
  try {
    logger.log('Lancement de l\'analyse QA pour la source:', source.id);
    
    // Fonction utilitaire pour mettre à jour le statut de la source
    const updateSourceStatus = (status) => {
      const sourceIndex = sources.value.findIndex(s => s.id === source.id);
      if (sourceIndex !== -1) {
        sources.value[sourceIndex].qa_status = status;
        logger.log(`Statut mis à jour pour la source ${source.id}: ${status}`);
      }
    };
    
    // Mettre à jour le statut localement pour afficher l'état pending immédiatement
    updateSourceStatus('pending');
    
    // Attendre un peu pour montrer l'état pending
    await new Promise(resolve => setTimeout(resolve, 100));
    
    // Puis passer à running
    updateSourceStatus('running');
    
    // Utiliser le service centralisé avec callbacks pour la gestion des événements
    await launchQAAnalysis(source, QA_API_URL, {
      onStatusUpdate: (status, data) => {
        logger.log(`Statut QA mis à jour pour la source ${source.id}:`, status);
        updateSourceStatus(status);
      },
      onSuccess: (data) => {
        logger.log('Analyse QA terminée avec succès:', data);
        updateSourceStatus('completed');
        
        showSuccess(t('Analyse terminée avec succès !'));
        
        // Recharger les données pour afficher les nouvelles réponses
        setTimeout(async () => {
          await refreshDataAndTooltips();
        }, 1000);
      },
      onError: (error, data) => {
        logger.error('Erreur lors de l\'analyse QA:', error);
        updateSourceStatus('failed');
        
        handleApiError(error, t('Erreur lors de l\'analyse'));
      },
      onComplete: (finalStatus, data) => {
        logger.log(`Analyse QA terminée pour la source ${source.id} avec le statut:`, finalStatus);
        updateSourceStatus(finalStatus);
      }
    });
    
  } catch (error) {
    logger.error('Erreur lors du lancement de l\'analyse QA:', error);
    // En cas d'erreur, remettre le statut à null
    updateSourceStatus(null);
    // L'erreur est déjà gérée par le service via les callbacks
  }
}

async function handleSourceIndexing(source) {
  try {
    logger.log('Lancement de l\'indexation pour la source:', source.id);
    
    // Vérifier qu'une collection est sélectionnée
    if (!props.selectedCollection) {
      showError(t('Veuillez sélectionner une collection pour indexer cette source'));
      return;
    }
    
    // Fonction utilitaire pour mettre à jour le statut de la source
    const updateSourceStatus = (status) => {
      const sourceIndex = sources.value.findIndex(s => s.id === source.id);
      if (sourceIndex !== -1) {
        sources.value[sourceIndex].indexing_status = status;
        logger.log(`Statut d'indexation mis à jour pour la source ${source.id}: ${status}`);
      }
    };
    
    // Mettre à jour le statut localement pour afficher l'état pending immédiatement
    updateSourceStatus('pending');
    
    // Attendre un peu pour montrer l'état pending
    await new Promise(resolve => setTimeout(resolve, 100));
    
    // Puis passer à running
    updateSourceStatus('running');
    
    // Lancer la tâche d'indexation via l'API ETL
    const response = await fetch('/rag_app/api/etl/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
      },
      body: JSON.stringify({
        collection_id: props.selectedCollection.id,
        source_id: source.id
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const result = await response.json();
    
    if (result.status === 'success') {
      // Polling du statut de la tâche
      await pollIndexingStatus(result.task_id, source, updateSourceStatus);
      
      // Après completion, rafraîchir le statut d'indexation réel
      await refreshSourceIndexingStatus(source);
    } else {
      throw new Error(result.error || 'Erreur lors du lancement de la tâche d\'indexation');
    }
    
  } catch (error) {
    logger.error('Erreur lors du lancement de l\'indexation:', error);
    // En cas d'erreur, remettre le statut à null
    const sourceIndex = sources.value.findIndex(s => s.id === source.id);
    if (sourceIndex !== -1) {
      sources.value[sourceIndex].indexing_status = null;
    }
    showError(t('Erreur lors du lancement de l\'indexation: ') + error.message);
  }
}

async function pollIndexingStatus(taskId, source, updateSourceStatus) {
  try {
    const maxAttempts = 60; // 5 minutes max
    let attempts = 0;
    
    while (attempts < maxAttempts) {
      await new Promise(resolve => setTimeout(resolve, 5000)); // Attendre 5 secondes
      attempts++;
      
      const response = await fetch(`/rag_app/api/etl/?task_id=${taskId}`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const result = await response.json();
      
      if (result.status === 'completed') {
        updateSourceStatus('completed');
        showSuccess(t('Source indexée avec succès !'));
        break;
      } else if (result.status === 'failed') {
        updateSourceStatus('failed');
        showError(t('Indexation échouée: ') + (result.error || 'Erreur inconnue'));
        break;
      } else if (result.status === 'running') {
        updateSourceStatus('running');
      }
      
      // Si on atteint le maximum d'essais
      if (attempts >= maxAttempts) {
        updateSourceStatus('failed');
        showError(t('Indexation en timeout - la tâche prend trop de temps'));
        break;
      }
    }
  } catch (error) {
    logger.error('Erreur lors du polling du statut d\'indexation:', error);
    updateSourceStatus('failed');
    showError(t('Erreur lors de la vérification du statut d\'indexation'));
  }
}

// La fonction pollQAStatus a été déplacée dans le service tasks.js
// et est maintenant gérée par la fonction launchQAAnalysis centralisée

// Lifecycle
onMounted(async () => {
  try {
    logger.log('Document component mounted, initializing...');
    
    // Charger les sources et initialiser les tooltips
    await refreshDataAndTooltips();
    
    logger.log('Document component initialized successfully');
  } catch (error) {
    logger.error('Error in onMounted:', error);
    showError(t('Erreur lors de l\'initialisation du composant'));
  }
});

// Watcher simplifié
watch(() => props.collectionId, async (newCollectionId, oldCollectionId) => {
  if (newCollectionId === oldCollectionId) {
    return;
  }
  
  try {
    logger.log('Collection changed, reloading sources...');
    
    // Rafraîchir les données et tooltips
    await refreshDataAndTooltips();
    
    logger.log('Collection change completed');
  } catch (error) {
    logger.error('Error in collectionId watch:', error);
    showError(t('Erreur lors du changement de collection'));
  }
});
</script>

<style scoped>
.table {
  margin-top: 1rem;
}

.badge {
  font-size: 0.8em;
}

.btn-group .btn {
  margin-right: 0.25rem;
}

.btn-group .btn:last-child {
  margin-right: 0;
}

.table-responsive {
  border-radius: 0.375rem;
  overflow: hidden;
}

.table-hover tbody tr:hover {
  background-color: rgba(0, 0, 0, 0.075);
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .btn-group {
    flex-direction: column;
  }
  
  .btn-group .btn {
    margin-right: 0;
    margin-bottom: 0.25rem;
  }
  
  .btn-group .btn:last-child {
    margin-bottom: 0;
  }
}

/* Styles pour les boutons d'action avec différents états */
.btn-outline-success:disabled,
.btn-outline-info:disabled,
.btn-success:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Styles spécifiques pour le bouton d'analyse */
.btn-outline-warning {
  border-color: #ffc107;
  color: #856404;
}

.btn-outline-warning:hover {
  background-color: #ffc107;
  border-color: #ffc107;
  color: #000;
}

.btn-outline-info {
  border-color: #17a2b8;
  color: #0c5460;
}

.btn-outline-info:hover {
  background-color: #17a2b8;
  border-color: #17a2b8;
  color: #fff;
}

/* Animation du spinner Bootstrap */
.spinner-border {
  animation: spinner-border 0.75s linear infinite;
  width: 1rem;
  height: 1rem;
}

@keyframes spinner-border {
  to {
    transform: rotate(360deg);
  }
}

/* Centrage des icônes dans les boutons */
.btn i,
.btn .spinner-border {
  display: block;
  margin: 0 auto;
}

.btn-outline-info:hover {
  background-color: #17a2b8;
  border-color: #17a2b8;
  color: #fff;
}

/* Centrage des icônes dans les boutons */
.btn i,
.btn .spinner-border {
  display: block;
  margin: 0 auto;
}
</style> 