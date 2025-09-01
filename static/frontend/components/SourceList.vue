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
      <SourceForm :show="showUpload" :form-url="sourceFormUrl" @close="closeUploadForm"
        @success="handleSourceSuccess" />

      <!-- Formulaire d'édition -->
      <SourceForm :show="showEdit" :form-url="editFormUrl" @close="closeEditForm" @success="handleSourceSuccess" />

      <!-- Notifications toast -->
      <NotificationToast :notifications="notifications" @remove="removeNotification" />

      <!-- Modale de confirmation -->
      <ConfirmationModal :confirmation-modal="confirmationModal" @confirm="handleConfirm" @cancel="handleCancel" />

      <!-- Tableau des documents -->
      <div class="table-responsive">
        <table ref="tableRef" class="table table-striped table-hover">
          <thead class="table-dark">
            <tr>
              <th>{{ $t('ID', 2) }}</th>
              <th>{{ $t('Source name', 2) }}</th>
              <th>{{ $t('Type', 2) }}</th>
              <th>{{ $t('Questions', 2) }}</th>
              <th>{{ $t('Answers', 2) }}</th>
              <th>{{ $t('Indexé', 2) }}</th>
              <th>{{ $t('Analyse', 2) }}</th>
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
                <!-- Colonne Indexé -->
                <div class="text-center">
                  <span v-if="source.is_indexed_at" class="badge bg-success">
                    <i class="bi bi-check-circle"></i> {{ $t('Oui', 2) }}
                  </span>
                  <span v-else class="badge bg-secondary">
                    <i class="bi bi-x-circle"></i> {{ $t('Non', 2) }}
                  </span>
                </div>
              </td>
              <td>
                <!-- Colonne Analyse -->
                <div class="text-center">
                  <button class="btn btn-sm" :class="{
                    'btn-outline-success': !source.qa_status || source.qa_status === 'completed',
                    'btn-outline-warning': source.qa_status === 'failed',
                    'btn-outline-info': source.qa_status === 'pending',
                    'btn-success': source.qa_status === 'running'
                  }" @click="handleQAAnalysis(source)" :title="getQATooltip(source.qa_status)"
                    :disabled="source.qa_status === 'running' || source.qa_status === 'pending' || !source.is_indexed_at"
                    data-bs-toggle="tooltip" data-bs-placement="top">
                    <ButtonSpinner :status="source.qa_status" default-icon-class="bi bi-robot" />
                  </button>
                </div>
              </td>
              <td>
                <div class="btn-group" role="group">
                  <button class="btn btn-outline-danger btn-sm" @click="deleteSource(source.id)" :title="$t('Delete')">
                    <i class="bi bi-trash"></i>
                  </button>
                  <button class="btn btn-outline-primary btn-sm" @click="editSource(source.id)" :title="$t('Edit')">
                    <i class="bi bi-pencil"></i>
                  </button>
                  <button class="btn btn-outline-info btn-sm" @click="viewSourceDetails(source)"
                    :title="$t('Voir détails')">
                    <i class="bi bi-eye"></i>
                  </button>

                  <!-- Bouton d'indexation de la source -->
                  <button class="btn btn-sm" :class="{
                    'btn-outline-secondary': !source.indexing_status || source.indexing_status === 'completed',
                    'btn-outline-warning': source.indexing_status === 'failed',
                    'btn-outline-info': source.indexing_status === 'pending',
                    'btn-secondary': source.indexing_status === 'running'
                  }" @click="handleSourceIndexing(source)" :title="getIndexingTooltip(source.indexing_status)"
                    :disabled="source.indexing_status === 'running' || source.indexing_status === 'pending'"
                    data-bs-toggle="tooltip" data-bs-placement="top">
                    <ButtonSpinner :status="source.indexing_status" default-icon-class="bi bi-database" />
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
import { ref, onMounted, onBeforeUnmount, watch, computed, nextTick } from 'vue';
import { useI18n } from 'vue-i18n';
import SourceForm from './SourceForm.vue';
import NotificationToast from './NotificationToast.vue';
import ConfirmationModal from './ConfirmationModal.vue';
import ButtonSpinner from './ButtonSpinner.vue';
import apiService from '../services/apiService.js';
import { launchQAAnalysis, launchIndexing } from '../services/tasks.js';
import { useErrorHandler } from '../composables/useErrorHandler.js';
import { useTooltips } from '../composables/useTooltips';
import { useDataTable } from '../composables/useDataTable.js';
import { SOURCE_API_URL, SOURCE_FORM_URL, SOURCE_EDIT_URL, QA_API_URL, ETL_API_URL } from '../config/api.js';

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

// Utilisation du composable DataTable
const { tableRef, initDataTable, destroyDataTable, refreshDataTable } = useDataTable({
  pageLength: 10,
  lengthMenu: [[5, 10, 25, 50], [5, 10, 25, 50]],
  order: [[0, 'asc']],
  columnDefs: [
    { targets: [5, 6, 7], orderable: false }, // Colonnes Indexé, Analyse, Actions non triables
    { targets: [3, 4], type: 'num' }, // Colonnes Questions et Answers de type numérique
  ],
  //language: {
  //url: '//cdn.datatables.net/plug-ins/1.13.7/i18n/fr-FR.json'
  //}
});

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

const emit = defineEmits(['view-details']);

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


const updateSourceStatus = (status, source) => {
      const sourceIndex = sources.value.findIndex(s => s.id === source.id);
      if (sourceIndex !== -1) {
        sources.value[sourceIndex].indexing_status = status;
        logger.log(`Statut d'indexation mis à jour pour la source ${source.id}: ${status}`);
      }
    };

