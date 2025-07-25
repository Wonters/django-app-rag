<template>
  <div class="modal fade" tabindex="-1" :class="{ show: show }" style="display: block;" v-if="show" @click.self="close">
    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">{{ $t('Ajouter une source') }}</h5>
          <button type="button" class="btn-close" @click="close"></button>
        </div>
        <div class="modal-body p-0">
          <iframe
            ref="iframe"
            :src="formUrl"
            style="width:100%;height:340px;border:none;overflow:auto;"
            @load="onIframeLoad"
          ></iframe>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';

const props = defineProps({
  show: Boolean,
  formUrl: {
    type: String,
    required: true
  }
});
const emit = defineEmits(['close', 'success']);
const iframe = ref(null);

function close() {
  emit('close');
}

function onIframeLoad() {
  try {
    const currentUrl = iframe.value?.contentWindow?.location?.pathname;
    const formUrlPath = new URL(props.formUrl, window.location.origin).pathname;
    
    if (currentUrl && currentUrl === formUrlPath) {
      // On ne ferme pas, c'est le formulaire affiché
    } else {
      // On ferme si redirection (après POST) et on émet un événement de succès
      emit('success');
      close();
    }
  } catch (e) {
    // Cross-origin, on ferme par sécurité
    close();
  }
}

// Reset iframe src when popup opens
watch(() => props.show, (val) => {
  if (val && iframe.value) {
    iframe.value.src = props.formUrl;
  }
});
</script>

<style scoped>
.modal {
  background: rgba(0,0,0,0.4);
  z-index: 1050;
}
</style> 