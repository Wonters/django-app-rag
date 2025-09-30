import apiService from './apiService.js';
import { logger } from '../composables/useErrorHandler.js';

/**
 * Configuration par défaut pour le polling
 */
const DEFAULT_POLLING_CONFIG = {
    maxAttempts: 60, // 5 minutes max (60 * 5 secondes)
    interval: 5000,  // Vérifier toutes les 5 secondes
    timeoutMessage: 'La tâche prend trop de temps'
};

/**
 * Fonction générique pour lancer une tâche
 * @param {string} endpoint - Endpoint de l'API pour lancer la tâche
 * @param {Object} taskData - Données de la tâche
 * @param {Object} options - Options de configuration
 * @returns {Promise<Object>} - Promise résolue avec la réponse de lancement
 */
export async function launchTask(endpoint, taskData, options = {}) {
    try {
        const response = await apiService.post(endpoint, taskData);
        const data = await apiService.processApiResponse(response);

        if (data.status === 'pending' && data.task_id) {
            return {
                success: true,
                taskId: data.task_id,
                status: data.status,
                message: data.message || 'Tâche lancée avec succès'
            };
        } else if (data.error) {
            throw new Error(data.error);
        } else {
            throw new Error('Réponse inattendue lors du lancement de la tâche');
        }
    } catch (error) {
        throw new Error(`Erreur lors du lancement de la tâche: ${error.message}`);
    }
}

/**
 * Fonction générique pour le polling du statut d'une tâche
 * @param {string} taskId - ID de la tâche
 * @param {string} endpoint - Endpoint pour vérifier le statut
 * @param {Object} options - Options de configuration
 * @param {Function} options.onStatusUpdate - Callback appelé à chaque mise à jour du statut
 * @param {Function} options.onSuccess - Callback appelé en cas de succès
 * @param {Function} options.onError - Callback appelé en cas d'erreur
 * @param {Function} options.onComplete - Callback appelé à la fin (succès ou échec)
 * @param {number} options.maxAttempts - Nombre maximum de tentatives
 * @param {number} options.interval - Intervalle entre les vérifications en ms
 * @param {string} options.timeoutMessage - Message de timeout personnalisé
 * @returns {Promise<Object>} - Promise résolue avec le résultat final
 */
export async function pollTaskStatus(taskId, endpoint, options = {}) {
    const config = { ...DEFAULT_POLLING_CONFIG, ...options };
    const {
        onStatusUpdate = () => { },
        onSuccess = () => { },
        onError = () => { },
        onComplete = () => { },
        maxAttempts,
        interval,
        timeoutMessage
    } = config;

    let attempts = 0;

    return new Promise((resolve, reject) => {
        const checkStatus = async () => {
            try {
                attempts++;

                const response = await apiService.get(`${endpoint}?task_id=${taskId}`);
                console.log('response', response);
                const data = await apiService.processApiResponse(response);
                console.log('data', data);

                // Appeler le callback de mise à jour du statut
                onStatusUpdate(data.status, data);

                if (data.status === 'completed') {
                    // Tâche terminée avec succès
                    logger.log('Tâche terminée avec succès:', data);
                    onSuccess(data);
                    onComplete('completed', data);
                    resolve({ status: 'completed', data });

                } else if (data.status === 'failed') {
                    // Tâche échouée
                    const error = new Error(data.error.message || 'Erreur lors de l\'exécution de la tâche');
                    logger.error('Tâche échouée:', error);
                    onError(error, data);
                    onComplete('failed', data);
                    reject(error);

                } else if (data.status === 'running' || data.status === 'pending') {
                    // Tâche en cours, continuer le polling
                    if (attempts < maxAttempts) {
                        setTimeout(checkStatus, interval);
                    } else {
                        // Timeout
                        const timeoutError = new Error(timeoutMessage);
                        logger.warn('Timeout de la tâche:', timeoutError.message);
                        onError(timeoutError, data);
                        onComplete('timeout', data);
                        reject(timeoutError);
                    }

                } else {
                    // Statut inconnu
                    const unknownError = new Error(`Statut inconnu: ${data.status}`);
                    logger.error('Statut inconnu de la tâche:', unknownError.message);
                    onError(unknownError, data);
                    onComplete('unknown', data);
                    reject(unknownError);
                }

            } catch (error) {
                onError(error);
                onComplete('error', null);
                reject(error);
            }
        };

        // Démarrer le polling
        checkStatus();
    });
}

