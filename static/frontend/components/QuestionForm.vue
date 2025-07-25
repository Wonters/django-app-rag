<template>
  <div class="modal fade" tabindex="-1" :class="{ show: show }" style="display: block;" v-if="show" @click.self="close">
    <div class="modal-dialog modal-lg">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">
            {{ question ? $t('Modifier la question') : $t('Ajouter une question') }}
          </h5>
          <button type="button" class="btn-close" @click="close"></button>
        </div>
        <div class="modal-body p-0">
          <iframe
            ref="iframe"
            :src="currentFormUrl"
            style="width:100%;height:500px;border:none;overflow:auto;"
            @load="onIframeLoad"
          ></iframe>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" @click="close">
            {{ $t('Annuler') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue';
import { useErrorHandler } from '../composables/useErrorHandler.js';

// Utilisation du composable d'erreur
const { logger } = useErrorHandler();

const props = defineProps({
  show: Boolean,
  sourceId: {
    type: [String, Number],
    required: true
  },
  question: {
    type: Object,
    default: null
  },
  formUrl: {
    type: String,
    required: true
  }
});

const emit = defineEmits(['close', 'success']);
const iframe = ref(null);

// Computed pour l'URL du formulaire avec les paramètres
const currentFormUrl = computed(() => {
  let url = props.formUrl;
  
  // Ajouter le source_id comme paramètre
  const separator = url.includes('?') ? '&' : '?';
  url += `${separator}source_id=${props.sourceId}`;
  
  // Si on modifie une question existante, ajouter l'ID
  if (props.question && props.question.id) {
    url += `&question_id=${props.question.id}`;
  }
  
  return url;
});

function onIframeLoad() {
  try {
    const currentUrl = iframe.value?.contentWindow?.location?.pathname;
    const formUrlPath = new URL(props.formUrl, window.location.origin).pathname;
    
    logger.log('Iframe loaded, current URL:', currentUrl, 'form URL path:', formUrlPath);
    
    if (currentUrl && currentUrl === formUrlPath) {
      // On ne ferme pas, c'est le formulaire affiché
      logger.log('Form displayed, not closing');
    } else {
      // On ferme si redirection (après POST)
      logger.log('Form submitted, closing and emitting success');
      close();
      emit('success');
    }
  } catch (e) {
    logger.log('Cross-origin error, closing modal:', e);
    // Cross-origin, on ferme par sécurité
    close();
  }
}

// Améliorer la gestion de la fermeture manuelle
function close() {
  logger.log('Closing question form');
  emit('close');
}

// Ajouter une méthode pour détecter la soumission du formulaire
function handleFormSubmission() {
  logger.log('Form submission detected');
  close();
  emit('success');
}

// Reset iframe src when popup opens or props change
watch([() => props.show, () => props.question, () => props.sourceId], ([show, question, sourceId]) => {
  if (show && iframe.value) {
    iframe.value.src = currentFormUrl.value;
  }
});
</script>

<style scoped>
.modal {
  background: rgba(0,0,0,0.4);
  z-index: 1050;
}

.modal-dialog {
  max-width: 800px;
}
</style> 