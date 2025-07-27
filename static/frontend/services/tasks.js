
// Fonction pour obtenir le cookie CSRF
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Fonction pour vérifier le statut d'une tâche d'upload
function pollUploadStatus(taskId, downloadLink, originalText) {
    const maxAttempts = 60; // 5 minutes max (60 * 5 secondes)
    let attempts = 0;
    
    // Extraire l'ID du dataset depuis l'URL originale
    const datasetIdMatch = downloadLink.href.match(/\/datasets\/(\d+)\/download/);
    const datasetId = datasetIdMatch ? datasetIdMatch[1] : '1';
    
    const checkStatus = () => {
        attempts++;
        
        // Utiliser l'URL de téléchargement avec le paramètre task_id
        const statusUrl = `/ml_app/api/datasets/${datasetId}/download/?task_id=${taskId}`;
        
        fetch(statusUrl, {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCookie("csrftoken"),
                'Accept': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            console.log('Upload status:', data);
            
            if (data.status === 'pending') {
                downloadLink.innerHTML = '<i class="fas fa-clock"></i> En attente...';
                if (attempts < maxAttempts) {
                    setTimeout(checkStatus, 5000); // Vérifier toutes les 5 secondes
                } else {
                    alert('Timeout: La tâche d\'upload prend trop de temps');
                    downloadLink.innerHTML = originalText;
                    downloadLink.style.pointerEvents = 'auto';
                }
            } else if (data.status === 'running') {
                downloadLink.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Upload en cours...';
                if (attempts < maxAttempts) {
                    setTimeout(checkStatus, 5000); // Vérifier toutes les 5 secondes
                } else {
                    alert('Timeout: La tâche d\'upload prend trop de temps');
                    downloadLink.innerHTML = originalText;
                    downloadLink.style.pointerEvents = 'auto';
                }
            } else if (data.status === 'completed') {
                downloadLink.innerHTML = '<i class="fas fa-check"></i> Terminé';
                setTimeout(() => {
                    alert('Dataset uploadé avec succès vers S3 !');
                    window.location.reload(); // Recharger la page pour mettre à jour l'état
                }, 1000);
            } else if (data.status === 'failed') {
                downloadLink.innerHTML = originalText;
                downloadLink.style.pointerEvents = 'auto';
                alert('Erreur lors de l\'upload: ' + (data.error || 'Erreur inconnue'));
            } else {
                downloadLink.innerHTML = originalText;
                downloadLink.style.pointerEvents = 'auto';
                alert('Statut inconnu: ' + data.status);
            }
        })
        .catch(error => {
            console.error('Erreur lors de la vérification du statut:', error);
            downloadLink.innerHTML = originalText;
            downloadLink.style.pointerEvents = 'auto';
            alert('Erreur lors de la vérification du statut de l\'upload');
        });
    };
    
    // Démarrer la vérification
    checkStatus();
}

// Fonction générique pour vérifier le statut d'une tâche
function pollTaskStatus(taskId, endpoint, element, originalText, taskName = "Tâche") {
    const maxAttempts = 60; // 5 minutes max (60 * 5 secondes)
    let attempts = 0;
    
    const checkStatus = () => {
        attempts++;
        
        fetch(`${endpoint}?task_id=${taskId}`, {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCookie("csrftoken"),
                'Accept': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            console.log(`${taskName} status:`, data);
            
            if (data.status === 'pending') {
                if (element) {
                    element.innerHTML = '<i class="fas fa-clock"></i> En attente...';
                }
                if (attempts < maxAttempts) {
                    setTimeout(checkStatus, 5000);
                } else {
                    alert(`Timeout: La ${taskName.toLowerCase()} prend trop de temps`);
                    if (element && originalText) {
                        element.innerHTML = originalText;
                        element.style.pointerEvents = 'auto';
                    }
                }
            } else if (data.status === 'running') {
                if (element) {
                    element.innerHTML = '<i class="fas fa-spinner fa-spin"></i> En cours...';
                }
                if (attempts < maxAttempts) {
                    setTimeout(checkStatus, 5000);
                } else {
                    alert(`Timeout: La ${taskName.toLowerCase()} prend trop de temps`);
                    if (element && originalText) {
                        element.innerHTML = originalText;
                        element.style.pointerEvents = 'auto';
                    }
                }
            } else if (data.status === 'completed') {
                if (element) {
                    element.innerHTML = '<i class="fas fa-check"></i> Terminé';
                }
                setTimeout(() => {
                    alert(`${taskName} terminée avec succès !`);
                    window.location.reload();
                }, 1000);
            } else if (data.status === 'failed') {
                if (element && originalText) {
                    element.innerHTML = originalText;
                    element.style.pointerEvents = 'auto';
                }
                alert(`Erreur lors de la ${taskName.toLowerCase()}: ` + (data.error || 'Erreur inconnue'));
            } else {
                if (element && originalText) {
                    element.innerHTML = originalText;
                    element.style.pointerEvents = 'auto';
                }
                alert('Statut inconnu: ' + data.status);
            }
        })
        .catch(error => {
            console.error(`Erreur lors de la vérification du statut de la ${taskName.toLowerCase()}:`, error);
            if (element && originalText) {
                element.innerHTML = originalText;
                element.style.pointerEvents = 'auto';
            }
            alert(`Erreur lors de la vérification du statut de la ${taskName.toLowerCase()}`);
        });
    };
    
    // Démarrer la vérification
    checkStatus();
}

