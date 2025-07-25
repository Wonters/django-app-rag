<template>
  <div id="app">
    <div class="text-end mb-2">
      <select class="select-lang text-primary" v-model="$i18n.locale">
        <option class="text-primary" value="fr">FR</option>
        <option class="text-primary" value="en">EN</option>
      </select>
    </div>
    <div> {{ $t('Test') }}</div>
    <h1>{{ $t('Bienvenue sur le RAG Django') }}</h1>
    <p class="text-center">{{ $t('Intégration Vue 3 + Vite + Django') }}</p>
    <p class="text-center">{{ $t('Vous pouvez modifier le contenu de ce fichier dans le dossier frontend') }}</p>
    <hr />
    <h2>{{ $t('Liste des documents') }}</h2>
    <div class="mb-3 text-end">
      <button class="btn btn-success" @click="showUpload = true">
        <i class="bi bi-plus-lg"></i> {{ $t('Ajouter un document') }}
      </button>
    </div>
    <SourceForm :show="showUpload" :form-url="sourceFormUrl" @close="showUpload = false" />
    <SourceForm :show="showEdit" :form-url="editFormUrl" @close="showEdit = false" />
    <DocumentTable :sources="sources" :detail-url="sourceDetailUrl" @edit="handleEditSource" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import DocumentTable from './DocumentTable.vue';
import SourceForm from './SourceForm.vue';

const sources = ref([]);
const showUpload = ref(false);
const showEdit = ref(false);
const editFormUrl = ref('');
// L'URL du formulaire sera injectée dynamiquement dans le template Django principal
const sourceFormUrl = window.SOURCE_FORM_URL;
const sourceApiUrl = window.SOURCE_API_URL;  
const sourceEditUrl = window.SOURCE_EDIT_URL;
function getFileName(path) {
  if (!path) return '';
  return path.split('/').pop();
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleString('fr-FR');
}

async function fetchSources() {
  const res = await fetch(window.SOURCE_API_URL);
  const data = await res.json();
  const docs = Array.isArray(data) ? data : (data.results || []);
  sources.value = docs.map(doc => ({
    ...doc,
  }));
}

function handleSourceSubmit(data) {
  // Ici, tu pourras faire l'appel API pour créer la source
  console.log('Source à créer:', data);
  // TODO: POST vers l'API, puis refresh la liste si besoin
}

function handleEditSource(id) {
  editFormUrl.value = sourceEditUrl.replace('__pk__', id);
  showEdit.value = true;
}

onMounted(() => {
  fetchSources();
});
</script>

<style scoped>
h1 {
  color: #42b983;
}
</style> 