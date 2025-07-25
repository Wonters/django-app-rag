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
      @question-saved="handleQuestionSaved"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import QuestionList from './QuestionList.vue';
import QuestionForm from './QuestionForm.vue';
import apiService from './services/apiService.js';

const { t } = useI18n();

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

// URLs pour les API
const questionApiUrl = window.QUESTION_API_URL || '/api/questions/';
const questionFormUrl = window.QUESTION_FORM_URL || '/questions/create/';
const questionEditUrl = window.QUESTION_EDIT_URL || '/questions/edit/';

// Computed pour l'URL du formulaire de question
const currentQuestionFormUrl = computed(() => {
  if (editingQuestion.value && editingQuestion.value.id) {
    return questionEditUrl.replace('__pk__', editingQuestion.value.id);
  }
  return questionFormUrl;
});

function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleString('fr-FR');
}

async function fetchQuestions() {
  try {
    isLoading.value = true;
    
    // Ajouter un timestamp pour éviter le cache
    const timestamp = new Date().getTime();
    const url = `${questionApiUrl}?source=${props.source.id}&_t=${timestamp}`;
    
    const response = await apiService.get(url);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    questions.value = Array.isArray(data) ? data : (data.results || []);
    
    console.log('Questions chargées avec succès:', questions.value.length);
  } catch (error) {
    console.error('Erreur lors du chargement des questions:', error);
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
  if (confirm(t('Êtes-vous sûr de vouloir supprimer cette question ?'))) {
    deleteQuestion(questionId);
  }
}

async function deleteQuestion(questionId) {
  try {
    console.log('Suppression de la question:', questionId);
    const response = await apiService.deleteWithCsrfFetch(`${questionApiUrl}${questionId}/`);
    
    if (response.ok) {
      console.log('Question supprimée avec succès');
      // Rafraîchir immédiatement la liste
      await fetchQuestions();
    } else {
      console.error('Erreur lors de la suppression de la question:', response.status);
      alert(t('Erreur lors de la suppression de la question'));
    }
  } catch (error) {
    console.error('Erreur lors de la suppression:', error);
    alert(t('Erreur lors de la suppression de la question'));
  }
}

function closeQuestionForm() {
  showQuestionForm.value = false;
  editingQuestion.value = null;
}

function handleQuestionSaved() {
  closeQuestionForm();
  
  // Ajouter un délai pour s'assurer que les données sont sauvegardées côté serveur
  setTimeout(async () => {
    console.log('Rafraîchissement des questions après sauvegarde...');
    await fetchQuestions();
  }, 500);
}

function handleQuestionFormClosed() {
  // Si le formulaire est fermé sans sauvegarde, on ne fait rien
  console.log('Formulaire fermé sans sauvegarde');
}

async function handleBack() {
  try {
    console.log('handleBack called');
    console.log('Emitting back event');
    
    // Add a small delay to ensure proper event processing
    await new Promise(resolve => setTimeout(resolve, 10));
    
    emit('back');
    console.log('Back event emitted successfully');
  } catch (error) {
    console.error('Error in handleBack:', error);
    // Try to emit the event again as a fallback
    try {
      emit('back');
    } catch (fallbackError) {
      console.error('Fallback emit also failed:', fallbackError);
    }
  }
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