/**
 * Fonction pour lancer et surveiller une tâche complète
 * @param {string} endpoint - Endpoint de l'API
 * @param {Object} taskData - Données de la tâche
 * @param {Object} options - Options de configuration
 * @returns {Promise<Object>} - Promise résolue avec le résultat final
 */
export async function launchTaskAndPoll(endpoint, taskData, options = {}) {
    try {
        // Lancer la tâche
        const launchResult = await launchTask(endpoint, taskData, options);

        // Commencer le polling
        const result = await pollTaskStatus(launchResult.taskId, endpoint, options);

        return {
            ...launchResult,
            finalResult: result
        };
    } catch (error) {
        throw error;
    }
}

/**
 * Fonction spécifique pour lancer l'initialisation d'une collection
 * @param {number} collectionId - ID de la collection
 * @param {Object} options - Options de configuration
 * @param {Function} options.onStatusUpdate - Callback pour les mises à jour de statut
 * @param {Function} options.onSuccess - Callback en cas de succès
 * @param {Function} options.onError - Callback en cas d'erreur
 * @param {Function} options.onComplete - Callback à la fin
 * @returns {Promise<Object>} - Promise résolue avec le résultat
 */
export async function launchCollectionInitialization(collectionId, options = {}) {
    const endpoint = '/rag_app/api/etl/';
    const taskData = { collection_id: collectionId };

    const defaultCallbacks = {
        onStatusUpdate: (status, data) => {
            logger.log(`Initialisation de la collection ${collectionId}: ${status}`);
        },
        onSuccess: (data) => {
            logger.log('Initialisation de la collection terminée avec succès');
            // Pas de reload automatique, laisser le composant décider
        },
        onError: (error, data) => {
            logger.error('Erreur lors de l\'initialisation:', error);
            // Pas d'alert automatique, laisser le composant décider
        },
        onComplete: (finalStatus, data) => {
            logger.log('Initialisation terminée avec le statut:', finalStatus);
        }
    };

    const callbacks = { ...defaultCallbacks, ...options };

    return launchTaskAndPoll(endpoint, taskData, {
        ...options,
        ...callbacks,
        timeoutMessage: 'L\'initialisation de la collection prend trop de temps'
    });
}

/**
 * Fonction spécifique pour lancer l'analyse QA d'une source
 * @param {Object} source - L'objet source à analyser
 * @param {string} qaApiUrl - URL de l'API QA
 * @param {Object} options - Options de configuration
 * @param {Function} options.onStatusUpdate - Callback pour les mises à jour de statut
 * @param {Function} options.onSuccess - Callback en cas de succès
 * @param {Function} options.onError - Callback en cas d'erreur
 * @param {Function} options.onComplete - Callback à la fin
 * @returns {Promise<Object>} - Promise résolue avec le résultat
 */