// Fonction pour lancer une tâche et gérer le polling
function launchTaskAndPoll(taskEndpoint, taskData, element, originalText, taskName = "Tâche") {
    // Changer l'état de l'élément pour indiquer le lancement
    if (element) {
        element.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Lancement...';
        element.style.pointerEvents = 'none';
    }
    
    fetch(taskEndpoint, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie("csrftoken"),
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        body: JSON.stringify(taskData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'pending' && data.task_id) {
            // Tâche lancée, commencer le polling
            alert(`${taskName} lancée ! Vérification du statut...`);
            pollTaskStatus(data.task_id, taskEndpoint, element, originalText, taskName);
        } else if (data.error) {
            // Erreur lors du lancement
            alert(`Erreur lors du lancement de la ${taskName.toLowerCase()}: ` + data.error);
            if (element && originalText) {
                element.innerHTML = originalText;
                element.style.pointerEvents = 'auto';
            }
        } else {
            // Autre cas
            alert(`Réponse inattendue: ${JSON.stringify(data)}`);
            if (element && originalText) {
                element.innerHTML = originalText;
                element.style.pointerEvents = 'auto';
            }
        }
    })
    .catch(error => {
        console.error(`Erreur lors du lancement de la ${taskName.toLowerCase()}:`, error);
        alert(`Erreur lors du lancement de la ${taskName.toLowerCase()}`);
        if (element && originalText) {
            element.innerHTML = originalText;
            element.style.pointerEvents = 'auto';
        }
    });
}

// Fonction spécifique pour lancer une tâche d'initialisation de collection
function launchCollectionInitialization(collectionId, collection, originalText) {
    const taskEndpoint = '/rag_app/api/etl/';
    const taskData = {
        collection_id: collectionId
    };
    
    // Marquer la collection comme en cours d'initialisation
    if (collection) {
        collection.initializationStatus = 'pending';
    }
    
    // Changer l'état de l'élément pour indiquer le lancement
    if (originalText) {
        originalText.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Lancement...';
        originalText.style.pointerEvents = 'none';
    }
    
    fetch(taskEndpoint, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie("csrftoken"),
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        body: JSON.stringify(taskData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'pending' && data.task_id) {
            // Tâche lancée, commencer le polling
            console.log('Tâche d\'initialisation lancée ! Vérification du statut...');
            pollInitializationStatus(data.task_id, collection, originalText);
        } else if (data.error) {
            // Erreur lors du lancement
            console.error('Erreur lors du lancement de la tâche d\'initialisation:', data.error);
            if (collection) {
                collection.initializationStatus = 'failed';
            }
            if (originalText) {
                originalText.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Erreur';
                originalText.style.pointerEvents = 'auto';
            }
            alert('Erreur lors du lancement de la tâche d\'initialisation: ' + data.error);
        } else {
            // Autre cas
            console.error('Réponse inattendue:', data);
            if (collection) {
                collection.initializationStatus = 'failed';
            }
            if (originalText) {
                originalText.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Erreur';
                originalText.style.pointerEvents = 'auto';
            }
            alert('Réponse inattendue lors du lancement de la tâche');
        }
    })
    .catch(error => {
        console.error('Erreur lors du lancement de la tâche d\'initialisation:', error);
        if (collection) {
            collection.initializationStatus = 'failed';
        }
        if (originalText) {
            originalText.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Erreur';
            originalText.style.pointerEvents = 'auto';
        }
        alert('Erreur lors du lancement de la tâche d\'initialisation');
    });
}

