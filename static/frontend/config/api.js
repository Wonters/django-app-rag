/**
 * Configuration des URLs de l'API
 * Centralise toutes les URLs injectées depuis Django
 */

// URLs des collections
export const COLLECTION_API_URL = window.COLLECTION_API_URL || '/api/collections/';
export const COLLECTION_FORM_URL = window.COLLECTION_FORM_URL || '/collections/create/';
export const COLLECTION_EDIT_URL = window.COLLECTION_EDIT_URL || '/collections/edit/';

// URLs des sources/documents
export const SOURCE_API_URL = window.SOURCE_API_URL || '/api/sources/';
export const SOURCE_FORM_URL = window.SOURCE_FORM_URL || '/sources/create/';
export const SOURCE_EDIT_URL = window.SOURCE_EDIT_URL || '/sources/edit/';
export const SOURCE_DETAIL_URL = window.SOURCE_DETAIL_URL || '/sources/detail/';

// URLs des questions
export const QUESTION_API_URL = window.QUESTION_API_URL || '/api/questions/';
export const QUESTION_FORM_URL = window.QUESTION_FORM_URL || '/questions/create/';
export const QUESTION_EDIT_URL = window.QUESTION_EDIT_URL || '/questions/edit/';

// Configuration générale
export const API_CONFIG = {
  // URLs des collections
  collections: {
    api: COLLECTION_API_URL,
    form: COLLECTION_FORM_URL,
    edit: COLLECTION_EDIT_URL
  },
  
  // URLs des sources
  sources: {
    api: SOURCE_API_URL,
    form: SOURCE_FORM_URL,
    edit: SOURCE_EDIT_URL,
    detail: SOURCE_DETAIL_URL
  },
  
  // URLs des questions
  questions: {
    api: QUESTION_API_URL,
    form: QUESTION_FORM_URL,
    edit: QUESTION_EDIT_URL
  }
};

// Fonctions utilitaires pour construire les URLs
export const buildUrl = {
  /**
   * Construire l'URL d'édition d'une collection
   */
  collectionEdit: (id) => {
    return COLLECTION_EDIT_URL.replace('__pk__', id);
  },
  
  /**
   * Construire l'URL d'édition d'une source
   */
  sourceEdit: (id) => {
    return SOURCE_EDIT_URL.replace('__pk__', id);
  },
  
  /**
   * Construire l'URL d'édition d'une question
   */
  questionEdit: (id) => {
    return QUESTION_EDIT_URL.replace('__pk__', id);
  },
  
  /**
   * Construire l'URL de suppression d'une ressource
   */
  delete: (baseUrl, id) => {
    return `${baseUrl}${id}/`;
  },
  
  /**
   * Construire l'URL avec paramètres
   */
  withParams: (baseUrl, params = {}) => {
    const url = new URL(baseUrl, window.location.origin);
    Object.entries(params).forEach(([key, value]) => {
      if (value !== null && value !== undefined) {
        url.searchParams.append(key, value);
      }
    });
    return url.toString();
  }
};

// Validation des URLs requises
export function validateApiUrls() {
  const requiredUrls = [
    'COLLECTION_API_URL',
    'SOURCE_API_URL',
    'QUESTION_API_URL'
  ];
  
  const missingUrls = requiredUrls.filter(url => !window[url]);
  
  if (missingUrls.length > 0) {
    console.warn('URLs API manquantes:', missingUrls);
    console.warn('Utilisation des URLs par défaut');
  }
  
  return missingUrls.length === 0;
}

// Initialisation
validateApiUrls(); 