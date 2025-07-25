import { ref, onBeforeUnmount } from 'vue';
import $ from 'jquery';
import 'datatables.net-bs5';

export function useDataTable(options = {}) {
  const tableRef = ref(null);
  let dataTableInstance = null;

  const defaultOptions = {
    pageLength: 10,
    lengthMenu: [[5, 10, 25, 50], [5, 10, 25, 50]],
    order: [[0, 'asc']],
    columnDefs: [],
    ...options
  };

  function initDataTable() {
    if (!tableRef.value || !document.contains(tableRef.value)) return;
    
    try {
      // Détruire l'instance existante si elle existe
      if (dataTableInstance) {
        dataTableInstance.destroy();
        dataTableInstance = null;
      }
      
      // Vérifier si DataTables est déjà initialisé sur ce tableau
      if ($.fn.dataTable.isDataTable(tableRef.value)) {
        $(tableRef.value).DataTable().destroy();
      }
      
      // Créer une nouvelle instance
      dataTableInstance = $(tableRef.value).DataTable(defaultOptions);
    } catch (error) {
      console.warn('Erreur lors de l\'initialisation du DataTable:', error);
    }
  }

  function destroyDataTable() {
    if (dataTableInstance && tableRef.value) {
      try {
        // Vérifier si le tableau est toujours dans le DOM et s'il a un parentNode
        if (document.contains(tableRef.value) && tableRef.value.parentNode) {
          // Détruire les tooltips avant de détruire DataTables pour éviter les conflits
          const tooltipElements = tableRef.value.querySelectorAll('[data-bs-toggle="tooltip"]');
          tooltipElements.forEach(element => {
            if (element._tooltip) {
              try {
                element._tooltip.dispose();
              } catch (error) {
                console.warn('Erreur lors de la destruction du tooltip:', error);
              }
            }
          });
          
          // Vérifier si DataTables est initialisé avant de le détruire
          if ($.fn.dataTable.isDataTable(tableRef.value)) {
            dataTableInstance.destroy();
          }
        }
      } catch (error) {
        console.warn('Erreur lors de la destruction du DataTable:', error);
      }
      dataTableInstance = null;
    }
  }

  function refreshDataTable() {
    if (dataTableInstance) {
      dataTableInstance.draw();
    }
  }

  // Nettoyer automatiquement lors de la destruction du composant
  onBeforeUnmount(() => {
    destroyDataTable();
  });

  return {
    tableRef,
    initDataTable,
    destroyDataTable,
    refreshDataTable,
    dataTableInstance: ref(dataTableInstance)
  };
} 