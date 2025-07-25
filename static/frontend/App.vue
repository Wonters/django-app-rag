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
    
    <!-- Section des collections -->
    <CollectionsSection 
      :collections="collections"
      :selected-collection="selectedCollection"
      @select="selectCollection"
      @edit="editCollection"
      @delete="deleteCollection"
      @create="createCollection"
    />
    
    <!-- Section des documents -->
    <SourceSection 
      :selected-collection="selectedCollection"
      @refresh="refreshCollections"
    />

    <!-- Formulaire de collection -->
    <CollectionForm 
      v-if="formState.show"
      :collection="formState.collection"
      :form-url="formState.formUrl"
      @close="closeForm"
      @success="handleFormSuccess"
    />

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
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import CollectionsSection from './components/CollectionsSection.vue';
import SourceSection from './components/SourceSection.vue';
import CollectionForm from './components/CollectionForm.vue';
import NotificationToast from './components/NotificationToast.vue';
import ConfirmationModal from './components/ConfirmationModal.vue';
import apiService from './services/apiService.js';
import { useErrorHandler } from './composables/useErrorHandler.js';
import { COLLECTION_API_URL, COLLECTION_EDIT_URL, COLLECTION_FORM_URL } from './config/api.js';

const { t } = useI18n();

// Utilisation du composable d'erreur
const {
  notifications,
  confirmationModal,
  showSuccess,
  showError,
  confirmDelete,
  handleApiError,
  removeNotification,
  logger
} = useErrorHandler();

// État principal
const collections = ref([]);
const selectedCollection = ref(null);

// État du formulaire
const formState = reactive({
  show: false,
  collection: null,
  formUrl: ''
});

// URLs depuis la configuration centralisée
const collectionApiUrl = COLLECTION_API_URL;
const collectionEditUrl = COLLECTION_EDIT_URL;

// Computed pour l'URL du formulaire
const getFormUrl = (collection = null) => {
  if (collection) {
    return collectionEditUrl.replace('__pk__', collection.id);
  }
  return COLLECTION_FORM_URL;
};

// Fonctions principales
async function fetchCollections() {
  try {
    const response = await apiService.get(collectionApiUrl);
    const data = await response.json();
    collections.value = Array.isArray(data) ? data : (data.results || []);
  } catch (error) {
    logger.error('Erreur lors du chargement des collections:', error);
    showError(t('Erreur lors du chargement des collections'));
    collections.value = [];
  }
}

function selectCollection(collection) {
  selectedCollection.value = collection;
}

function editCollection(collection) {
  formState.collection = collection;
  formState.formUrl = getFormUrl(collection);
  formState.show = true;
}

function createCollection() {
  formState.collection = null;
  formState.formUrl = getFormUrl();
  formState.show = true;
}

async function deleteCollection(collectionId) {
  const collection = collections.value.find(c => c.id === collectionId);
  const collectionName = collection?.title || 'cette collection';
  
  confirmDelete(collectionName, async () => {
    try {
      const response = await apiService.deleteWithCsrfFetch(`${collectionApiUrl}${collectionId}/`);
      
      if (response.ok) {
        // Si la collection supprimée était sélectionnée, désélectionner
        if (selectedCollection.value?.id === collectionId) {
          selectedCollection.value = null;
        }
        await fetchCollections();
        showSuccess(t('Collection supprimée avec succès'));
      } else {
        showError(t('Erreur lors de la suppression de la collection'));
      }
    } catch (error) {
      handleApiError(error, t('Erreur lors de la suppression de la collection'));
    }
  });
}

function closeForm() {
  formState.show = false;
  formState.collection = null;
}

function handleFormSuccess(collection) {
  closeForm();
  fetchCollections();
  
  // Si c'était une création et qu'aucune collection n'est sélectionnée, sélectionner la nouvelle
  if (!selectedCollection.value) {
    selectedCollection.value = collection;
  }
  
  // Afficher un message de succès
  const message = collection ? t('Collection modifiée avec succès') : t('Collection créée avec succès');
  showSuccess(message);
}

function refreshCollections() {
  fetchCollections();
}

// Gestion des événements de confirmation
function handleConfirm() {
  // Cette fonction sera appelée par la modale de confirmation
  // La logique spécifique est gérée dans les callbacks de confirmDelete
}

function handleCancel() {
  // Cette fonction sera appelée quand l'utilisateur annule une confirmation
  // Pas d'action nécessaire ici
}

onMounted(() => {
  fetchCollections();
});
</script>

<style scoped>
h1 {
  color: #42b983;
}
</style> 