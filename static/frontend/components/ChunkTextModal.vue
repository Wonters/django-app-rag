<template>
  <div>
    <!-- Bouton pour ouvrir la modale -->
    <button 
      class="btn btn-sm btn-outline-info" 
      @click="openModal" 
      :title="$t('Voir le texte du chunk')"
      data-bs-toggle="tooltip" 
      data-bs-placement="top"
      :disabled="loading"
    >
      <i v-if="loading" class="bi bi-hourglass-split"></i>
      <i v-else class="bi bi-file-text"></i>
      <span v-if="loading" class="ms-1">{{ $t('Chargement...') }}</span>
    </button>

    <!-- Modale gérée par Vue -->
    <div 
      class="modal fade" 
      :class="{ show: showModal }" 
      style="display: block;" 
      v-if="showModal" 
      @click.self="closeModal"
    >
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              <i class="bi bi-file-text me-2"></i>
              {{ $t('Texte du chunk') }}
            </h5>
            <button 
              type="button" 
              class="btn-close" 
              @click="closeModal"
            ></button>
          </div>
          <div class="modal-body">
            <div v-if="loading" class="text-center py-4">
              <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">{{ $t('Chargement...') }}</span>
              </div>
              <p class="mt-2 text-muted">{{ $t('Récupération du texte du chunk...') }}</p>
            </div>
            
            <div v-else-if="error" class="alert alert-danger">
              <i class="bi bi-exclamation-triangle me-2"></i>
              {{ error }}
            </div>
            
            <div v-else-if="chunkText" class="chunk-content">
              <div class="mb-3">
                <small class="text-muted">
                  <strong>{{ $t('UID') }}:</strong> {{ uid }}
                </small>
                <div v-if="!showFullDocument" class="mt-2">
                  <button 
                    class="btn btn-sm btn-outline-primary" 
                    @click="loadFullDocument"
                    :disabled="loading"
                  >
                    <i v-if="loading" class="bi bi-hourglass-split"></i>
                    <i v-else class="bi bi-file-text"></i>
                    <span v-if="loading" class="ms-1">{{ $t('Chargement...') }}</span>
                    <span v-else class="ms-1">{{ $t('Voir le document complet') }}</span>
                  </button>
                </div>
                <div v-else class="mt-2">
                  <button 
                    class="btn btn-sm btn-outline-secondary" 
                    @click="showChunkOnly"
                  >
                    <i class="bi bi-arrow-left"></i>
                    <span class="ms-1">{{ $t('Revenir au chunk') }}</span>
                  </button>
                </div>
              </div>
              <div class="chunk-text-container">
                <div v-if="showFullDocument && documentData" class="document-info mb-3">
                  <div class="row">
                    <div class="col-md-6">
                      <small class="text-muted">
                        <strong>{{ $t('ID') }}:</strong> {{ documentData.id }}
                      </small>
                    </div>
                    <div class="col-md-6">
                      <small class="text-muted">
                        <strong>{{ $t('Titre') }}:</strong> {{ documentData.title || '-' }}
                      </small>
                    </div>
                  </div>
                  <div class="row mt-2" v-if="documentData.url">
                    <div class="col-12">
                      <small class="text-muted">
                        <strong>{{ $t('URL') }}:</strong> 
                        <a :href="documentData.url" target="_blank" class="text-decoration-none">
                          {{ documentData.url }}
                        </a>
                      </small>
                    </div>
                  </div>
                  <div class="row mt-2" v-if="documentData.metadata">
                    <div class="col-12">
                      <small class="text-muted">
                        <strong>{{ $t('Métadonnées') }}:</strong>
                        <pre class="metadata-display">{{ JSON.stringify(documentData.metadata, null, 2) }}</pre>
                      </small>
                    </div>
                  </div>
                </div>
                <pre class="chunk-text" v-html="showFullDocument ? (documentData?.content || '').replace(/\n/g, '<br>') : chunkText"></pre>
              </div>
            </div>
            
            <div v-else class="text-center py-4">
              <i class="bi bi-file-text fs-1 text-muted"></i>
              <p class="text-muted mt-2">{{ $t('Aucun contenu à afficher') }}</p>
            </div>
          </div>
          <div class="modal-footer">
            <button 
              type="button" 
              class="btn btn-secondary" 
              @click="closeModal"
            >
              {{ $t('Fermer') }}
            </button>
            <button 
              v-if="chunkText" 
              type="button" 
              class="btn btn-primary" 
              @click="copyToClipboard"
            >
              <i class="bi bi-clipboard me-1"></i>
              {{ $t('Copier') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

// Constantes
const CHUNK_TEXT_API_URL = '/rag_app/api/chunk-text/';
const DOCUMENT_TEXT_API_URL = '/rag_app/api/document-text/';

const props = defineProps({
  uid: {
    type: String,
    required: true
  },
  questionId: {
    type: [String, Number],
    default: null
  }
});

const emit = defineEmits(['chunk-loaded', 'error']);

// État du composant
const loading = ref(false);
const chunkText = ref('');
const documentData = ref(null);
const error = ref('');
const showModal = ref(false);
const showFullDocument = ref(false);

// Fonction pour ouvrir la modale
const openModal = async () => {
  if (loading.value) return;
  
  showModal.value = true;
  
  // Toujours charger le contenu (pas de cache côté front)
  await loadChunkText();
};

// Fonction pour fermer la modale
const closeModal = () => {
  showModal.value = false;
  // Réinitialiser le contenu pour forcer le rechargement
  chunkText.value = '';
  documentData.value = null;
  error.value = '';
  showFullDocument.value = false;
};

// Fonction pour extraire le document ID du chunk UID
const extractDocumentId = (chunkUid) => {
  // Format: fA9vzUnCcht-28qciIVETe-Saeu3PXm4_chunk_036
  // Document ID: fA9vzUnCcht-28qciIVETe-Saeu3PXm4
  const parts = chunkUid.split('_chunk_');
  return parts[0];
};

// Fonction pour charger le texte du chunk
const loadChunkText = async () => {
  if (loading.value) return;
  
  loading.value = true;
  error.value = '';
  
  try {
    const params = new URLSearchParams({
      uid: props.uid
    });
    
    if (props.questionId) {
      params.append('question_id', props.questionId);
    }
    
    const response = await fetch(`${CHUNK_TEXT_API_URL}?${params}`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    console.log('Chunk data:', data);
    
    if (data && data.text) {
      chunkText.value = data.text;
      emit('chunk-loaded', {
        uid: props.uid,
        text: data.text,
        questionId: data.question_id
      });
    } else {
      error.value = t('Aucun contenu trouvé pour ce chunk');
    }
  } catch (err) {
    console.error('Erreur lors du chargement du chunk:', err);
    
    if (err.message && err.message.includes('404')) {
      error.value = t('Chunk non trouvé');
    } else if (err.message && err.message.includes('HTTP error')) {
      // Essayer de récupérer le message d'erreur du serveur
      try {
        const errorResponse = await fetch(`${CHUNK_TEXT_API_URL}?${params}`);
        const errorData = await errorResponse.json();
        if (errorData && errorData.error) {
          error.value = errorData.error;
        } else {
          error.value = t('Erreur lors du chargement du chunk');
        }
      } catch {
        error.value = t('Erreur lors du chargement du chunk');
      }
    } else {
      error.value = t('Erreur lors du chargement du chunk');
    }
    
    emit('error', {
      uid: props.uid,
      error: error.value
    });
  } finally {
    loading.value = false;
  }
};

// Fonction pour charger le document complet
const loadFullDocument = async () => {
  if (loading.value) return;
  
  loading.value = true;
  error.value = '';
  
  try {
    const documentId = extractDocumentId(props.uid);
    const params = new URLSearchParams({
      document_id: documentId,
      question_id: props.questionId
    });
    
    const response = await fetch(`${DOCUMENT_TEXT_API_URL}?${params}`);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    console.log('Document data:', data);
    
    if (data && data.document_data) {
      documentData.value = data.document_data;
      showFullDocument.value = true;
      
      // Attendre que le DOM soit mis à jour, puis surligner le chunk
      await nextTick();
      // Ajouter un délai supplémentaire pour s'assurer que le DOM est complètement rendu
      setTimeout(() => {
        highlightChunkInDocument();
      }, 100);
    } else {
      error.value = t('Aucun document trouvé');
    }
  } catch (err) {
    console.error('Erreur lors du chargement du document:', err);
    
    if (err.message && err.message.includes('404')) {
      error.value = t('Document non trouvé');
    } else {
      error.value = t('Erreur lors du chargement du document');
    }
  } finally {
    loading.value = false;
  }
};

// Fonction pour revenir au chunk
const showChunkOnly = () => {
  showFullDocument.value = false;
  
  // Réinitialiser le contenu HTML pour enlever le surlignage
  const chunkTextElement = document.querySelector('.chunk-text');
  if (chunkTextElement) {
    chunkTextElement.innerHTML = chunkText.value;
  }
};

// Fonction pour surligner le chunk dans le document complet
const highlightChunkInDocument = () => {
  if (!chunkText.value || !documentData.value?.content) {
    return;
  }
  
  // Chercher l'élément de texte du chunk dans le DOM
  const chunkTextElement = document.querySelector('.chunk-text');
  if (!chunkTextElement) {
    console.error('Element .chunk-text not found in DOM');
    return;
  }
  
  // Chercher le texte exact du chunk dans le document
  const chunkTextToFind = chunkText.value;
  
  // Remplacer le texte trouvé par une version surlignée (recherche simple)
  let highlightedContent = documentData.value.content.replace(
    new RegExp(chunkTextToFind.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi'), 
    '<mark class="chunk-highlight">$&</mark>'
  );
  
  // Si aucune correspondance trouvée, essayer une recherche plus flexible
  if (!highlightedContent.includes('<mark')) {
    // Essayer de trouver des parties du texte du chunk (mots de plus de 3 caractères)
    const chunkWords = chunkText.value.split(/\s+/).filter(word => word.length > 3);
    if (chunkWords.length > 0) {
      const flexibleRegex = new RegExp(`(${chunkWords.slice(0, 5).join('|')})`, 'gi');
      highlightedContent = documentData.value.content.replace(flexibleRegex, '<mark class="chunk-highlight">$1</mark>');
    }
  }
  
  // Mettre à jour le contenu affiché
  chunkTextElement.innerHTML = highlightedContent.replace(/\n/g, '<br>');
  
  // Attendre un peu pour que le DOM soit mis à jour
  setTimeout(() => {
    // Faire défiler vers le premier élément surligné
    const firstHighlight = chunkTextElement.querySelector('.chunk-highlight');
    
    if (firstHighlight) {
      try {
        // Méthode 1: scrollIntoView avec options
        firstHighlight.scrollIntoView({ 
          behavior: 'smooth', 
          block: 'center',
          inline: 'nearest'
        });
        
        // Méthode 2: Scroll manuel du conteneur si scrollIntoView ne fonctionne pas
        setTimeout(() => {
          const container = chunkTextElement.closest('.chunk-text-container');
          if (container) {
            const containerRect = container.getBoundingClientRect();
            const highlightRect = firstHighlight.getBoundingClientRect();
            
            // Calculer la position relative du highlight dans le conteneur
            const relativeTop = highlightRect.top - containerRect.top + container.scrollTop;
            
            // Faire défiler le conteneur pour centrer le highlight
            container.scrollTo({
              top: relativeTop - (containerRect.height / 2) + (highlightRect.height / 2),
              behavior: 'smooth'
            });
          }
        }, 100);
        
        // Ajouter un effet visuel supplémentaire
        firstHighlight.style.animation = 'highlight-pulse 2s ease-in-out';
        
      } catch (scrollError) {
        console.warn('Error during scroll:', scrollError);
        // Fallback: scroll simple
        firstHighlight.scrollIntoView();
      }
    }
  }, 50);
};

// Fonction pour copier le texte dans le presse-papiers
const copyToClipboard = async () => {
  try {
    const textToCopy = showFullDocument.value ? documentData.value?.content : chunkText.value;
    await navigator.clipboard.writeText(textToCopy);
    // Optionnel: afficher une notification de succès
    console.log('Texte copié dans le presse-papiers');
  } catch (err) {
    console.error('Erreur lors de la copie:', err);
  }
};

</script>

<style scoped>
.modal {
  background: rgba(0,0,0,0.4);
  z-index: 1050;
}

.chunk-content {
  max-height: 60vh;
  overflow-y: auto;
}

.chunk-text-container {
  background-color: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 0.375rem;
  padding: 1rem;
  max-height: 50vh;
  overflow-y: auto;
  scroll-behavior: smooth;
  position: relative;
}

.chunk-text {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.9rem;
  line-height: 1.4;
  margin: 0;
  color: #495057;
}

.document-info {
  background-color: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 0.375rem;
  padding: 1rem;
  margin-bottom: 1rem;
}

.metadata-display {
  background-color: #e9ecef;
  border: 1px solid #ced4da;
  border-radius: 0.25rem;
  padding: 0.5rem;
  font-size: 0.8rem;
  max-height: 200px;
  overflow-y: auto;
  margin-top: 0.5rem;
}

.chunk-highlight {
  background-color: #b3d9ff;
  padding: 2px 4px;
  border-radius: 3px;
  font-weight: 500;
  animation: highlight-pulse 2s ease-in-out;
}

@keyframes highlight-pulse {
  0% {
    background-color: #4dabf7;
    transform: scale(1.02);
  }
  50% {
    background-color: #74c0fc;
    transform: scale(1.05);
  }
  100% {
    background-color: #b3d9ff;
    transform: scale(1);
  }
}

.btn-outline-info:hover {
  background-color: #0dcaf0;
  border-color: #0dcaf0;
  color: white;
}

.spinner-border {
  width: 3rem;
  height: 3rem;
}

/* Responsive */
@media (max-width: 768px) {
  .modal-dialog {
    margin: 0.5rem;
  }
  
  .chunk-text-container {
    max-height: 40vh;
  }
  
  .chunk-text {
    font-size: 0.8rem;
  }
}
</style>
