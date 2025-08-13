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
                <div v-if="question.answer" class="answer-item mb-2">
                  <div class="answer-text">
                    <p class="mb-1"><strong>{{ question.answer.title }}</strong></p>
                    <p class="mb-1">{{ question.answer.field }}</p>
                    <div v-if="question.answer.documents && question.answer.documents.length > 0" class="mt-2">
                      <small class="text-muted">
                        <strong>{{ $t('Sources utilisées') }}:</strong>
                        <div class="table-responsive mt-2">
                          <table class="table table-sm table-borderless mb-0">
                            <thead>
                              <tr>
                                <th class="text-muted small">{{ $t('Nom') }}</th>
                                <th class="text-muted small">{{ $t('Lien') }}</th>
                                <th class="text-muted small">{{ $t('Score') }}</th>
                              </tr>
                            </thead>
                            <tbody>
                              <tr v-for="document in question.answer.documents" :key="document.uid">
                                <td>
                                  <i class="bi bi-link-45deg"></i>
                                  <span v-if="document.title">{{ document.title }}</span>
                                  <span v-else class="text-muted">{{ document.uid }}</span>
                                </td>
                                <td>
                                  <span v-if="document.url">
                                    <a :href="document.url" target="_blank" class="text-decoration-none">
                                      <i class="bi bi-box-arrow-up-right"></i> {{ $t('Ouvrir') }}
                                    </a>
                                  </span>
                                  <span v-else class="text-muted">-</span>
                                </td>
                                <td>
                                  <span v-if="document.similarity_score" class="badge bg-secondary">
                                    {{ (document.similarity_score * 100).toFixed(1) }}%
                                  </span>
                                  <span v-else class="text-muted">-</span>
                                </td>
                              </tr>
                            </tbody>
                          </table>
                        </div>
                      </small>
                    </div>
                  </div>
                </div>
                <div v-else class="text-muted">
                  <i class="bi bi-dash"></i> {{ $t('Aucune réponse') }}
                </div>
              </div>
            </td>
            <td>
              <div class="btn-group" role="group">
                <button class="btn btn-sm btn-outline-primary" @click="editQuestion(question)" :title="$t('Modifier')"
                  data-bs-toggle="tooltip" data-bs-placement="top">
                  <i class="bi bi-pencil"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger" @click="deleteQuestion(question.id)"
                  :title="$t('Supprimer')" data-bs-toggle="tooltip" data-bs-placement="top">
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
import { useTooltips } from '../composables/useTooltips';
import { useDataTable } from '../composables/useDataTable';
import { useErrorHandler } from '../composables/useErrorHandler.js';

const { t } = useI18n();

// Utilisation du composable d'erreur
const { logger } = useErrorHandler();

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
  order: [[1, 'desc']], // Trier par la colonne des réponses (maintenant index 1)
  columnDefs: [
    {
      targets: [2], // Colonne des actions (maintenant index 2)
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
    logger.warn('Erreur lors de l\'initialisation du tableau:', error);
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
    logger.warn('Erreur lors de la mise à jour du tableau:', error);
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
  width: 100%;
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

.answer-item {
  border-left: 3px solid #007bff;
  padding-left: 0.75rem;
  background-color: #f8f9fa;
  border-radius: 0.25rem;
  padding: 0.5rem;
}

.answer-item:not(:last-child) {
  margin-bottom: 0.75rem;
}

.answer-text p:first-child {
  color: #495057;
  font-weight: 600;
}

.answer-text p:nth-child(2) {
  color: #6c757d;
  font-style: italic;
}

.badge {
  font-size: 0.7rem;
}

.table-sm th {
  font-size: 0.75rem;
  font-weight: 600;
  color: #6c757d;
  border-bottom: 1px solid #dee2e6;
  padding: 0.25rem;
}

.table-sm td {
  font-size: 0.8rem;
  padding: 0.25rem;
  vertical-align: middle;
}

.table-borderless {
  border: none;
}

.table-borderless th,
.table-borderless td {
  border: none;
}

/* Responsive pour les petits écrans */
@media (max-width: 768px) {
  .answer-content {
    width: 100%;
    max-height: 150px;
  }
  
  .btn-group .btn {
    padding: 0.25rem 0.5rem;
    font-size: 0.8rem;
  }
  
  .answer-item {
    padding: 0.25rem;
    margin-bottom: 0.5rem;
  }
}
</style>