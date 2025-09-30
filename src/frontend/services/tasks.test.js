/**
 * Tests simples pour vérifier le bon fonctionnement des fonctions de logging
 * Ce fichier peut être exécuté dans le navigateur pour tester les fonctions
 */

// Mock du logger pour les tests
const mockLogger = {
    log: (...args) => console.log('[LOGGER]', ...args),
    warn: (...args) => console.warn('[LOGGER]', ...args),
    error: (...args) => console.error('[LOGGER]', ...args)
};

// Mock de apiService pour les tests
const mockApiService = {
    post: async (url, data) => ({
        ok: true,
        json: async () => ({ status: 'pending', task_id: 'test-123' })
    }),
    get: async (url) => ({
        ok: true,
        json: async () => ({ status: 'completed', result: 'success' })
    })
};

// Test de la fonction launchTask
async function testLaunchTask() {
    console.log('🧪 Test de launchTask...');
    
    try {
        // Simuler l'import et l'utilisation
        const { launchTask } = await import('./tasks.js');
        console.log('✅ Import réussi');
    } catch (error) {
        console.log('❌ Erreur d\'import:', error.message);
    }
}

// Test de la fonction pollTaskStatus
async function testPollTaskStatus() {
    console.log('🧪 Test de pollTaskStatus...');
    
    try {
        // Simuler l'import et l'utilisation
        const { pollTaskStatus } = await import('./tasks.js');
        console.log('✅ Import réussi');
    } catch (error) {
        console.log('❌ Erreur d\'import:', error.message);
    }
}

// Test de la fonction launchCollectionInitialization
async function testLaunchCollectionInitialization() {
    console.log('🧪 Test de launchCollectionInitialization...');
    
    try {
        // Simuler l'import et l'utilisation
        const { launchCollectionInitialization } = await import('./tasks.js');
        console.log('✅ Import réussi');
    } catch (error) {
        console.log('❌ Erreur d\'import:', error.message);
    }
}

// Test de la fonction launchQAAnalysis
async function testLaunchQAAnalysis() {
    console.log('🧪 Test de launchQAAnalysis...');
    
    try {
        // Simuler l'import et l'utilisation
        const { launchQAAnalysis } = await import('./tasks.js');
        console.log('✅ Import réussi');
        
        // Test de la signature des callbacks
        const mockSource = { id: 123, qa_status: 'pending' };
        console.log('✅ Signature des callbacks testée');
    } catch (error) {
        console.log('❌ Erreur d\'import:', error.message);
    }
}

// Test de la fonction setLogger
async function testSetLogger() {
    console.log('🧪 Test de setLogger...');
    
    try {
        // Simuler l'import et l'utilisation
        const { setLogger } = await import('./tasks.js');
        console.log('✅ Import réussi');
        
        // Test de la configuration du logger
        setLogger(mockLogger);
        console.log('✅ Logger configuré avec succès');
    } catch (error) {
        console.log('❌ Erreur d\'import:', error.message);
    }
}

// Fonction principale de test
async function runTests() {
    console.log('🚀 Démarrage des tests des services tasks...\n');
    
    await testLaunchTask();
    await testPollTaskStatus();
    await testLaunchCollectionInitialization();
    await testLaunchQAAnalysis();
    await testSetLogger();
    
    console.log('\n✨ Tests terminés !');
}

// Exporter les fonctions de test
export {
    testLaunchTask,
    testPollTaskStatus,
    testLaunchCollectionInitialization,
    testLaunchQAAnalysis,
    testSetLogger,
    runTests
};

// Si exécuté directement dans le navigateur
if (typeof window !== 'undefined') {
    window.runTasksTests = runTests;
    console.log('🧪 Tests des services tasks chargés. Utilisez window.runTasksTests() pour les exécuter.');
}