// Fonctions simplifiées∑
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
    logger.log('Début du rafraîchissement des données...');

    // Détruire d'abord DataTable et tooltips pour éviter les conflits DOM
    destroyDataTable();
    destroyTooltips();
    await nextTick();
    await fetchSources();
    await nextTick();
    initTooltips();

    console.log('Sources après rafraîchissement:', sources.value.length);

    if (sources.value.length > 0) {
      initDataTable();
      logger.log('DataTable initialisé avec succès');
    } else {
      logger.log('Aucune source à afficher, DataTable non initialisé');
    }

    logger.log('Rafraîchissement des données terminé');
  } catch (error) {
    logger.error('Erreur lors du rafraîchissement des données et tooltips:', error);
    // En cas d'erreur, s'assurer que l'état est cohérent
    sources.value = [];
    error.value = error.message;
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
        // Rafraîchir DataTable
        await refreshDataAndTooltips();
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
    updateSourceStatus('pending', source);
    await new Promise(resolve => setTimeout(resolve, 100));
    updateSourceStatus('running', source);

    await launchQAAnalysis(source, QA_API_URL, {
      onStatusUpdate: (status, data) => {
        logger.log(`Statut QA mis à jour pour la source ${source.id}:`, status);
        updateSourceStatus(status, source);
      },
      onSuccess: (data) => {
        logger.log('Analyse QA terminée avec succès:', data);
        updateSourceStatus('completed', source);
        showSuccess(t('Analyse terminée avec succès !'));
        // Recharger les données pour afficher les nouvelles réponses
        setTimeout(async () => {
          await refreshDataAndTooltips();
        }, 1000);
      },
      onError: (error, data) => {
        logger.error('Erreur lors de l\'analyse QA:', error);
        updateSourceStatus('failed', source);
        handleApiError(error, t('Erreur lors de l\'analyse'));
      },
      onComplete: (finalStatus, data) => {
        logger.log(`Analyse QA terminée pour la source ${source.id} avec le statut:`, finalStatus);
        updateSourceStatus(finalStatus, source);
      }
    });

  } catch (error) {
    logger.error('Erreur lors du lancement de l\'analyse QA:', error);
    updateSourceStatus(null, source);
  }
}

async function handleSourceIndexing(source) {
  try{
    logger.log('Lancement de l\'indexation pour la source:', source.id);

    await launchIndexing(source, ETL_API_URL, {
      onStatusUpdate: (status, data) => {
        logger.log(`Statut d'indexation mis à jour pour la source ${source.id}:`, status);
        updateSourceStatus(status, source);
      },
      onSuccess: (data) => {
        logger.log('Indexation terminée avec succès:', data);
        updateSourceStatus('completed', source);
        showSuccess(t('Indexation terminée avec succès !'));
        // Recharger les données pour afficher les nouvelles réponses
        setTimeout(async () => {
          await refreshDataAndTooltips();
        }, 1000);
      },
      onError: (error, data) => {
        logger.error('Erreur lors de l\'indexation:', error);
        updateSourceStatus('failed', source);
        handleApiError(error, t('Erreur lors de l\'indexation'));
      },
      onComplete: (finalStatus, data) => {
        logger.log(`Indexation terminée pour la source ${source.id} avec le statut:`, finalStatus);
        updateSourceStatus(finalStatus, source);
      }
    });
  }
  catch(error){
    logger.error('Erreur lors du lancement de l\'indexation:', error);
  }
}

onMounted(async () => {
  try {
    logger.log('Document component mounted, initializing...');
    await refreshDataAndTooltips();
    logger.log('Document component initialized successfully');
  } catch (error) {
    logger.error('Error in onMounted:', error);
    showError(t('Erreur lors de l\'initialisation du composant'));
  }
});

onBeforeUnmount(() => {
  destroyDataTable();
  destroyTooltips();

  logger.log('Composant SourceList démonté, ressources nettoyées');
});

// Watcher amélioré pour les changements de collection
watch(() => props.collectionId, async (newCollectionId, oldCollectionId) => {
  if (newCollectionId === oldCollectionId) {
    return;
  }

  try {
    logger.log('Collection changed, reloading sources...');
    sources.value = [];
    await nextTick();
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
  background-color: rgba(36, 119, 130, 0.474);
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

/* Styles pour DataTables */
.dataTables_wrapper .dataTables_length,
.dataTables_wrapper .dataTables_filter,
.dataTables_wrapper .dataTables_info,
.dataTables_wrapper .dataTables_paginate {
  margin: 1rem 0;
}

.dataTables_wrapper .dataTables_filter input {
  border: 1px solid #dee2e6;
  border-radius: 0.375rem;
  padding: 0.375rem 0.75rem;
}

.dataTables_wrapper .dataTables_paginate .paginate_button {
  border: 1px solid #dee2e6;
  border-radius: 0.375rem;
  margin: 0 0.125rem;
}

.dataTables_wrapper .dataTables_paginate .paginate_button.current {
  background-color: #0d6efd;
  border-color: #0d6efd;
  color: white !important;
}

.dataTables_wrapper .dataTables_paginate .paginate_button:hover {
  background-color: #e9ecef;
  border-color: #dee2e6;
}

/* Responsive pour DataTables */
@media (max-width: 768px) {

  .dataTables_wrapper .dataTables_length,
  .dataTables_wrapper .dataTables_filter {
    text-align: center;
    margin-bottom: 0.5rem;
  }

  .dataTables_wrapper .dataTables_info,
  .dataTables_wrapper .dataTables_paginate {
    text-align: center;
    margin-top: 0.5rem;
  }
}
</style>