# RAGio - AI-Powered Document Analysis Platform

<div align="center">

<img src="Images/logo.svg" alt="RAGio Logo" width="200"/>

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.12+-green.svg)
![React](https://img.shields.io/badge/react-18.3.1-61dafb.svg)
![FastAPI](https://img.shields.io/badge/fastapi-0.104.1-009688.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

**A comprehensive full-stack application that combines document processing, AI-powered chat, and intelligent document analysis using Retrieval-Augmented Generation (RAG) technology.**

[Features](#features) • [Installation](#installation) • [Documentation](#api-documentation) • [Deployment](#deployment) • [Contributing](#contributing)

</div>

---

## Screenshots

### Landing Page

![Landing Page](Images/landing.png)

### Document Management

![Files List](Images/files_list.png)

### PDF Document Chat

![PDF Chat Interface](Images/pdf_chat.png)

### CSV Document Chat

![CSV Chat Interface](Images/csv_chat.png)

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Deployment](#deployment)
- [Project Structure](#project-structure)
- [Monitoring & Observability](#monitoring--observability)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

**RAGio** is an enterprise-grade document analysis platform that leverages advanced AI technologies to help users interact with their documents intelligently. The platform uses Retrieval-Augmented Generation (RAG) to provide accurate, context-aware responses based on document content.

### Key Capabilities

- **Multi-format Document Processing**: PDF, CSV, TXT
- **AI-Powered Chat**: Context-aware conversations with your documents
- **Semantic Search**: Advanced vector search using Qdrant
- **Multi-Document Analysis**: Ask questions across multiple documents simultaneously
- **Secure Authentication**: JWT-based user authentication and authorization
- **Real-time Monitoring**: Comprehensive observability with Prometheus, Loki, and Grafana

---

## Features

### AI-Powered Document Analysis

- **RAG Technology**: Multi-stage retrieval-augmented generation pipeline
  - Query expansion using LLM
  - Hybrid retrieval (dense + sparse/BM25)
  - BGE re-ranking for quality
  - Cross-encoder verification
  - Context assembly with deduplication
- **Multi-Document Chat**: Simultaneous analysis across multiple documents
- **Intelligent Search**: Semantic vector search with Qdrant
- **Cross-Document Analysis**: Compare and synthesize information from multiple sources
- **Source Attribution**: Clear indication of information sources with page references

### Document Processing

- **Multi-Format Support**: PDF, CSV, TXT files
- **Document Viewer**: Built-in viewers for various file formats
- **File Management**: Secure storage with MinIO object storage
- **Background Processing**: Async document processing with Celery

### Advanced Chat System

- **Context-Aware Conversations**: AI remembers conversation context
- **Multi-Document Chat**: Ask questions spanning multiple documents
- **Real-time Responses**: Fast, intelligent answers with source citations
- **Chat History**: Persistent conversation history with caching
- **Token Management**: Intelligent handling of large documents
- **Suggested Questions**: AI-generated question suggestions

### Security & Authentication

- **JWT Authentication**: Secure user authentication with access and refresh tokens
- **User Management**: Registration, login, and session management
- **File Ownership**: Secure document access control
- **CORS Protection**: Configurable cross-origin request security
- **Rate Limiting**: API rate limiting to prevent abuse
- **Input Validation**: Comprehensive data validation

### Performance & Scalability

- **Database Optimization**: PostgreSQL with connection pooling
- **Vector Search**: High-performance semantic search with Qdrant
- **Background Processing**: Async document processing with Celery workers
- **Health Monitoring**: Comprehensive system monitoring
- **Production Ready**: Multi-worker uvicorn configuration

### Observability

- **Prometheus Metrics**: Application and system metrics
- **Loki Logging**: Centralized log aggregation
- **Grafana Dashboards**: Pre-configured dashboards for monitoring
- **Health Checks**: Detailed health endpoints
- **Performance Tracking**: Request tracing and performance monitoring

---

## Technology Stack

### Frontend

- **React 18.3.1** - Modern UI framework
- **React Router 6** - Client-side routing
- **Axios** - HTTP client for API communication
- **Zustand** - State management
- **React Hook Form** - Form management
- **Tailwind CSS** - Utility-first CSS framework
- **Flowbite React** - UI component library

### Backend

- **FastAPI 0.104.1** - High-performance Python web framework
- **SQLAlchemy 2.0** - Database ORM
- **PostgreSQL 15** - Primary database
- **Qdrant** - Vector database for semantic search
- **MinIO** - Object storage for documents
- **Redis 7** - Caching and Celery broker
- **Celery 5.3** - Distributed task queue
- **Uvicorn** - ASGI server

### AI/ML

- **LangChain** - AI/ML framework
- **OpenRouter API** - LLM provider (Mistral, Llama, etc.)
- **Sentence Transformers** - Text embeddings (all-MiniLM-L6-v2)
- **Cross-Encoder** - Re-ranking models (ms-marco-MiniLM-L-6-v2)
- **Hugging Face Transformers** - Model loading and inference

### DevOps & Monitoring

- **Docker** - Containerization
- **Docker Compose** - Multi-service orchestration
- **Prometheus** - Metrics collection
- **Loki** - Log aggregation
- **Grafana** - Visualization and dashboards
- **Flower** - Celery monitoring

---

## Architecture

![Architecture](Images/architecture.png)

### Key Components

1. **Frontend**: React SPA with modern UI components
2. **Backend API**: FastAPI REST API with async support
3. **RAG Pipeline**: Multi-stage retrieval and generation pipeline
4. **Vector Database**: Qdrant for semantic search
5. **Object Storage**: MinIO for document storage
7. **Task Queue**: Celery for background document processing
8. **Monitoring**: Prometheus, Loki, and Grafana stack

---

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.12+**
- **Node.js 18+** and npm
- **Docker** and **Docker Compose**
- **Git**

### System Requirements

- **RAM**: Minimum 8GB (16GB recommended)
- **Storage**: 10GB+ free space
- **CPU**: Multi-core processor recommended

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/ragio.git
cd ragio
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your configuration
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Copy environment template
cp .env.example .env
# Edit .env and set REACT_APP_API_URL
```

### 4. Start Services

```bash
cd backend

# Start all Docker services (PostgreSQL, Redis, MinIO, Qdrant, etc.)
docker-compose up -d

# Start the backend server
python start.py

# Or start manually
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### 5. Start Frontend

```bash
cd frontend
npm start
```

The application will be available at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8080
- **API Docs**: http://localhost:8080/docs
- **Grafana**: http://localhost:3001
- **MinIO Console**: http://localhost:9001

---

## Configuration

### Backend Environment Variables

Create `backend/.env` from `backend/.env.example`:

```env
# Application
ENVIRONMENT=development
HOST=0.0.0.0
PORT=8080

# Database
DATABASE_URL=postgresql://postgres:admin@localhost:5432/hcp

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=documents

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Security (IMPORTANT: Generate strong keys!)
SECRET_KEY=your-secret-key-here
REFRESH_SECRET_KEY=your-refresh-secret-key-here

# CORS
ALLOWED_ORIGINS=http://localhost:3000
ALLOWED_HOSTS=localhost,127.0.0.1

# AI/ML
OPENROUTER_API_KEY=your-openrouter-api-key
OPENROUTER_MODEL=mistralai/mistral-7b-instruct:free
```

### Frontend Environment Variables

Create `frontend/.env`:

```env
REACT_APP_API_URL=http://localhost:8080
```

### Generate Secret Keys

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

---


## API Documentation

### Authentication Endpoints

```bash
POST /api/auth/register    # User registration
POST /api/auth/login        # User login
POST /api/auth/refresh     # Refresh access token
POST /api/auth/logout      # User logout
```

### Document Management

```bash
POST   /api/document/upload           # Upload and process documents
GET    /api/document/files            # List user's documents
GET    /api/document/{id}              # Get document details
DELETE /api/document/{id}              # Delete document
GET    /api/document/{id}/download    # Download document
```

### Chat Endpoints

```bash
POST /api/chat/{file_id}                    # Chat with single document
GET  /api/chat/messages/{file_id}           # Get chat history

POST /api/chat/general                      # General chat (all documents)
GET  /api/chat/general/messages             # General chat history
```

### Health & Monitoring

```bash
GET /api/health/           # Basic health check
GET /api/health/detailed   # Detailed health with metrics
GET /api/health/metrics    # System and application metrics
GET /metrics               # Prometheus metrics endpoint
```

### Interactive API Documentation

- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc

---


#### Quick Start

```bash
# Backend
cd backend
cp .env.example .env
# Edit .env with production values
docker-compose -f docker-compose.prod.yml up -d --build

# Frontend
cd frontend
cp .env.example .env
# Set REACT_APP_API_URL to production backend URL
npm run build
# Deploy build/ folder to your web server
```

### Docker Compose Production

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Environment Variables for Production

- Set `ENVIRONMENT=production`
- Generate strong `SECRET_KEY` and `REFRESH_SECRET_KEY`
- Update `ALLOWED_ORIGINS` with production domains
- Configure SSL/HTTPS
- Set up proper database credentials

---

## Project Structure

```
ragio/
├── backend/
│   ├── app/
│   │   ├── db/              # Database models and connection
│   │   ├── middleware/      # Custom middleware (error, rate limit, etc.)
│   │   ├── routes/          # API endpoints
│   │   ├── services/        # Business logic (RAG, chat, etc.)
│   │   ├── tasks/           # Celery background tasks
│   │   └── utils/           # Utilities (logger, auth, etc.)
│   ├── grafana/             # Grafana dashboards and provisioning
│   ├── loki/                # Loki configuration
│   ├── prometheus/          # Prometheus configuration
│   ├── promtail/            # Promtail configuration
│   ├── docker-compose.yml   # Development docker-compose
│   ├── docker-compose.prod.yml  # Production docker-compose
│   ├── Dockerfile           # Multi-stage Dockerfile
│   ├── requirements.txt     # Python dependencies
│   ├── start.py             # Startup script
│   └── .env.example         # Environment template
│
├── frontend/
│   ├── public/              # Static assets
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── hooks/           # Custom React hooks
│   │   ├── stores/          # Zustand state management
│   │   └── utils/           # Utilities
│   ├── package.json         # Node dependencies
│   └── .env.example         # Environment template
│
└── README.md                # This file
```

---

## Monitoring & Observability

### Grafana Dashboards

Access Grafana at http://localhost:3001 (default credentials: admin/admin)

Pre-configured dashboards:
- **API Performance**: Request rates, latency, error rates
- **Backend Latency**: Response time metrics
- **Celery Workers**: Task queue monitoring
- **Error Rate**: Error tracking and alerts
- **RAG Pipeline**: RAG-specific metrics
- **Logs Overview**: Centralized log viewing

### Prometheus Metrics

- **Application Metrics**: Custom business metrics
- **System Metrics**: CPU, memory, disk usage
- **Database Metrics**: Connection pool stats
- **Celery Metrics**: Task execution metrics

### Health Checks

```bash
# Basic health
curl http://localhost:8080/api/health/

# Detailed health with metrics
curl http://localhost:8080/api/health/detailed

# Prometheus metrics
curl http://localhost:8080/metrics
```

---

## Testing



### Integration Tests

```bash
# Test API endpoints
curl http://localhost:8080/api/health/

# Test authentication
curl -X POST http://localhost:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'
```

---


---

## Contributing

Contributions are welcome! Please follow these steps:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**
4. **Commit changes**: `git commit -m 'Add amazing feature'`
5. **Push to branch**: `git push origin feature/amazing-feature`
6. **Open a Pull Request**

### Code Guidelines

- **Backend**: Follow PEP 8 style guidelines
- **Frontend**: Use ESLint and Prettier
- **Tests**: Add tests for new features
- **Documentation**: Update docs for API changes
- **Commits**: Use conventional commit messages

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- **FastAPI** - Excellent Python web framework
- **React** - Powerful frontend library
- **LangChain** - AI/ML framework
- **Qdrant** - Vector search database
- **MinIO** - Object storage
- **OpenRouter** - LLM API provider
- **Hugging Face** - Model hub and transformers

---

## Support


- **API Docs**: http://localhost:8080/docs (when running)
- **Issues**: [GitHub Issues](https://github.com/simoderyouch/ragio/issues)
- **Discussions**: [GitHub Discussions](https://github.com/simoderyouch/ragio/discussions)

---

## Roadmap

### Upcoming Features

- [ ] Real-time collaboration
- [ ] Advanced analytics and insights
- [ ] Mobile app (React Native)
- [ ] OCR with more languages
- [ ] Document versioning
- [ ] Export chat conversations
- [ ] Webhook support for integrations
- [ ] Advanced search filters

### Performance Improvements

- [ ] CDN integration for static assets
- [ ] Database query optimization
- [ ] Enhanced caching strategies
- [ ] Load balancing support
- [ ] Horizontal scaling

---

<div align="center">

**Built with FastAPI, React, PostgreSQL, Redis, Qdrant, MinIO, and AI/ML technologies**

Star this repo if you find it helpful!

</div>
