<template>
  <div 
    v-if="confirmationModal.show" 
    class="confirmation-modal-overlay"
    @click="handleOverlayClick"
  >
    <div class="confirmation-modal" @click.stop>
      <div class="confirmation-modal-header">
        <h5 class="confirmation-modal-title">
          <i class="bi bi-exclamation-triangle-fill text-warning me-2"></i>
          {{ confirmationModal.title }}
        </h5>
        <button 
          type="button" 
          class="btn-close" 
          @click="handleCancel"
          :title="$t('Fermer')"
        ></button>
      </div>
      
      <div class="confirmation-modal-body">
        <p class="confirmation-modal-message">
          {{ confirmationModal.message }}
        </p>
      </div>
      
      <div class="confirmation-modal-footer">
        <button 
          type="button" 
          class="btn btn-secondary" 
          @click="handleCancel"
        >
          {{ confirmationModal.cancelText }}
        </button>
        <button 
          type="button" 
          class="btn btn-danger" 
          @click="handleConfirm"
        >
          {{ confirmationModal.confirmText }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  confirmationModal: {
    type: Object,
    required: true,
    default: () => ({
      show: false,
      title: '',
      message: '',
      confirmText: '',
      cancelText: '',
      onConfirm: null,
      onCancel: null
    })
  }
});

const emit = defineEmits(['confirm', 'cancel']);

function handleConfirm() {
  if (props.confirmationModal.onConfirm) {
    props.confirmationModal.onConfirm();
  }
  emit('confirm');
}

function handleCancel() {
  if (props.confirmationModal.onCancel) {
    props.confirmationModal.onCancel();
  }
  emit('cancel');
}

function handleOverlayClick() {
  handleCancel();
}
</script>

<style scoped>
.confirmation-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 20px;
}

.confirmation-modal {
  background: white;
  border-radius: 12px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
  max-width: 500px;
  width: 100%;
  animation: modalSlideIn 0.3s ease;
}

@keyframes modalSlideIn {
  from {
    opacity: 0;
    transform: translateY(-20px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.confirmation-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 0;
  border-bottom: 1px solid #e9ecef;
  padding-bottom: 16px;
}

.confirmation-modal-title {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: #333;
  display: flex;
  align-items: center;
}

.confirmation-modal-body {
  padding: 20px 24px;
}

.confirmation-modal-message {
  margin: 0;
  font-size: 1rem;
  line-height: 1.5;
  color: #555;
}

.confirmation-modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 0 24px 20px;
}

.btn {
  padding: 8px 20px;
  font-size: 0.9rem;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.btn-secondary {
  background: #6c757d;
  border: 1px solid #6c757d;
  color: white;
}

.btn-secondary:hover {
  background: #5a6268;
  border-color: #545b62;
}

.btn-danger {
  background: #dc3545;
  border: 1px solid #dc3545;
  color: white;
}

.btn-danger:hover {
  background: #c82333;
  border-color: #bd2130;
}

.btn-close {
  background: none;
  border: none;
  font-size: 1.2rem;
  color: #666;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.btn-close:hover {
  background: rgba(0, 0, 0, 0.1);
  color: #333;
}

/* Responsive */
@media (max-width: 768px) {
  .confirmation-modal-overlay {
    padding: 10px;
  }
  
  .confirmation-modal {
    max-width: none;
  }
  
  .confirmation-modal-header,
  .confirmation-modal-body,
  .confirmation-modal-footer {
    padding-left: 20px;
    padding-right: 20px;
  }
  
  .confirmation-modal-footer {
    flex-direction: column-reverse;
  }
  
  .btn {
    width: 100%;
    justify-content: center;
  }
}
</style> 