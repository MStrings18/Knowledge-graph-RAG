# 📌 Knowledge Graph RAG (Retrieval-Augmented Generation)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white) ![React](https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black) ![TailwindCSS](https://img.shields.io/badge/TailwindCSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white) ![Neo4j](https://img.shields.io/badge/Neo4j-008CC1?style=for-the-badge&logo=neo4j&logoColor=white) ![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white) ![spaCy](https://img.shields.io/badge/spaCy-FF0000?style=for-the-badge&logo=spacy&logoColor=white) ![PDFPlumber](https://img.shields.io/badge/PDFPlumber-0A0A0A?style=for-the-badge&logo=adobeacrobat&logoColor=white) ![Google Gemini](https://img.shields.io/badge/Google%20Gemini-4285F4?style=for-the-badge&logo=google&logoColor=white) ![LangGraph](https://img.shields.io/badge/LangGraph-FF9900?style=for-the-badge)


---

## Table of Contents
- [Overview](#overview)
- [Features](#features)
  - [Document Processing](#document-processing)
  - [Intelligent Retrieval](#intelligent-retrieval)
  - [User Management](#user-management)
  - [Insurance Features](#insurance-features)
  - [Chat Interface](#chat-interface)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Environment Variables](#environment-variables)
- [Setup](#setup)
  - [Install Dependencies](#1-install-dependencies)
  - [Initialize databases](#2-initialize-databases)
  - [Start Servers](#3-start-servers)
- [Project Structure](#project-structure)
- [Architecture Overview](#architecture-overview)
- [Contributing](#contributing)
- [License \& Disclaimer](#license--disclaimer)

## Overview
Knowledge Graph RAG is a document Q&A system that combines Neo4j knowledge graphs with LLM-based retrieval to provide context-aware answers. Users can upload PDFs, extract key entities, and query documents intelligently. The system supports user authentication, chat history, and insurance-specific workflows like policy updates, claims filing, and credential management, all through a real-time chat interface.

## Features

### Document Processing
- PDF upload and intelligent chunking  
- Named Entity Recognition (NER) with **spaCy**  
- Keyword extraction and filtering  
- Automatic **Neo4j knowledge graph construction**  

### Intelligent Retrieval
- Graph-based document retrieval  
- Context-aware answers via **Google Gemini LLM**  
- Configurable **retrieval depth & relevance scoring**  

### User Management
- User registration & authentication  
- Secure credential storage  
- Session management  

### Insurance Features
- Insurance credential management  
- Policy updates & claims filing  
- Secure password change  

### Chat Interface
- Real-time messaging  
- Document upload during chat  
- Chat history & **thread-based conversations**  

---

## Tech Stack

**Backend**
- FastAPI web framework
- Neo4j graph database
- SQLite for user/thread data
- spaCy for NER
- Google Gemini for LLM
- LangGraph for workflow
- PDFPlumber for document parsing 

**Frontend**
- React + React Router  
- TailwindCSS  
- React Toastify  

---

## Prerequisites

- **Python** 3.10+  
- **Node.js** 18+  
- **Neo4j** 5.x (Local or [AuraDB](https://neo4j.com/cloud/aura/))  

---

## Environment Variables

Create a `.env` file in the project root:

```env
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# LLM
GEMINI_API_KEY=your_gemini_key

# Database
DATABASE_URL=sqlite:///./app.db
```

---
##  Setup

### 1. Install Dependencies
```bash
#Backend
pip install -r requirements.txt

#Frontend
cd frontend
npm install
```

### 2. Initialize databases
```bash
python -m backend.database
python -m backend.mock_insurance_db
```

### 3. Start Servers
```bash
# Backend
uvicorn backend.API:app --reload --port 8000

# Frontend
cd frontend
npm run dev
```

## Project Structure
```bash
├── backend/
|   |__config.py 
│   ├── API.py                # FastAPI routes
│   ├── chunker2.py           # PDF processing
│   ├── database.py           # Main DB operations
│   ├── gemini_client.py      # LLM integration
│   ├── graph_builder2.py     # Neo4j graph construction
│   ├── graph_pipeline.py     # Core pipeline
│   ├── graph_retriever2.py   # Graph-based retrieval
│   ├── ner_extractor.py      # Entity extraction
│   └── mock_*.py              # Mock services
├── frontend/
│   └── src/
│       ├── Pages/            # React components
│       └── Router/           # Route configuration               # Configuration settings
└── main.py                   # Entry point
```

## Architecture Overview
![Architecture Diagram](assets/image.svg)

## Contributing

- Fork the repository
- Create a feature branch (git checkout -b feature/your-feature)
- Commit your changes (git commit -m "Add feature")
- Push to your branch (git push origin feature/your-feature)
- Open a Pull Request

## License & Disclaimer
⚠️ Disclaimer: This project is for research and demonstration purposes only.
It does not provide legal or financial insurance advice.







