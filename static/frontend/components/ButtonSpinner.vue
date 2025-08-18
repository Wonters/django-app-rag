<template>
  <div>
    <!-- Spinner pour running -->
    <span v-if="status === 'running'" class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
    
    <!-- Icône pour pending -->
    <i v-else-if="status === 'pending'" class="bi bi-clock"></i>
    
    <!-- Icône warning pour failed -->
    <i v-else-if="status === 'failed'" class="bi bi-exclamation-triangle"></i>
    
    <!-- Icône personnalisée pour completed ou pas de statut -->
    <i v-else :class="defaultIconClass"></i>
  </div>
</template>

<script setup>
import { defineProps } from 'vue';

const props = defineProps({
  status: {
    type: String,
    default: null,
    validator: (value) => ['running', 'pending', 'failed', 'completed', null].includes(value)
  },
  defaultIconClass: {
    type: String,
    default: 'bi bi-robot'
  }
});
</script>
