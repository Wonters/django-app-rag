import { ref, onBeforeUnmount } from 'vue';
import { Tooltip } from 'bootstrap';

export function useTooltips() {
  const tooltipInstances = ref([]);

  function initTooltips() {
    // Détruire les tooltips existants
    destroyTooltips();
    
    try {
      // Initialiser les nouveaux tooltips
      const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
      tooltipTriggerList.forEach(tooltipTriggerEl => {
        // Vérifier si l'élément existe et n'a pas déjà un tooltip
        if (tooltipTriggerEl && !tooltipTriggerEl._tooltip) {
          try {
            const tooltip = new Tooltip(tooltipTriggerEl);
            tooltipInstances.value.push(tooltip);
          } catch (error) {
            console.warn('Erreur lors de l\'initialisation du tooltip:', error);
          }
        }
      });
    } catch (error) {
      console.warn('Erreur lors de l\'initialisation des tooltips:', error);
    }
  }

  function destroyTooltips() {
    tooltipInstances.value.forEach(tooltip => {
      if (tooltip && typeof tooltip.dispose === 'function') {
        try {
          // Vérifier si l'élément associé au tooltip existe encore
          if (tooltip._element && document.contains(tooltip._element)) {
            tooltip.dispose();
          }
        } catch (error) {
          console.warn('Erreur lors de la destruction du tooltip:', error);
        }
      }
    });
    tooltipInstances.value = [];
  }

  // Nettoyer automatiquement les tooltips lors de la destruction du composant
  onBeforeUnmount(() => {
    destroyTooltips();
  });

  return {
    initTooltips,
    destroyTooltips,
    tooltipInstances
  };
} 