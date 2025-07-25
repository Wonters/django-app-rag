<template>
  <div>
    <table ref="tableRef" id="documents-table" class="table table-striped" style="width:100%">
      <thead>
        <tr>
          <th>{{ t('ID', 2) }}</th>
          <th>{{ t('Source name', 2) }}</th>
          <th>{{ t('Type', 2) }}</th>
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
            <button class="btn btn-danger" @click="deleteSource(source.id)" data-bs-toggle="tooltip" data-bs-placement="top" :title="t('Delete', 1)">
              <i class="bi bi-trash"></i>
            </button>
            <button class="btn btn-primary mx-2" @click="editSource(source.id)" data-bs-toggle="tooltip" data-bs-placement="top" :title="t('Edit', 1)">
              <i class="bi bi-pencil"></i>
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch, onBeforeUnmount, defineEmits } from 'vue';
import { useI18n } from 'vue-i18n';
const { t } = useI18n();
import $ from 'jquery';
import 'datatables.net-bs5';
import 'bootstrap/dist/css/bootstrap.min.css';
import 'datatables.net-bs5/css/dataTables.bootstrap5.min.css';
import { Tooltip } from 'bootstrap';
import 'bootstrap/dist/js/bootstrap.bundle.min.js';

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

const emit = defineEmits(['edit']);

const tableRef = ref(null);

function getFileName(path) {
  if (!path) return '';
  return path.split('/').pop();
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleString('fr-FR');
}

let dataTableInstance = null;

function initDataTable() {
  if (!tableRef.value) return;
  if ($.fn.dataTable.isDataTable(tableRef.value)) {
    $(tableRef.value).DataTable().destroy();
  }
  dataTableInstance = $(tableRef.value).DataTable();
}

function destroyDataTable() {
  if (dataTableInstance) {
    dataTableInstance.destroy();
    dataTableInstance = null;
  }
}

function editSource(id) {
  // On émet un événement pour demander l'édition au parent
  console.log('Edit source', id);
  emit('edit', id);
}

function deleteSource(id) {
  // À implémenter : suppression côté parent ou API
  // Ici, on évite juste l'erreur
  console.log('Suppression source', id);
}

onMounted(async () => {
  await nextTick();
  // Initialisation des tooltips Bootstrap
  const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  tooltipTriggerList.forEach(tooltipTriggerEl => {
    new Tooltip(tooltipTriggerEl);
  });
});

watch(() => props.sources, async () => {
  destroyDataTable();
  await nextTick();
  initDataTable();
  // Réinitialisation des tooltips après mise à jour du DOM
  const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  tooltipTriggerList.forEach(tooltipTriggerEl => {
    new Tooltip(tooltipTriggerEl);
  });
});

onBeforeUnmount(() => {
  destroyDataTable();
});
</script> 