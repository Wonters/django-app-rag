<template>
  <div id="app">
    <div class="d-flex justify-content-between">
      <h1>Django RAG</h1>

      <div class="text-end mb-2">
        <select class="select-lang form-select" v-model="$i18n.locale">
          <option class="text-primary" value="fr">{{ $t('Français') }}</option>
          <option class="text-primary" value="en">{{ $t('Anglais') }}</option>
        </select>
      </div>
    </div>
    
    <hr />
    
    <!-- Layout avec collections en ligne en haut et documents en dessous -->
    
    <!-- Section des collections en ligne -->
    <div class="mb-4">
      <div class="card">
        <div class="card-header d-flex justify-content-between align-items-center">
          <h5 class="mb-0">{{ $t('Collections') }}</h5>
          <button class="btn btn-success btn-sm" @click="showCreateCollection = true">
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
                @click="selectCollection(collection)"
                style="cursor: pointer; transition: all 0.2s ease;"
              >
                <div class="card-body text-center p-3">
                  <div class="mb-2">
                    <i class="bi bi-collection display-6 text-primary"></i>
                  </div>
                  <h6 class="card-title mb-1 text-truncate" :title="collection.title">
                    {{ collection.title }}
                  </h6>
                  <small class="text-muted d-block text-truncate" :title="collection.description || 'Aucune description'">
                    {{ collection.description || 'Aucune description' }}
                  </small>
                  <div class="mt-2">
                    <span class="badge bg-primary rounded-pill">{{ collection.sources_count || 0 }}</span>
                  </div>
                </div>
                <div class="card-footer p-2 bg-transparent border-top-0">
                  <div class="d-flex justify-content-center gap-1">
                    <button 
                      class="btn btn-outline-secondary btn-sm" 
                      @click.stop="editCollection(collection)" 
                      :title="$t('Edit', 1)"
                    >
                      <i class="bi bi-pencil"></i>
                    </button>
                    <button 
                      class="btn btn-outline-danger btn-sm" 
                      @click.stop="deleteCollection(collection.id)" 
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
            <button class="btn btn-primary" @click="showCreateCollection = true">
              {{ $t('Créer votre première collection') }}
            </button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Section des documents en dessous -->
    <div class="card">
      <div class="card-header">
        <h5 class="mb-0">
          {{ selectedCollection ? `${$t('Documents de')} "${selectedCollection.title}"` : $t('Sélectionnez une collection pour voir ses documents') }}
        </h5>
      </div>
      <div class="card-body">
        <Document 
          v-if="selectedCollection"
          :key="`collection-${selectedCollection.id}-${documentKey}`"
          :collection-id="selectedCollection.id"
          :selected-collection="selectedCollection"
        />
        <div v-else class="text-center text-muted py-5">
          <i class="bi bi-file-text display-1"></i>
          <p class="mt-3">{{ $t('Cliquez sur une collection pour voir ses documents') }}</p>
        </div>
      </div>
    </div>

    <!-- Formulaire de collection -->
    <CollectionForm 
      :show="showCreateCollection || showEditCollection"
      :collection="editingCollection"
      :form-url="collectionFormUrl"
      @close="closeCollectionForm"
      @success="handleCollectionSuccess"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, computed, nextTick } from 'vue';
import Document from './Document.vue';
import CollectionForm from './CollectionForm.vue';
import apiService from './services/apiService.js';

// État local
const collections = ref([]);
const selectedCollection = ref(null);
const showCreateCollection = ref(false);
const showEditCollection = ref(false);
const editingCollection = ref(null);
const documentKey = ref(0); // Clé pour forcer la recréation du composant Document

// URLs injectées depuis Django
const collectionApiUrl = window.COLLECTION_API_URL;
const collectionEditUrl = window.COLLECTION_EDIT_URL;

// Computed
const collectionFormUrl = computed(() => {
  if (editingCollection.value) {
    return collectionEditUrl.replace('__pk__', editingCollection.value.id);
  }
  return window.COLLECTION_FORM_URL;
});

// Fonctions
async function fetchCollections() {
  try {
    const response = await apiService.get(collectionApiUrl);
    const data = await response.json();
    collections.value = Array.isArray(data) ? data : (data.results || []);
  } catch (error) {
    console.error('Erreur lors du chargement des collections:', error);
    collections.value = [];
  }
}

function selectCollection(collection) {
  // Si on clique sur la même collection, ne rien faire
  if (selectedCollection.value && selectedCollection.value.id === collection.id) {
    return;
  }
  
  // Désélectionner d'abord pour forcer la destruction du composant Document
  selectedCollection.value = null;
  
  // Utiliser nextTick pour s'assurer que le DOM est mis à jour
  nextTick(() => {
    selectedCollection.value = collection;
  });
}

function editCollection(collection) {
  editingCollection.value = collection;
  showEditCollection.value = true;
}

async function deleteCollection(collectionId) {
  if (confirm(t('Êtes-vous sûr de vouloir supprimer cette collection ?'))) {
    try {
      const response = await apiService.deleteWithCsrfFetch(`${collectionApiUrl}${collectionId}/`);
      
      if (response.ok) {
        // Si la collection supprimée était sélectionnée, désélectionner
        if (selectedCollection.value && selectedCollection.value.id === collectionId) {
          selectedCollection.value = null;
        }
        // Recharger la liste des collections
        await fetchCollections();
      } else {
        console.error('Erreur lors de la suppression de la collection');
        alert(t('Erreur lors de la suppression de la collection'));
      }
    } catch (error) {
      console.error('Erreur lors de la suppression:', error);
      alert(t('Erreur lors de la suppression de la collection'));
    }
  }
}

function closeCollectionForm() {
  showCreateCollection.value = false;
  showEditCollection.value = false;
  editingCollection.value = null;
}

function handleCollectionSuccess(collection) {
  // Recharger la liste des collections
  fetchCollections();
  
  // Si c'était une création et qu'aucune collection n'est sélectionnée, sélectionner la nouvelle
  if (!selectedCollection.value) {
    selectedCollection.value = collection;
  }
}

// Fonction pour forcer le rechargement du composant Document
function forceDocumentReload() {
  documentKey.value++;
}

// Exposer la fonction globalement pour qu'elle puisse être appelée depuis Document.vue
window.forceDocumentReload = forceDocumentReload;

onMounted(() => {
  fetchCollections();
});
</script>

<style scoped>
h1 {
  color: #42b983;
}

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