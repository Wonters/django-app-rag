<template>
  <div>
    <h2>{{ $t('Liste des collections') }}</h2>
    <div class="mb-3 text-end">
      <button class="btn btn-success" @click="showCreateCollection = true">
        <i class="bi bi-plus-lg"></i> {{ $t('Créer une collection') }}
      </button>
    </div>
    
    <!-- Tableau des collections -->
    <div>
      <table ref="tableRef" id="collections-table" class="table table-striped" style="width:100%">
        <thead>
          <tr>
            <th>{{ $t('ID', 2) }}</th>
            <th>{{ $t('Titre', 2) }}</th>
            <th>{{ $t('Description', 2) }}</th>
            <th>{{ $t('Documents', 2) }}</th>
            <th>{{ $t('Créé le', 2) }}</th>
            <th>{{ $t('Actions', 2) }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="collection in collections" :key="collection.id" @click="viewCollection(collection.id)" style="cursor: pointer;">
            <td>{{ collection.id }}</td>
            <td>
              <strong>{{ collection.title }}</strong>
            </td>
            <td>{{ collection.description || '-' }}</td>
            <td>
              <span class="badge bg-info">{{ collection.sources_count || 0 }}</span>
            </td>
            <td>{{ formatDate(collection.created_at) }}</td>
            <td @click.stop>
              <button class="btn btn-danger" @click="deleteCollection(collection.id)" data-bs-toggle="tooltip" data-bs-placement="top" :title="$t('Delete', 1)">
                <i class="bi bi-trash"></i>
              </button>
              <button class="btn btn-primary mx-2" @click="editCollection(collection.id)" data-bs-toggle="tooltip" data-bs-placement="top" :title="$t('Edit', 1)">
                <i class="bi bi-pencil"></i>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import apiService from './services/apiService.js';
import { useTooltips } from './composables/useTooltips';
import { useDataTable } from './composables/useDataTable';

const { t } = useI18n();

// Props et emits
const props = defineProps({
  collections: {
    type: Array,
    required: true,
    default: () => []
  }
});

const emit = defineEmits(['view-collection', 'edit-collection', 'delete-collection', 'create-collection']);

// État local
const showCreateCollection = ref(false);

// Utilisation des composables
const { initTooltips } = useTooltips();
const { tableRef, initDataTable, destroyDataTable } = useDataTable();

// Fonctions
function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleString('fr-FR');
}

function viewCollection(id) {
  console.log('View collection', id);
  emit('view-collection', id);
}

function editCollection(id) {
  console.log('Edit collection', id);
  emit('edit-collection', id);
}

function deleteCollection(id) {
  if (confirm(t('Êtes-vous sûr de vouloir supprimer cette collection ?'))) {
    emit('delete-collection', id);
  }
}

// Lifecycle
onMounted(async () => {
  await nextTick();
  // Initialisation des tooltips Bootstrap
  initTooltips();
});

watch(() => props.collections, async () => {
  destroyDataTable();
  await nextTick();
  initDataTable();
  // Réinitialisation des tooltips après mise à jour du DOM
  initTooltips();
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

.table tbody tr:hover {
  background-color: rgba(0, 123, 255, 0.1) !important;
}
</style> 