// Fonction pour vérifier le statut d'une tâche d'initialisation
function pollInitializationStatus(taskId, collection, originalText) {
    const taskEndpoint = '/rag_app/api/etl/';
    const maxAttempts = 60; // 5 minutes max (60 * 5 secondes)
    let attempts = 0;
    
    const checkStatus = () => {
        attempts++;
        
        fetch(`${taskEndpoint}?task_id=${taskId}`, {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCookie("csrftoken"),
                'Accept': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            console.log('Statut de la tâche d\'initialisation:', data);
            
            if (data.status === 'pending') {
                if (collection) {
                    collection.initializationStatus = 'pending';
                }
                if (attempts < maxAttempts) {
                    setTimeout(checkStatus, 5000);
                } else {
                    console.error('Timeout: La tâche d\'initialisation prend trop de temps');
                    if (collection) {
                        collection.initializationStatus = 'timeout';
                    }
                    if (originalText) {
                        originalText.innerHTML = '<i class="fas fa-clock"></i> Timeout';
                        originalText.style.pointerEvents = 'auto';
                    }
                    alert('Timeout: La tâche d\'initialisation prend trop de temps');
                }
            } else if (data.status === 'running') {
                if (collection) {
                    collection.initializationStatus = 'running';
                }
                if (attempts < maxAttempts) {
                    setTimeout(checkStatus, 5000);
                } else {
                    console.error('Timeout: La tâche d\'initialisation prend trop de temps');
                    if (collection) {
                        collection.initializationStatus = 'timeout';
                    }
                    if (originalText) {
                        originalText.innerHTML = '<i class="fas fa-clock"></i> Timeout';
                        originalText.style.pointerEvents = 'auto';
                    }
                    alert('Timeout: La tâche d\'initialisation prend trop de temps');
                }
            } else if (data.status === 'completed') {
                if (collection) {
                    collection.initializationStatus = 'completed';
                }
                if (originalText) {
                    originalText.innerHTML = '<i class="fas fa-check"></i> Terminé';
                    originalText.style.pointerEvents = 'auto';
                }
                setTimeout(() => {
                    alert('Initialisation de la collection terminée avec succès !');
                    window.location.reload();
                }, 1000);
            } else if (data.status === 'failed') {
                if (collection) {
                    collection.initializationStatus = 'failed';
                }
                if (originalText) {
                    originalText.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Erreur';
                    originalText.style.pointerEvents = 'auto';
                }
                alert('Erreur lors de l\'initialisation: ' + (data.error || 'Erreur inconnue'));
            } else {
                if (collection) {
                    collection.initializationStatus = 'unknown';
                }
                if (originalText) {
                    originalText.innerHTML = '<i class="fas fa-question"></i> Inconnu';
                    originalText.style.pointerEvents = 'auto';
                }
                alert('Statut inconnu: ' + data.status);
            }
        })
        .catch(error => {
            console.error('Erreur lors de la vérification du statut de l\'initialisation:', error);
            if (collection) {
                collection.initializationStatus = 'error';
            }
            if (originalText) {
                originalText.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Erreur';
                originalText.style.pointerEvents = 'auto';
            }
            alert('Erreur lors de la vérification du statut de l\'initialisation');
        });
    };
    
    // Démarrer la vérification
    checkStatus();
}

export {
    getCookie,
    pollUploadStatus,
    pollTaskStatus,
    launchTaskAndPoll,
    launchCollectionInitialization,
    pollInitializationStatus
}; 
/**
 * Handle standardized API responses
 * @param {Object} data - Response data with standardized format
 * @param {string} data.status - Response status
 * @param {string} data.message - Response message
 * @param {string} data.task_id - Task identifier
 * @param {string} data.error - Error message (if applicable)
 * @param {Object} data.result - Result data (if applicable)
 * @returns {Object} - Processed response object
 */
export function handleStandardizedResponse(data) {
    const response = {
        status: data.status,
        message: data.message,
        task_id: data.task_id,
        error: data.error,
        result: data.result,
        isValid: true
    };
    
    // Validation de base
    if (!data.status) {
        response.isValid = false;
        response.error = 'Format de réponse invalide: statut manquant';
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
                response.error = 'ID de tâche manquant pour le statut: ' + data.status;
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
            response.isValid = false;
            response.error = 'Statut inconnu: ' + data.status;
    }
    
    return response;
}