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
                  <button class="btn btn-outline-danger btn-sm" @click="deleteSource(source.id)" :title="$t('Delete', 1)">
                    <i class="bi bi-trash"></i>
                  </button>
                  <button class="btn btn-outline-primary btn-sm" @click="editSource(source.id)" :title="$t('Edit', 1)">
                    <i class="bi bi-pencil"></i>
                  </button>
                  <button class="btn btn-outline-info btn-sm" @click="viewSourceDetails(source)" :title="$t('Voir détails', 1)">
                    <i class="bi bi-eye"></i>
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
import { ref, onMounted, watch, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import SourceForm from './SourceForm.vue';
import apiService from '../services/apiService.js';
import { useErrorHandler } from '../composables/useErrorHandler.js';
import { SOURCE_API_URL, SOURCE_FORM_URL, SOURCE_EDIT_URL } from '../config/api.js';

const { t } = useI18n();

// Utilisation du composable d'erreur
const {
  showSuccess,
  showError,
  confirmDelete,
  handleApiError,
  logger
} = useErrorHandler();

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
    
    // Recharger les sources
    await fetchSources();
    
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

// Lifecycle
onMounted(async () => {
  try {
    logger.log('Document component mounted, initializing...');
    await fetchSources();
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
    await fetchSources();
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
</style> 