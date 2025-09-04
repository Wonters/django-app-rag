# Django RAG APPLICATION

[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com/Wonters/django-app-rag)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![Django](https://img.shields.io/badge/django-5.0%2B-green.svg)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-beta-orange.svg)](https://github.com/Wonters/django-app-rag)

A comprehensive Django application for Retrieval-Augmented Generation (RAG) with modern web interface and REST API.

## 📑 Table of Contents

- [📦 Project Information](#-project-information)
- [🚀 Features](#-features)
  - [📚 Collection and Source Management](#-collection-and-source-management)
  - [🤖 Complete RAG Pipeline](#-complete-rag-pipeline)
  - [🎨 Modern Web Interface](#-modern-web-interface)
  - [🔧 Integrations](#-integrations)
- [📋 Prerequisites](#-prerequisites)
- [🛠️ Installation](#️-installation)
  - [1. Install Python Dependencies](#1-install-python-dependencies)
  - [2. Environment Configuration](#2-environment-configuration)
  - [3. Django Configuration](#3-django-configuration)
  - [4. Frontend Installation](#4-frontend-installation)
  - [5. Start Services](#5-start-services)
- [🏗️ Architecture](#️-architecture)
  - [Project Structure](#project-structure)
  - [Data Models](#data-models)
- [🚀 Usage](#-usage)
  - [1. Create a Collection](#1-create-a-collection)
  - [2. Add Sources](#2-add-sources)
  - [3. Index Data](#3-index-data)
  - [4. Ask Questions](#4-ask-questions)
- [🔌 REST API](#-rest-api)
  - [Collections](#collections)
  - [Sources](#sources)
  - [Questions](#questions)
  - [Tasks](#tasks)
- [⚙️ Configuration](#️-configuration)
  - [RAG Configuration](#rag-configuration)
  - [Configuration Example](#configuration-example)
- [🧪 Testing](#-testing)
- [📊 Monitoring](#-monitoring)
  - [Logs](#logs)
  - [MLflow](#mlflow)
- [🚀 Deployment](#-deployment)
  - [Docker](#docker)
  - [Production](#production)
- [🤝 Contributing](#-contributing)
- [📝 License](#-license)
- [🆘 Support](#-support)
- [🙏 Acknowledgments](#-acknowledgments)

## 📦 Project Information

- **Version** : 0.1.0
- **Author** : Wonters
- **Email** : shift.python.software@gmail.com
- **License** : MIT
- **Status** : Beta
- **Repository** : [GitHub](https://github.com/Wonters/django-app-rag)
- **Documentation** : [Wiki](https://github.com/Wonters/django-app-rag/wiki)
- **Issues** : [GitHub Issues](https://github.com/Wonters/django-app-rag/issues)

## 🚀 Features

### 📚 Collection and Source Management
- **Collections** : Organize your data sources by thematic collections
- **Multiple Sources** : Support for Notion, URLs, and local files
- **Automatic Indexing** : ETL pipeline to process and index your data
- **Quality Scores** : Automatic content quality assessment

### 🤖 Complete RAG Pipeline
- **Data Collection** : Notion, files (PDF, TXT, MD), web URLs
- **ETL Processing** : Extract, transform and load data
- **[FAISS](https://github.com/facebookresearch/faiss) Vector Indexing** : Index creation for semantic search
- **Answer Generation** : Q&A system based on your data

### 🎨 Modern Web Interface
- **[Vue.js](https://vuejs.org/) Frontend** : Reactive and modern user interface
- **[Django REST Framework](https://www.django-rest-framework.org/) API** : Complete endpoints for integration
- **[Dramatiq](https://dramatiq.io/) Asynchronous Tasks** : Background processing
- **Monitoring** : Real-time task monitoring

### 🔧 Integrations
- **[Notion](https://developers.notion.com/)** : Automatic retrieval from your Notion databases
- **[OpenAI](https://platform.openai.com/)** : Integration with GPT models for generation
- **[Hugging Face](https://huggingface.co/)** : Support for open-source embedding models
- **[Crawl4AI](https://github.com/unclecode/crawl4ai)** : Advanced web crawling and content extraction
- **[Docling](https://github.com/DS4SD/docling)** : Document processing and parsing capabilities
- **[MLflow](https://mlflow.org/)** : Experiment and metrics tracking

## 📋 Prerequisites

- [Python 3.8+](https://www.python.org/downloads/)
- [Django 5.0+](https://www.djangoproject.com/)
- [Node.js 16+](https://nodejs.org/) (for frontend)
- [PostgreSQL](https://www.postgresql.org/) or [SQLite](https://www.sqlite.org/)

## 🛠️ Installation

### 1. Install Python Dependencies

```bash
# Clone the repository
git clone https://github.com/Wonters/django-app-rag.git
cd django-app-rag

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

```bash
# Copy environment file
cp .env.example .env

# Edit environment variables
nano .env
```

Essential environment variables:
```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/rag_db

# OpenAI (for generation)
OPENAI_API_KEY=your_openai_api_key

# Notion (for data collection)
NOTION_API_KEY=your_notion_api_key

# RAG Configuration
RAG_DATA_DIR=/path/to/rag/data
```

### 3. Django Configuration

```bash
# Database migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic
```

### 4. Frontend Installation

```bash
cd static/frontend
npm install
npm run build
```

### 5. Start Services

```bash
# Terminal 1: Django server
python manage.py runserver

# Terminal 2: Dramatiq worker (for async tasks)
python manage.py rundramatiq

# Terminal 3: Frontend development mode (optional)
cd static/frontend
npm run dev
```

## 🏗️ Architecture

### Project Structure

```
django-app-rag/
├── django_app_rag/           # Main Django application
│   ├── models.py             # Data models
│   ├── views.py              # Views and REST API
│   ├── rag/                  # Core RAG module
│   │   ├── agents/           # AI agents for processing
│   │   ├── config/           # YAML configurations
│   │   ├── pipelines/        # ETL pipelines
│   │   ├── retrievers.py     # Retrieval system
│   │   └── embeddings.py     # Embedding models
│   └── tasks/                # Asynchronous tasks
├── static/frontend/          # Vue.js interface
└── templates/                # Django templates
```

### Data Models

- **Collection** : Group of thematic sources
- **Source** : Data source (Notion, URL, file)
- **Question** : Questions associated with a source
- **Answer** : Answers generated by the RAG system
- **Document** : Documents indexed in the vector store
- **RagConfig** : RAG configurations per collection

## 🚀 Usage

### 1. Create a Collection

```python
from django_app_rag.models import Collection

collection = Collection.objects.create(
    title="Technical Documentation",
    description="Collection for technical documentation"
)
```

### 2. Add Sources

```python
from django_app_rag.models import Source

# Notion Source
notion_source = Source.objects.create(
    type=Source.NOTION,
    title="Notion API Database",
    notion_db_ids="database_id_1,database_id_2",
    collection=collection
)

# URL Source
url_source = Source.objects.create(
    type=Source.URL,
    title="Online Documentation",
    link="https://docs.example.com",
    collection=collection
)

# File Source
file_source = Source.objects.create(
    type=Source.FILE,
    title="PDF Manual",
    file=uploaded_file,
    collection=collection
)
```

### 3. Index Data

```python
from django_app_rag.tasks.etl_tasks import indexing_collection_task

# Launch indexing for entire collection
task = indexing_collection_task.delay(collection_id=collection.id)

# Or index a specific source
from django_app_rag.tasks.etl_tasks import indexing_source_task
task = indexing_source_task.delay(source_id=source.id)
```

### 4. Ask Questions

```python
from django_app_rag.tasks.rag_tasks import launch_qa_process

# Create a question
question = Question.objects.create(
    title="How to use the API?",
    field="How to use the API to retrieve data?",
    source=source
)

# Launch Q&A process
task = launch_qa_process.delay(
    source_id=source.id,
    config_path=collection.get_rag_config()
)
```

## 🔌 REST API

### Collections

```http
GET    /api/collections/              # List collections
POST   /api/collections/              # Create collection
GET    /api/collections/{id}/         # Collection details
PUT    /api/collections/{id}/         # Update collection
DELETE /api/collections/{id}/         # Delete collection
```

### Sources

```http
GET    /api/sources/                  # List sources
POST   /api/sources/                  # Create source
GET    /api/sources/{id}/             # Source details
PUT    /api/sources/{id}/             # Update source
DELETE /api/sources/{id}/             # Delete source
```

### Questions

```http
GET    /api/questions/                # List questions
POST   /api/questions/                # Create question
GET    /api/questions/{id}/           # Question details
PUT    /api/questions/{id}/           # Update question
DELETE /api/questions/{id}/           # Delete question
```

### Tasks

```http
POST   /api/etl/                      # Launch indexing
GET    /api/etl/?task_id={id}         # ETL task status
POST   /api/qa/                       # Launch Q&A process
GET    /api/qa/?task_id={id}          # Q&A task status
```

## ⚙️ Configuration

### RAG Configuration

RAG configurations are stored in `django_app_rag/rag/config/` :

- `rag.yaml` : Main configuration
- `etl.yaml` : ETL configuration
- `index.yaml` : Indexing configuration
- `retrieve.yaml` : Retrieval configuration

### Configuration Example

```yaml
# rag.yaml
collection_name: "my_collection"
data_dir: "/path/to/data"
urls:
  - "https://docs.example.com"
notion_database_ids:
  - "database_id_1"
file_paths:
  - "/path/to/file.pdf"
embedding_model:
  model_id: "sentence-transformers/all-MiniLM-L6-v2"
  model_type: "huggingface"
retriever:
  type: "parent"
  k: 3
  similarity_threshold: 0.5
```

## 🧪 Testing

```bash
# Run all tests
python manage.py test

# Tests with coverage
pytest --cov=django_app_rag

# Specific tests
python manage.py test django_app_rag.tests
```

## 📊 Monitoring

### Logs

Logs are available in the `log/` directory:
- `rag.log` : RAG application logs
- `processing_monitor.log` : Task monitoring logs

### MLflow

Experiment tracking is available via MLflow:
```bash
# Start MLflow UI
mlflow ui --backend-store-uri sqlite:///mlflow.db
```

## 🚀 Deployment

### Docker

```bash
# Build image
docker build -t django-rag-app .

# Run with docker-compose
docker-compose up -d
```

### Production

1. Configure web server (Nginx)
2. Use WSGI server (Gunicorn)
3. Configure PostgreSQL database
4. Configure Redis for Dramatiq
5. Configure S3 storage (optional)

## 🤝 Contributing

1. Fork the project
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License. See the `LICENSE` file for more details.

## 🆘 Support

- Documentation : [GitHub Wiki](https://github.com/Wonters/django-app-rag/wiki)
- Issues : [GitHub Issues](https://github.com/Wonters/django-app-rag/issues)
- Email : shift.python.software@gmail.com

## 🙏 Acknowledgments

- [LangChain](https://github.com/langchain-ai/langchain) for the RAG framework
- [Django](https://www.djangoproject.com/) for the web framework
- [Vue.js](https://vuejs.org/) for the user interface
- [FAISS](https://github.com/facebookresearch/faiss) for vector search
- [Crawl4AI](https://github.com/unclecode/crawl4ai) for web crawling capabilities
- [Docling](https://github.com/DS4SD/docling) for document processing