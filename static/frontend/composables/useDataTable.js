import { ref } from 'vue';
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
    //language: {
      // url: '//cdn.datatables.net/plug-ins/1.13.7/i18n/fr-FR.json'
    //},
    ...options
  };

  function initDataTable() {
    if (isInitializing) {
      console.warn('DataTable initialization already in progress, skipping');
      return;
    }
    
    if (!tableRef.value) {
      console.warn('Table ref not available, skipping DataTable initialization');
      return;
    }
    
    // Vérifier que le tableau a des données avant d'initialiser DataTables
    if (!tableRef.value.querySelector('tbody tr')) {
      console.warn('Table has no data rows, skipping DataTable initialization');
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
      
      // Créer une nouvelle instance directement
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
    try {
      // Détruire l'instance locale si elle existe
      if (dataTableInstance) {
        try {
          dataTableInstance.destroy();
        } catch (error) {
          console.warn('Error destroying local DataTable instance:', error);
        }
        dataTableInstance = null;
      }
      
      // Vérifier et détruire l'instance jQuery si elle existe
      if (tableRef.value && document.contains(tableRef.value)) {
        try {
          if ($.fn.dataTable.isDataTable(tableRef.value)) {
            $(tableRef.value).DataTable().destroy();
          }
        } catch (error) {
          console.warn('Error destroying jQuery DataTable instance:', error);
        }
      }
      
      // Nettoyer les classes et attributs DataTables restants
      if (tableRef.value) {
        try {
          $(tableRef.value).removeClass('dataTable');
          $(tableRef.value).removeAttr('id');
          $(tableRef.value).find('thead, tbody').removeAttr('role');
        } catch (error) {
          console.warn('Error cleaning up DataTable classes:', error);
        }
      }
    } catch (error) {
      console.warn('Erreur lors de la destruction du DataTable:', error);
    } finally {
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

  // Pas de onBeforeUnmount dans un composable - la gestion du cycle de vie
  // doit être faite par le composant qui utilise ce composable

  return {
    tableRef,
    initDataTable,
    destroyDataTable,
    refreshDataTable,
    dataTableInstance: ref(dataTableInstance)
  };
} 