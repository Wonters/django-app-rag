<template>
  <div class="question-list">
    <div v-if="questions.length === 0" class="text-center py-4">
      <i class="bi bi-chat-dots fs-1 text-muted"></i>
      <p class="text-muted mt-2">{{ $t('Aucune question pour cette source') }}</p>
    </div>
    
    <div v-else>
      <table ref="tableRef" id="questions-table" class="table table-striped" style="width:100%">
        <thead>
          <tr>
            <th>{{ $t('Question') }}</th>
            <th>{{ $t('Réponse') }}</th>
            <th>{{ $t('Date de création') }}</th>
            <th>{{ $t('Actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="question in questions" :key="question.id">
            <td>
              <div class="question-title">{{ question.title }}</div>
              <small class="text-muted">{{ question.field }}</small>
            </td>
            <td>
              <div class="answer-content">
                <div v-if="question.answer">
                  <div v-if="question.answer.is_loading" class="text-center">
                    <div class="spinner-border spinner-border-sm" role="status">
                      <span class="visually-hidden">{{ $t('Chargement...') }}</span>
                    </div>
                    <span class="ms-2">{{ $t('Génération de la réponse...') }}</span>
                  </div>
                  <div v-else-if="question.answer.error" class="alert alert-danger py-2">
                    <i class="bi bi-exclamation-triangle"></i>
                    {{ $t('Erreur lors de la génération de la réponse') }}: {{ question.answer.error }}
                  </div>
                  <div v-else>
                    <div class="answer-text">
                      <p class="mb-1">{{ question.answer.text }}</p>
                      <div v-if="question.answer.sources && question.answer.sources.length > 0" class="mt-2">
                        <small class="text-muted">
                          <strong>{{ $t('Sources utilisées') }}:</strong>
                          <ul class="list-unstyled mt-1 mb-0">
                            <li v-for="source in question.answer.sources" :key="source">
                              <i class="bi bi-link-45deg"></i> {{ source }}
                            </li>
                          </ul>
                        </small>
                      </div>
                    </div>
                  </div>
                </div>
                <div v-else class="text-muted">
                  <i class="bi bi-dash"></i> {{ $t('Aucune réponse') }}
                </div>
              </div>
            </td>
            <td>
              <div class="date-info">
                <div>{{ formatDate(question.created_at) }}</div>
                <small v-if="question.updated_at && question.updated_at !== question.created_at" class="text-muted">
                  {{ $t('Modifiée le') }} {{ formatDate(question.updated_at) }}
                </small>
              </div>
            </td>
            <td>
              <div class="btn-group" role="group">
                <button 
                  class="btn btn-sm btn-outline-primary" 
                  @click="editQuestion(question)"
                  :title="$t('Modifier')"
                  data-bs-toggle="tooltip" 
                  data-bs-placement="top"
                >
                  <i class="bi bi-pencil"></i>
                </button>
                <button 
                  class="btn btn-sm btn-outline-danger" 
                  @click="deleteQuestion(question.id)"
                  :title="$t('Supprimer')"
                  data-bs-toggle="tooltip" 
                  data-bs-placement="top"
                >
                  <i class="bi bi-trash"></i>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { watch, onMounted, onBeforeUnmount, nextTick, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import 'bootstrap/dist/css/bootstrap.min.css';
import 'datatables.net-bs5/css/dataTables.bootstrap5.min.css';
import 'bootstrap/dist/js/bootstrap.bundle.min.js';
import { useTooltips } from './composables/useTooltips';
import { useDataTable } from './composables/useDataTable';

const { t } = useI18n();

const props = defineProps({
  questions: {
    type: Array,
    required: true,
    default: () => []
  },
  sourceId: {
    type: [String, Number],
    required: true
  }
});

const emit = defineEmits(['edit-question', 'delete-question']);

// Variable pour suivre l'état du composant
const isComponentMounted = ref(false);

// Utilisation des composables
const { initTooltips, destroyTooltips } = useTooltips();
const { tableRef, initDataTable, destroyDataTable } = useDataTable({
  pageLength: 10,
  lengthMenu: [[5, 10, 25, 50], [5, 10, 25, 50]],
  order: [[2, 'desc']], // Trier par date de création décroissante
  columnDefs: [
    {
      targets: [3], // Colonne des actions
      orderable: false,
      searchable: false
    }
  ]
});

function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleString('fr-FR');
}

function editQuestion(question) {
  emit('edit-question', question);
}

function deleteQuestion(questionId) {
  emit('delete-question', questionId);
}

onMounted(async () => {
  isComponentMounted.value = true;
  try {
    await nextTick();
    if (props.questions && props.questions.length > 0 && isComponentMounted.value) {
      initDataTable();
    }
    // Initialisation des tooltips Bootstrap
    if (isComponentMounted.value) {
      initTooltips();
    }
  } catch (error) {
    console.warn('Erreur lors de l\'initialisation du tableau:', error);
  }
});

onBeforeUnmount(() => {
  isComponentMounted.value = false;
});

watch(() => props.questions, async () => {
  if (!isComponentMounted.value) return;
  
  try {
    // Détruire les tooltips en premier pour éviter les conflits avec DataTables
    destroyTooltips();
    
    // Détruire le tableau existant
    destroyDataTable();
    
    // Attendre que Vue ait terminé ses mises à jour DOM
    await nextTick();
    
    // Attendre un peu plus pour s'assurer que le DOM est stable
    await new Promise(resolve => setTimeout(resolve, 50));
    
    // Vérifier que le tableau existe toujours dans le DOM et que le composant est toujours monté
    if (tableRef.value && props.questions && props.questions.length > 0 && isComponentMounted.value) {
      initDataTable();
    }
    
    // Réinitialisation des tooltips après mise à jour du DOM
    if (isComponentMounted.value) {
      initTooltips();
    }
  } catch (error) {
    console.warn('Erreur lors de la mise à jour du tableau:', error);
  }
}, { deep: true });
</script>

<style scoped>
.question-list {
  max-width: 100%;
}

.question-title {
  font-weight: 500;
  color: #333;
  margin-bottom: 0.25rem;
}

.answer-content {
  max-width: 400px;
  max-height: 200px;
  overflow-y: auto;
}

.answer-text {
  line-height: 1.4;
}

.answer-text p {
  margin-bottom: 0.5rem;
}

.date-info {
  font-size: 0.9rem;
}

.btn-group .btn {
  margin-right: 0.25rem;
}

.btn-group .btn:last-child {
  margin-right: 0;
}

/* Responsive pour les petits écrans */
@media (max-width: 768px) {
  .answer-content {
    max-width: 250px;
    max-height: 150px;
  }
  
  .btn-group .btn {
    padding: 0.25rem 0.5rem;
    font-size: 0.8rem;
  }
}
</style> 