<template>
  <div class="source-detail">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2>{{ $t('Détails de la source') }}</h2>
      <button class="btn btn-secondary" @click="handleBack">
        <i class="bi bi-arrow-left"></i> {{ $t('Retour') }}
      </button>
    </div>

    <!-- Informations de la source -->
    <div class="card mb-4">
      <div class="card-header">
        <h5 class="mb-0">{{ $t('Informations de la source') }}</h5>
      </div>
      <div class="card-body">
        <div class="row">
          <div class="col-md-6">
            <p><strong>{{ $t('Titre') }}:</strong> {{ source.title }}</p>
            <p><strong>{{ $t('Type') }}:</strong> {{ source.type }}</p>
          </div>
          <div class="col-md-6">
            <p><strong>{{ $t('Lien') }}:</strong> 
              <a :href="source.link" target="_blank">{{ source.link }}</a>
            </p>
            <p><strong>{{ $t('Date de création') }}:</strong> {{ formatDate(source.created_at) }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Section des questions -->
    <div class="card">
      <div class="card-header d-flex justify-content-between align-items-center">
        <h5 class="mb-0">{{ $t('Questions et réponses') }}</h5>
        <button class="btn btn-success" @click="showQuestionForm = true">
          <i class="bi bi-plus-lg"></i> {{ $t('Ajouter une question') }}
        </button>
      </div>
      <div class="card-body">
        <div v-if="isLoading" class="text-center py-4">
          <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">{{ $t('Chargement...') }}</span>
          </div>
          <p class="mt-2">{{ $t('Chargement des questions...') }}</p>
        </div>
        <QuestionList 
          v-else-if="questions && questions.length > 0"
          :questions="questions" 
          :source-id="source.id"
          @edit-question="handleEditQuestion"
          @delete-question="handleDeleteQuestion"
        />
        <div v-else class="text-center py-4 text-muted">
          <i class="bi bi-chat-dots fs-1"></i>
          <p class="mt-2">{{ $t('Aucune question pour cette source') }}</p>
        </div>
      </div>
    </div>

    <!-- Modal pour ajouter/modifier une question -->
    <QuestionForm 
      :show="showQuestionForm" 
      :source-id="source.id"
      :question="editingQuestion || null"
      :form-url="currentQuestionFormUrl"
      @close="handleQuestionFormClosed"
      @success="handleQuestionSaved"
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
import { ref, onMounted, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import QuestionList from './QuestionList.vue';
import QuestionForm from './QuestionForm.vue';
import NotificationToast from './NotificationToast.vue';
import ConfirmationModal from './ConfirmationModal.vue';
import apiService from '../services/apiService.js';
import { useErrorHandler } from '../composables/useErrorHandler.js';
import { QUESTION_API_URL, QUESTION_FORM_URL, QUESTION_EDIT_URL } from '../config/api.js';

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

const props = defineProps({
  source: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['back']);

const questions = ref([]);
const showQuestionForm = ref(false);
const editingQuestion = ref(null);
const isLoading = ref(false);

// URLs depuis la configuration centralisée
const questionApiUrl = QUESTION_API_URL;
const questionFormUrl = QUESTION_FORM_URL;
const questionEditUrl = QUESTION_EDIT_URL;

// Computed pour l'URL du formulaire de question
const currentQuestionFormUrl = computed(() => {
  if (editingQuestion.value) {
    return questionEditUrl.replace('__pk__', editingQuestion.value.id);
  }
  return questionFormUrl;
});

// Gestionnaires d'événements pour les composants UI
function handleConfirm() {
  // Cette fonction sera appelée par la modale de confirmation
  // La logique spécifique est gérée dans les callbacks de confirmDelete
}

function handleCancel() {
  // Cette fonction sera appelée quand l'utilisateur annule une confirmation
  // Pas d'action nécessaire ici
}

// Fonctions
async function fetchQuestions() {
  isLoading.value = true;
  
  try {
    const url = `${questionApiUrl}?source_id=${props.source.id}`;
    const response = await apiService.get(url);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    questions.value = Array.isArray(data) ? data : (data.results || []);
    
    logger.log('Questions chargées avec succès:', questions.value.length);
  } catch (error) {
    logger.error('Erreur lors du chargement des questions:', error);
    showError(t('Erreur lors du chargement des questions'));
    questions.value = [];
  } finally {
    isLoading.value = false;
  }
}

function handleEditQuestion(question) {
  editingQuestion.value = question;
  showQuestionForm.value = true;
}

function handleDeleteQuestion(questionId) {
  const question = questions.value.find(q => q.id === questionId);
  const questionTitle = question?.title || 'cette question';
  
  confirmDelete(questionTitle, async () => {
    try {
      logger.log('Suppression de la question:', questionId);
      const response = await apiService.deleteWithCsrfFetch(`${questionApiUrl}${questionId}/`);
      
      if (response.ok) {
        logger.log('Question supprimée avec succès');
        showSuccess(t('Question supprimée avec succès'));
        // Rafraîchir immédiatement la liste
        await fetchQuestions();
      } else {
        showError(t('Erreur lors de la suppression de la question'));
      }
    } catch (error) {
      handleApiError(error, t('Erreur lors de la suppression de la question'));
    }
  });
}

function closeQuestionForm() {
  showQuestionForm.value = false;
  editingQuestion.value = null;
}

function handleQuestionSaved() {
  closeQuestionForm();
  
  // Ajouter un délai pour s'assurer que les données sont sauvegardées côté serveur
  setTimeout(async () => {
    logger.log('Rafraîchissement des questions après sauvegarde...');
    await fetchQuestions();
    showSuccess(t('Question sauvegardée avec succès'));
  }, 500);
}

function handleQuestionFormClosed() {
  // Si le formulaire est fermé sans sauvegarde, on ne fait rien
  logger.log('Formulaire fermé sans sauvegarde');
}

async function handleBack() {
  try {
    logger.log('handleBack called');
    logger.log('Emitting back event');
    
    // Add a small delay to ensure proper event processing
    await new Promise(resolve => setTimeout(resolve, 10));
    
    emit('back');
    logger.log('Back event emitted successfully');
  } catch (error) {
    logger.error('Error in handleBack:', error);
    // Try to emit the event again as a fallback
    try {
      emit('back');
    } catch (fallbackError) {
      logger.error('Fallback emit also failed:', fallbackError);
    }
  }
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleString('fr-FR');
}

onMounted(() => {
  fetchQuestions();
});
</script>

<style scoped>
.source-detail {
  max-width: 1200px;
  margin: 0 auto;
}
</style> 