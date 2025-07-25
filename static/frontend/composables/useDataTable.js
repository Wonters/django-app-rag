import { ref, onBeforeUnmount } from 'vue';
import $ from 'jquery';
import 'datatables.net-bs5';

export function useDataTable(options = {}) {
  const tableRef = ref(null);
  let dataTableInstance = null;
  let isInitializing = false;

  const defaultOptions = {
    pageLength: 10,
    lengthMenu: [[5, 10, 25, 50], [5, 10, 25, 50]],
    order: [[0, 'asc']],
    columnDefs: [],
    responsive: true,
    language: {
      // url: '//cdn.datatables.net/plug-ins/1.13.7/i18n/fr-FR.json'
    },
    ...options
  };

  function initDataTable() {
    if (isInitializing) {
      console.warn('DataTable initialization already in progress, skipping');
      return;
    }
    
    if (!tableRef.value || !document.contains(tableRef.value)) {
      console.warn('Table element not found or not in DOM, skipping DataTable initialization');
      return;
    }
    
    // Vérifier si l'élément a un parentNode (nécessaire pour DataTables)
    if (!tableRef.value.parentNode) {
      console.warn('Table element has no parentNode, skipping DataTable initialization');
      return;
    }
    
    isInitializing = true;
    
    try {
      // Détruire l'instance existante si elle existe
      if (dataTableInstance) {
        try {
          dataTableInstance.destroy();
        } catch (error) {
          console.warn('Error destroying existing DataTable instance:', error);
        }
        dataTableInstance = null;
      }
      
      // Vérifier si DataTables est déjà initialisé sur ce tableau
      if ($.fn.dataTable.isDataTable(tableRef.value)) {
        try {
          $(tableRef.value).DataTable().destroy();
        } catch (error) {
          console.warn('Error destroying existing jQuery DataTable:', error);
        }
      }
      
      // Vérifier à nouveau que l'élément existe et est dans le DOM
      if (!tableRef.value || !document.contains(tableRef.value)) {
        console.warn('Table element no longer available after cleanup, skipping initialization');
        return;
      }
      
      // Créer une nouvelle instance
      dataTableInstance = $(tableRef.value).DataTable(defaultOptions);
      console.log('DataTable initialized successfully');
    } catch (error) {
      console.warn('Erreur lors de l\'initialisation du DataTable:', error);
      dataTableInstance = null;
    } finally {
      isInitializing = false;
    }
  }

  function destroyDataTable() {
    if (dataTableInstance && tableRef.value) {
      try {
        // Vérifier si le tableau est toujours dans le DOM et s'il a un parentNode
        if (document.contains(tableRef.value) && tableRef.value.parentNode) {
          // Vérifier si DataTables est initialisé avant de le détruire
          if ($.fn.dataTable.isDataTable(tableRef.value)) {
            dataTableInstance.destroy();
          }
        } else {
          console.warn('Table element not in DOM or has no parentNode, skipping DataTable destruction');
        }
      } catch (error) {
        console.warn('Erreur lors de la destruction du DataTable:', error);
      }
      dataTableInstance = null;
    }
  }

  function refreshDataTable() {
    if (dataTableInstance) {
      try {
        dataTableInstance.draw();
      } catch (error) {
        console.warn('Error refreshing DataTable:', error);
      }
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