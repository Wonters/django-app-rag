// Service pour gérer les appels API avec CSRF token
class ApiService {
  constructor() {
    this.csrfToken = null;
    this.baseHeaders = {
      'Content-Type': 'application/json',
    };
  }

  // Récupérer le CSRF token depuis les cookies
  getCsrfToken() {
    if (this.csrfToken) {
      return this.csrfToken;
    }
    
    const value = `; ${document.cookie}`;
    const parts = value.split('; csrftoken=');
    if (parts.length === 2) {
      this.csrfToken = parts.pop().split(';').shift();
      return this.csrfToken;
    }
    return null;
  }

  // Récupérer le CSRF token depuis une requête GET
  async fetchCsrfToken(url) {
    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: this.baseHeaders
      });
      
      if (response.ok) {
        // Essayer de récupérer le token depuis les headers ou cookies
        const token = response.headers.get('X-CSRFToken') || this.getCsrfToken();
        if (token) {
          this.csrfToken = token;
          return token;
        }
      }
    } catch (error) {
      console.error('Erreur lors de la récupération du CSRF token:', error);
    }
    return null;
  }

  // Préparer les headers avec CSRF token
  getHeaders() {
    const token = this.getCsrfToken();
    return {
      ...this.baseHeaders,
      ...(token && { 'X-CSRFToken': token })
    };
  }

  // Méthode GET
  async get(url, options = {}) {
    const headers = { ...this.getHeaders(), ...options.headers };
    return fetch(url, {
      method: 'GET',
      headers,
      ...options
    });
  }

  // Méthode POST
  async post(url, data = null, options = {}) {
    const headers = { ...this.getHeaders(), ...options.headers };
    const fetchOptions = {
      method: 'POST',
      headers,
      ...options
    };
    
    if (data) {
      fetchOptions.body = JSON.stringify(data);
    }
    
    return fetch(url, fetchOptions);
  }

  // Méthode PUT
  async put(url, data = null, options = {}) {
    const headers = { ...this.getHeaders(), ...options.headers };
    const fetchOptions = {
      method: 'PUT',
      headers,
      ...options
    };
    
    if (data) {
      fetchOptions.body = JSON.stringify(data);
    }
    
    return fetch(url, fetchOptions);
  }

  // Méthode PATCH
  async patch(url, data = null, options = {}) {
    const headers = { ...this.getHeaders(), ...options.headers };
    const fetchOptions = {
      method: 'PATCH',
      headers,
      ...options
    };
    
    if (data) {
      fetchOptions.body = JSON.stringify(data);
    }
    
    return fetch(url, fetchOptions);
  }

  // Méthode DELETE avec gestion automatique du CSRF
  async delete(url, options = {}) {
    // D'abord, essayer de récupérer le CSRF token si nécessaire
    if (!this.getCsrfToken()) {
      await this.fetchCsrfToken(url);
    }
    
    const headers = { ...this.getHeaders(), ...options.headers };
    return fetch(url, {
      method: 'DELETE',
      headers,
      ...options
    });
  }

  // Méthode DELETE avec pré-récupération du CSRF token
  async deleteWithCsrfFetch(url, options = {}) {
    // Toujours faire une requête GET d'abord pour récupérer le CSRF token
    await this.fetchCsrfToken(url);
    
    const headers = { ...this.getHeaders(), ...options.headers };
    return fetch(url, {
      method: 'DELETE',
      headers,
      ...options
    });
  }
}

// Instance singleton
const apiService = new ApiService();

export default apiService; 