export async function launchQAAnalysis(source, qaApiUrl, options = {}) {
    const taskData = { source_id: source.id };

    const defaultCallbacks = {
        onStatusUpdate: (status, data) => {
            // Mettre à jour le statut de la source
            if (source) {
                source.qa_status = status;
            }
            logger.log(`Analyse QA de la source ${source.id}: ${status}`);
        },
        onSuccess: (data) => {
            logger.log('Analyse QA terminée avec succès');
            if (source) {
                source.qa_status = 'completed';
            }
            // Pas de reload automatique, laisser le composant décider
        },
        onError: (error, data) => {
            logger.error('Erreur lors de l\'analyse QA:', error);
            if (source) {
                source.qa_status = 'failed';
            }
            // Pas d'alert automatique, laisser le composant décider
        },
        onComplete: (finalStatus, data) => {
            logger.log('Analyse QA terminée pour la source', source.id, 'avec le statut:', finalStatus);
        }
    };

    const callbacks = { ...defaultCallbacks, ...options };

    return launchTaskAndPoll(qaApiUrl, taskData, {
        ...options,
        ...callbacks,
        timeoutMessage: 'L\'analyse QA prend trop de temps'
    });
}


/**
 * Fonction spécifique pour lancer l'indexation d'une source
 * @param {Object} source - L'objet source à indexer
 * @param {string} endpoint - URL de l'API ETL
 * @param {Object} options - Options de configuration
 * @param {Function} options.onStatusUpdate - Callback pour les mises à jour de statut
 * @param {Function} options.onSuccess - Callback en cas de succès
 * @param {Function} options.onError - Callback en cas d'erreur
 * @param {Function} options.onComplete - Callback à la fin
 * @returns {Promise<Object>} - Promise résolue avec le résultat
 */
export async function launchIndexing(source, endpoint, options = {}) {
    const taskData = { source_id: source.id };
    return launchTaskAndPoll(endpoint, taskData, {
        ...options,
        timeoutMessage: 'L\'indexation prend trop de temps'
    });
}



/**
 * Gestionnaire de réponses API standardisées pour les tâches
 * @param {Object} data - Données de réponse avec format standardisé
 * @returns {Object} - Objet de réponse traité
 * 
 * @example
 * // Exemple d'utilisation avec une réponse API
 * const apiResponse = {
 *   status: 'completed',
 *   task_id: '12345',
 *   result: { data: 'success' },
 *   message: 'Tâche terminée'
 * };
 * 
 * const standardized = handleStandardizedTaskResponse(apiResponse);
 * if (standardized.isValid) {
 *   console.log('Statut:', standardized.status);
 *   console.log('Résultat:', standardized.result);
 * } else {
 *   console.error('Erreur:', standardized.error);
 * }
 */
export function handleStandardizedTaskResponse(data) {
    // Vérification que data est un objet valide
    if (!data || typeof data !== 'object') {
        return {
            status: 'unknown',
            message: 'Réponse invalide: données non-object',
            task_id: null,
            error: 'Format de réponse invalide',
            result: null,
            isValid: false,
            rawData: data
        };
    }

    const response = {
        status: data.status || 'unknown',
        message: data.message || null,
        task_id: data.task_id || null,
        error: data.error || null,
        result: data.result || null,
        isValid: true,
        rawData: data
    };

    // Validation de base
    if (!data.status) {
        response.isValid = false;
        response.error = 'Format de réponse invalide: statut manquant';
        return response;
    }

    // Validation selon le statut
    switch (data.status) {
        case 'pending':
        case 'running':
            if (!data.task_id) {
                response.isValid = false;
                response.error = 'ID de tâche manquant pour le statut: ' + data.status;
            }
            break;
        case 'completed':
            if (!data.task_id && !data.result) {
                response.isValid = false;
                response.error = 'ID de tâche ou résultat manquant pour le statut: ' + data.status;
            }
            break;
        case 'failed':
            if (!data.error && !data.message) {
                response.isValid = false;
                response.error = 'Message d\'erreur manquant pour le statut: failed';
            }
            break;
        case 'unknown':
            if (!data.message) {
                response.isValid = false;
                response.error = 'Message manquant pour le statut: unknown';
            }
            break;
        default:
            // Pour les statuts personnalisés, on accepte mais on marque comme potentiellement non-standard
            response.isValid = true;
            response.warning = 'Statut non-standard détecté: ' + data.status;
    }

    return response;
}



