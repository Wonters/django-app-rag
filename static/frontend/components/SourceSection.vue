<template>
  <div class="card">
    <div class="card-header">
      <h5 class="mb-0">
        <span v-if="currentView === 'list'">
          {{ selectedCollection ? `${$t('Documents de')} "${selectedCollection.title}"` : $t('Sélectionnez une collection pour voir ses documents') }}
        </span>
        <span v-else-if="currentView === 'detail' && selectedSource">
          {{ $t('Détails du document') }} : {{ selectedSource.title }}
        </span>
      </h5>
    </div>
    <div class="card-body">
      <!-- Vue liste des documents -->
      <SourceList 
        v-if="currentView === 'list' && selectedCollection"
        :collection-id="selectedCollection.id"
        :selected-collection="selectedCollection"
        @refresh="$emit('refresh')"
        @view-details="viewSourceDetails"
      />
      
      <!-- Vue détail d'une source -->
      <SourceDetail 
        v-if="currentView === 'detail' && selectedSource"
        :source="selectedSource"
        @back="goBackToList"
      />
      
      <!-- Message si aucune collection sélectionnée -->
      <div v-if="!selectedCollection" class="text-center text-muted py-5">
        <i class="bi bi-file-text display-1"></i>
        <p class="mt-3">{{ $t('Cliquez sur une collection pour voir ses documents') }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import SourceList from './SourceList.vue';
import SourceDetail from './SourceDetail.vue';
import { useErrorHandler } from '../composables/useErrorHandler.js';

const { t } = useI18n();
const { logger } = useErrorHandler();

const props = defineProps({
  selectedCollection: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['refresh']);

// État de navigation
const currentView = ref('list'); // 'list' ou 'detail'
const selectedSource = ref(null);

// Fonctions de navigation
function viewSourceDetails(source) {
  try {
    logger.log('Switching to detail view for source:', source.id);
    selectedSource.value = source;
    currentView.value = 'detail';
  } catch (error) {
    logger.error('Error switching to detail view:', error);
  }
}

function goBackToList() {
  try {
    logger.log('Returning to list view');
    currentView.value = 'list';
    selectedSource.value = null;
  } catch (error) {
    logger.error('Error returning to list view:', error);
  }
}

// Watcher pour réinitialiser la vue quand la collection change
watch(() => props.selectedCollection, (newCollection, oldCollection) => {
  if (newCollection?.id !== oldCollection?.id) {
    logger.log('Collection changed, resetting to list view');
    currentView.value = 'list';
    selectedSource.value = null;
  }
});
</script> 