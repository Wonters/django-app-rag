<template>
  <div>
    <table ref="tableRef" id="documents-table" class="table table-striped" style="width:100%">
      <thead>
        <tr>
          <th>{{ t('ID', 2) }}</th>
          <th>{{ t('Source name', 2) }}</th>
          <th>{{ t('Type', 2) }}</th>
          <th>{{ t('Questions', 2) }}</th>
          <th>{{ t('Answers', 2) }}</th>
          <th>{{ t('Actions', 2) }}</th>
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
            <button class="btn btn-danger" @click="deleteSource(source.id)" data-bs-toggle="tooltip" data-bs-placement="top" :title="t('Delete', 1)">
              <i class="bi bi-trash"></i>
            </button>
            <button class="btn btn-primary mx-2" @click="editSource(source.id)" data-bs-toggle="tooltip" data-bs-placement="top" :title="t('Edit', 1)">
              <i class="bi bi-pencil"></i>
            </button>
            <button class="btn btn-info" @click="viewSourceDetails(source.id)" data-bs-toggle="tooltip" data-bs-placement="top" :title="t('Voir détails', 1)">
              <i class="bi bi-eye"></i>
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { onMounted, nextTick, watch } from 'vue';
import { useI18n } from 'vue-i18n';
const { t } = useI18n();
import 'bootstrap/dist/css/bootstrap.min.css';
import 'datatables.net-bs5/css/dataTables.bootstrap5.min.css';
import 'bootstrap/dist/js/bootstrap.bundle.min.js';
import { useTooltips } from './composables/useTooltips';
import { useDataTable } from './composables/useDataTable';

const props = defineProps({
  sources: {
    type: Array,
    required: true,
    default: () => []
  },
  detailUrl: {
    type: String,
    required: true,
    default: () => ''
  }
});

const emit = defineEmits(['edit', 'view-details', 'delete']);

// Utilisation des composables
const { initTooltips } = useTooltips();
const { tableRef, initDataTable, destroyDataTable } = useDataTable();

function getFileName(path) {
  if (!path) return '';
  return path.split('/').pop();
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleString('fr-FR');
}

function editSource(id) {
  // On émet un événement pour demander l'édition au parent
  console.log('Edit source', id);
  emit('edit', id);
}

function deleteSource(id) {
  if (confirm(t('Êtes-vous sûr de vouloir supprimer cette source ?'))) {
    emit('delete', id);
  }
}

function viewSourceDetails(id) {
  console.log('View source details', id);
  emit('view-details', id);
}

onMounted(async () => {
  await nextTick();
  // Initialisation des tooltips Bootstrap
  initTooltips();
});

watch(() => props.sources, async () => {
  destroyDataTable();
  await nextTick();
  initDataTable();
  // Réinitialisation des tooltips après mise à jour du DOM
  initTooltips();
});
</script> 