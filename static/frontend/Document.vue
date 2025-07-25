<template>
  <div>
    <!-- Loading state during navigation -->
    <div v-if="shouldShowLoading" class="text-center py-4">
      <div class="spinner-border" role="status">
        <span class="visually-hidden">{{ $t('Chargement...') }}</span>
      </div>
    </div>
    
    <!-- Vue principale (liste des documents) -->
    <div v-if="isListView">
      <div class="mb-3 text-end">
        <button class="btn btn-success" @click="showUpload = true">
          <i class="bi bi-plus-lg"></i> {{ $t('Ajouter un document') }}
        </button>
      </div>
      
      <!-- Formulaire d'ajout -->
      <SourceForm :show="showUpload" :form-url="sourceFormUrl" @close="updateTable('upload')" @success="handleSourceSuccess" />
      
      <!-- Formulaire d'édition -->
      <SourceForm :show="showEdit" :form-url="editFormUrl" @close="updateTable('edit')" @success="handleSourceSuccess" />
      
      <!-- Tableau des documents -->
      <div>
        <table ref="tableRef" id="documents-table" class="table table-striped" style="width:100%">
          <thead>
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
                <a :href="source.link" target="_blank">{{ source.title }}</a>
              </td>
              <td>{{ source.type }}</td>
              <td>
                <span class="badge bg-primary">{{ source.questions_count || 0 }}</span>
              </td>
              <td>
                <span class="badge bg-success">{{ source.answers_count || 0 }}</span>
              </td>
              <td>
                <button class="btn btn-danger" @click="deleteSource(source.id)" data-bs-toggle="tooltip" data-bs-placement="top" :title="$t('Delete', 1)">
                  <i class="bi bi-trash"></i>
                </button>
                <button class="btn btn-primary mx-2" @click="editSource(source.id)" data-bs-toggle="tooltip" data-bs-placement="top" :title="$t('Edit', 1)">
                  <i class="bi bi-pencil"></i>
                </button>
                <button class="btn btn-info" @click="viewSourceDetails(source.id)" data-bs-toggle="tooltip" data-bs-placement="top" :title="$t('Voir détails', 1)">
                  <i class="bi bi-eye"></i>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Vue détail d'une source -->
    <div v-if="isDetailView">
      <SourceDetail 
        :source="selectedSource"
        @back="goBackToList"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import SourceForm from './SourceForm.vue';
import SourceDetail from './SourceDetail.vue';
import apiService from './services/apiService.js';
import { useTooltips } from './composables/useTooltips';
import { useDataTable } from './composables/useDataTable';

const { t } = useI18n();

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

const emit = defineEmits([]);

// État local
const sources = ref([]);
const showUpload = ref(false);
const showEdit = ref(false);
const editFormUrl = ref('');
const currentView = ref('list'); // 'list' ou 'detail'
const selectedSource = ref(null);
const isNavigating = ref(false); // Flag to prevent multiple navigation attempts

// Computed properties for view management
const isListView = computed(() => !currentView.value || currentView.value === 'list');
const isDetailView = computed(() => currentView.value === 'detail' && selectedSource.value && !isNavigating.value);
const shouldShowLoading = computed(() => isNavigating.value);

// URLs injectées depuis Django
const sourceFormUrl = computed(() => {
  let url = window.SOURCE_FORM_URL;
  if (props.collectionId) {
    const separator = url.includes('?') ? '&' : '?';
    url += `${separator}collection=${props.collectionId}`;
  }
  return url;
});
const sourceApiUrl = window.SOURCE_API_URL;  
const sourceEditUrl = window.SOURCE_EDIT_URL;
const sourceDetailUrl = window.SOURCE_DETAIL_URL;

// Utilisation des composables
const { initTooltips } = useTooltips();
const { tableRef, initDataTable, destroyDataTable } = useDataTable();

