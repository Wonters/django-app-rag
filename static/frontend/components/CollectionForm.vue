<template>
  <div v-if="show" class="modal fade show d-block" tabindex="-1" style="background-color: rgba(0,0,0,0.5);">
    <div class="modal-dialog modal-lg">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">{{ isEdit ? $t('Modifier la collection') : $t('Créer une collection') }}</h5>
          <button type="button" class="btn-close" @click="closeForm"></button>
        </div>
        <div class="modal-body p-0">
          <iframe 
            :src="formUrl" 
            width="100%" 
            height="500px" 
            frameborder="0"
            @load="handleIframeLoad"
            ref="iframeRef"
          ></iframe>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  collection: {
    type: Object,
    default: null
  },
  formUrl: {
    type: String,
    required: true
  }
});

const emit = defineEmits(['close', 'success']);

// État local
const iframeRef = ref(null);
const initialUrl = ref(null);

// Computed
const isEdit = computed(() => props.collection !== null);

// Watcher pour réinitialiser l'URL initiale quand le formulaire s'ouvre
watch(() => props.show, (newShow) => {
  if (newShow) {
    initialUrl.value = null;
  }
});

// Fonctions
function closeForm() {
  emit('close');
}

function handleIframeLoad() {
  try {
    const currentUrl = iframeRef.value?.contentWindow?.location?.href;
    
    // Si c'est le premier chargement, on sauvegarde l'URL initiale
    if (!initialUrl.value) {
      initialUrl.value = currentUrl;
      return;
    }
    
    // Si l'URL a changé par rapport à l'URL initiale, on ferme le formulaire
    if (currentUrl !== initialUrl.value) {
      closeForm();
      emit('success');
    }
  } catch (e) {
    // Cross-origin, on ferme par sécurité
    closeForm();
  }
}

</script>

<style scoped>
.modal {
  z-index: 1050;
}

.modal-dialog {
  max-width: 800px;
}

.modal-body {
  min-height: 500px;
}

iframe {
  border: none;
}
</style> 