# CI/CD Quick Start - 5 Minutes

## 🚀 Configuration Rapide

### 1. Configurer les Secrets GitHub (2 min)

Aller dans **Settings → Secrets and variables → Actions** et ajouter :

```
DEVELOP_IP=192.168.1.100          # IP de votre serveur
SSH_USER=ubuntu                    # Votre utilisateur SSH
SSH_PRIVATE_KEY=<contenu clé SSH>  # Votre clé privée SSH
DJANGO_SECRET_KEY=<générer>        # Django secret key
OPENAI_API_KEY=sk-...              # Votre clé OpenAI
DATABASE_URL=postgresql://...      # URL de votre base de données
```

### 2. Préparer le Serveur (2 min)

Sur votre serveur de développement :

```bash
# Installer Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Autoriser SSH avec votre clé
cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys

# Ouvrir les ports
sudo ufw allow 8080/tcp
sudo ufw allow 22/tcp
```

### 3. Push et C'est Parti ! (1 min)

```bash
git push origin develop
```

Ça y est ! 🎉

- ✅ Tests automatiques lancés
- ✅ Build Docker créé
- ✅ Déploiement sur `http://DEVELOP_IP:8080`

## 📊 Voir le Déploiement

- **GitHub Actions** : Onglet "Actions" de votre repo
- **Logs serveur** : `ssh user@DEVELOP_IP 'cd /opt/django-app-rag-dev && sudo docker-compose logs'`
- **Application** : `http://DEVELOP_IP:8080`
- **Health check** : `http://DEVELOP_IP:8080/health`

## 🛠️ Commandes Utiles

```bash
# Voir les logs
ssh user@DEVELOP_IP 'cd /opt/django-app-rag-dev && sudo docker-compose logs -f'

# Redémarrer
ssh user@DEVELOP_IP 'cd /opt/django-app-rag-dev && sudo docker-compose restart'

# Voir l'état
ssh user@DEVELOP_IP 'cd /opt/django-app-rag-dev && sudo docker-compose ps'
```

## 📚 Documentation Complète

Voir `CI_CD_SETUP.md` pour la documentation complète.

---

**C'est tout !** Le reste est automatique. 🚀