// Fonctions
async function fetchSources() {
  try {
    let url = window.SOURCE_API_URL;
    
    // Si une collection est sélectionnée, filtrer par collection
    if (props.collectionId) {
      url += `?collection=${props.collectionId}`;
    }
    
    const response = await apiService.get(url);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    const docs = Array.isArray(data) ? data : (data.results || []);
    sources.value = docs.map(doc => ({
      ...doc,
    }));
  } catch (error) {
    console.error('Erreur lors du chargement des sources:', error);
    sources.value = [];
  }
}

async function updateTable(popupType) {
  try {
    // Fermer la popup en définissant la référence à false
    if (popupType === 'upload') {
      showUpload.value = false;
    } else if (popupType === 'edit') {
      showEdit.value = false;
    }
    
    // Attendre un peu pour s'assurer que la popup est fermée
    await nextTick();
    
    // Recharger les sources
    await fetchSources();
    
    // Réinitialiser le DataTable si nécessaire
    await nextTick();
    if (tableRef.value && document.contains(tableRef.value)) {
      try {
        destroyDataTable();
        await nextTick();
        initDataTable();
        initTooltips();
      } catch (error) {
        console.warn('Error reinitializing DataTable in updateTable:', error);
      }
    }
  } catch (error) {
    console.error('Error in updateTable:', error);
  }
}

async function handleSourceSuccess() {
  try {
    console.log('Source added/updated successfully, reloading data...');
    
    // Fermer les popups
    showUpload.value = false;
    showEdit.value = false;
    
    // Recharger les sources
    await fetchSources();
    
    // Forcer le rechargement du composant Document via la fonction globale
    if (window.forceDocumentReload) {
      window.forceDocumentReload();
    }
    
    // Réinitialiser le DataTable après le rechargement
    await nextTick();
    
    // Vérifier si l'élément existe avant d'initialiser
    if (tableRef.value && document.contains(tableRef.value)) {
      try {
        // Détruire l'ancien DataTable
        destroyDataTable();
        await nextTick();
        
        // Initialiser le nouveau DataTable
        initDataTable();
        initTooltips();
        
        console.log('DataTable reinitialized successfully');
      } catch (error) {
        console.warn('Error reinitializing DataTable:', error);
      }
    }
  } catch (error) {
    console.error('Error in handleSourceSuccess:', error);
  }
}

function editSource(id) {
  try {
    editFormUrl.value = sourceEditUrl.replace('__pk__', id);
    showEdit.value = true;
  } catch (error) {
    console.error('Error in editSource:', error);
  }
}

function deleteSource(id) {
  try {
    if (confirm(t('Êtes-vous sûr de vouloir supprimer cette source ?'))) {
      handleDeleteSource(id);
    }
  } catch (error) {
    console.error('Error in deleteSource:', error);
  }
}

async function handleDeleteSource(id) {
  try {
    const response = await apiService.deleteWithCsrfFetch(`${window.SOURCE_API_URL}${id}/`);
    
    if (response.ok) {
      // Recharger la liste des sources après suppression
      await fetchSources();
    } else {
      console.error('Erreur lors de la suppression de la source');
    }
  } catch (error) {
    console.error('Erreur lors de la suppression:', error);
  }
}

async function viewSourceDetails(id) {
  try {
    // Prevent multiple navigation attempts
    if (isNavigating.value) {
      console.log('Navigation already in progress, skipping');
      return;
    }
    
    isNavigating.value = true;
    
    // Set a timeout to reset the navigation flag if something goes wrong
    const navigationTimeout = setTimeout(() => {
      if (isNavigating.value) {
        console.warn('Navigation timeout, resetting flag');
        isNavigating.value = false;
      }
    }, 5000); // 5 second timeout
    
    // Trouver la source correspondante
    const source = sources.value.find(s => s.id === id);
    if (source) {
      // Destroy DataTable before switching views
      try {
        destroyDataTable();
      } catch (dtError) {
        console.warn('Error destroying DataTable:', dtError);
      }
      
      await nextTick();
      
      selectedSource.value = source;
      currentView.value = 'detail';
      
      console.log('Switched to detail view for source:', source.id);
    }
    
    // Clear the timeout since navigation completed successfully
    clearTimeout(navigationTimeout);
    
  } catch (error) {
    console.error('Error in viewSourceDetails:', error);
  } finally {
    // Always reset the navigation flag
    isNavigating.value = false;
  }
}

async function goBackToList() {
  try {
    // Prevent multiple navigation attempts
    if (isNavigating.value) {
      console.log('Navigation already in progress, skipping');
      return;
    }
    
    isNavigating.value = true;
    
    // Set a timeout to reset the navigation flag if something goes wrong
    const navigationTimeout = setTimeout(() => {
      if (isNavigating.value) {
        console.warn('Navigation timeout, resetting flag');
        isNavigating.value = false;
      }
    }, 5000); // 5 second timeout
    
    console.log('goBackToList called');
    console.log('Current view before:', currentView.value);
    console.log('Selected source before:', selectedSource.value);
    
    // First, destroy any existing DataTable to prevent conflicts
    try {
      destroyDataTable();
    } catch (dtError) {
      console.warn('Error destroying DataTable:', dtError);
    }
    
    // Use nextTick to ensure DOM updates are complete
    await nextTick();
    
    // Reset state explicitly
    currentView.value = 'list';
    selectedSource.value = null;
    
    console.log('Current view after:', currentView.value);
    console.log('Selected source after:', selectedSource.value);
    
    // Wait for next tick to ensure state changes are applied
    await nextTick();
    
    // Reinitialize DataTable for the list view
    try {
      await nextTick();
      initDataTable();
      initTooltips();
    } catch (initError) {
      console.warn('Error reinitializing DataTable:', initError);
    }
    
    // Clear the timeout since navigation completed successfully
    clearTimeout(navigationTimeout);
    
  } catch (error) {
    console.error('Error in goBackToList:', error);
    // Fallback: force the state change even if there's an error
    currentView.value = 'list';
    selectedSource.value = null;
  } finally {
    // Always reset the navigation flag
    isNavigating.value = false;
  }
}

// Lifecycle
onMounted(async () => {
  try {
    await fetchSources();
    await nextTick();
    // Initialisation des tooltips Bootstrap
    initTooltips();
  } catch (error) {
    console.error('Error in onMounted:', error);
  }
});

// Watch pour recharger les sources quand la collection change
watch(() => props.collectionId, async () => {
  try {
    // Détruire le DataTable avant de changer de collection
    try {
      destroyDataTable();
    } catch (error) {
      console.warn('Error destroying DataTable during collection change:', error);
    }
    
    await fetchSources();
  } catch (error) {
    console.error('Error in collectionId watch:', error);
  }
});

watch(() => sources.value, async () => {
  try {
    // Don't interfere with navigation operations
    if (isNavigating.value) {
      console.log('Navigation in progress, skipping sources watch');
      return;
    }
    
    // Vérifier si le composant est toujours monté et si l'élément existe
    if (!tableRef.value || !document.contains(tableRef.value)) {
      console.log('Table element not found, skipping DataTable update');
      return;
    }
    
    console.log('Sources changed, updating DataTable');
    
    // Détruire le DataTable existant de manière sécurisée
    try {
      destroyDataTable();
    } catch (error) {
      console.warn('Error destroying DataTable:', error);
    }
    
    // Attendre que le DOM soit mis à jour
    await nextTick();
    
    // Vérifier à nouveau si l'élément existe avant d'initialiser
    if (tableRef.value && document.contains(tableRef.value)) {
      try {
        initDataTable();
        // Réinitialisation des tooltips après mise à jour du DOM
        initTooltips();
      } catch (error) {
        console.warn('Error initializing DataTable:', error);
      }
    }
  } catch (error) {
    console.error('Error in sources watch:', error);
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

.btn {
  margin-right: 0.25rem;
}

.alert {
  margin-bottom: 1rem;
}
</style> 