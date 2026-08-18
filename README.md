# 🧭 Code Sherpa

> **AI-powered semantic code exploration for understanding large and unfamiliar codebases using natural language.**

Code Sherpa is a full-stack **Semantic Code Exploration Tool** that helps developers understand large, unfamiliar codebases without manually reading files from top to bottom.

Instead of searching through hundreds of files, developers can ask questions in natural language such as:

* *"Give me a map of the project structure."*
* *"Where is authentication implemented?"*
* *"Explain how the API request flows through the application."*
* *"Show me the code responsible for database connections."*
* *"What does this function do?"*
* *"Which files are related to this feature?"*

Under the hood, Code Sherpa parses source files into semantic chunks, generates vector embeddings, performs hybrid search, and uses an LLM agent to provide contextual answers with code references.

---

## ✨ Key Highlights

* 🤖 **AI-powered code exploration**
* 🔍 **Natural-language code search**
* 🌳 **Repository structure visualization**
* 🧠 **Agentic memory**
* 🔗 **Code-flow and dependency exploration**
* 📚 **AST-based semantic chunking**
* ⚡ **Hybrid vector + full-text search**
* 🗃️ **PostgreSQL/pgvector support**
* 💾 **SQLite fallback**
* 💬 **Conversational follow-up questions**
* 📝 **Markdown-based AI responses**
* 🎯 **Interactive source citations**
* 🎨 **Three-panel developer interface**

---

## 🖥️ Application Preview

Code Sherpa provides a developer-focused three-panel interface for exploring an entire codebase.

### 📸 Output / Screenshots

#### 1. Code Sherpa Explorer Dashboard

The main Code Sherpa interface provides a repository tree, semantic AI explorer, and code viewer in a single workspace.

![Code Sherpa Dashboard](docs/images/dashboard.png)

---

#### 2. AI Semantic Code Exploration

Developers can ask questions about the codebase using natural language and receive contextual explanations from the AI agent.

![Semantic Code Exploration](docs/images/semantic-explorer.png)

---

#### 3. Code Understanding & AI Responses

Code Sherpa can answer questions about specific code concepts and explain implementation details interactively.

![Code Exploration](docs/images/code-exploration.png)

---

## 🚀 Features

### 🌳 1. Repository Tree Explorer

The left-side repository panel provides an overview of the indexed project structure.

Features include:

* Repository file-tree visualization
* File filtering
* Fuzzy search
* Project selection
* File navigation
* Indexed source overview

This allows developers to quickly understand how a project is organized.

---

### 🤖 2. Semantic Explorer

The center panel acts as the AI-powered exploration interface.

Developers can ask questions such as:

```text
Give me a map of the project structure.
```

or:

```text
Where is the database connection implemented?
```

or:

```text
Explain how authentication works in this project.
```

The AI analyzes the relevant code and generates a contextual explanation.

---

### 💻 3. Code Viewer

The right-side panel provides an interactive code viewer.

It is designed to support:

* Syntax highlighting
* Line numbers
* Source navigation
* File selection
* Code inspection
* Source references from AI responses

This allows developers to move directly from an AI explanation to the corresponding source code.

---

### 🔍 4. Hybrid Search

Code Sherpa combines multiple search techniques to improve code retrieval.

The search system combines:

**Vector similarity search**

with

**Full-text search**

using **Reciprocal Rank Fusion (RRF)**.

Conceptually:

```text
Natural Language Query
        │
        ▼
 ┌───────────────┐
 │ Query Analysis│
 └───────┬───────┘
         │
    ┌────┴─────┐
    ▼          ▼
Vector Search  Full-Text Search
    │          │
    └────┬─────┘
         ▼
 Reciprocal Rank Fusion
         │
         ▼
 Relevant Code Chunks
         │
         ▼
      LLM Agent
         │
         ▼
 Contextual Answer
```

This approach allows Code Sherpa to find relevant code based on both **meaning** and **exact textual matches**.

---

### 🧠 5. Agentic Memory

Code Sherpa supports memory to make code exploration more useful across multiple interactions.

#### Episodic Memory

Stores previous exploration interactions and allows the agent to build on earlier discussions.

Example:

```text
User:
Where is authentication implemented?

Code Sherpa:
Authentication is implemented in...

User:
How does that connect to the database?

Code Sherpa:
Based on the authentication flow discussed earlier...
```

#### Semantic Memory

Allows developers to store useful project-level knowledge.

Examples:

```text
The old authentication module is deprecated.
```

```text
PostgreSQL is the primary production database.
```

```text
This service should not be modified because it is shared by multiple applications.
```

This information can then influence future AI responses.

---

### 🌲 6. AST-Based Code Parsing

Code Sherpa uses **Tree-sitter** to understand source-code structure.

Instead of splitting files into arbitrary text blocks, the parser identifies meaningful programming constructs such as:

* Functions
* Classes
* Methods
* Modules
* Imports
* Code blocks

For example:

```text
Source File
    │
    ▼
Tree-sitter AST
    │
    ├── Class
    ├── Function
    ├── Method
    ├── Import
    └── Module
```

This produces more meaningful semantic chunks for embedding and retrieval.

---

## 🏗️ System Architecture

```text
                    ┌──────────────────────┐
                    │      Developer       │
                    └──────────┬───────────┘
                               │
                         Natural Language
                               │
                               ▼
                    ┌──────────────────────┐
                    │   React + Vite UI    │
                    │                      │
                    │  Repository Explorer │
                    │  Semantic Explorer    │
                    │  Code Viewer         │
                    └──────────┬───────────┘
                               │
                              API
                               │
                               ▼
                    ┌──────────────────────┐
                    │    FastAPI Backend   │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
       ┌────────────┐   ┌──────────────┐   ┌────────────┐
       │ AST Parser │   │ Hybrid Search│   │ AI Agent   │
       │ Tree-sitter│   │ Vector + FTS │   │ + Memory   │
       └─────┬──────┘   └──────┬───────┘   └─────┬──────┘
             │                 │                 │
             └─────────────────┼─────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ PostgreSQL + pgvector│
                    │          OR          │
                    │       SQLite         │
                    └──────────────────────┘
                               │
                               ▼
                         Ollama / LLM
```

---

## 🛠️ Technology Stack

| Layer                | Technology                           |
| -------------------- | ------------------------------------ |
| Frontend             | React.js                             |
| Build Tool           | Vite                                 |
| Backend              | FastAPI                              |
| Programming Language | Python                               |
| Database             | PostgreSQL                           |
| Vector Database      | pgvector                             |
| Fallback Database    | SQLite                               |
| Code Parser          | Tree-sitter                          |
| Embeddings           | nomic-embed-text                     |
| LLM                  | Qwen 2.5 Coder 7B                    |
| Local AI Runtime     | Ollama                               |
| Search               | Vector Similarity + Full-Text Search |
| Ranking              | Reciprocal Rank Fusion               |
| API Documentation    | FastAPI Swagger / OpenAPI            |

---

## 🗄️ Dual Database Architecture

Code Sherpa supports two database configurations.

### PostgreSQL + pgvector

For production and larger projects, Code Sherpa can use PostgreSQL with pgvector.

```text
PostgreSQL
     │
     ├── Project Metadata
     ├── Code Chunks
     ├── Embeddings
     ├── Full-Text Search
     └── Memory
```

### SQLite Fallback

For local development, Code Sherpa can automatically fall back to:

```text
code_sherpa.db
```

The SQLite implementation supports vector similarity through Python-registered functions.

This makes the application easier to run without requiring PostgreSQL during initial development.

---

## 🤖 Local AI Models

Code Sherpa is designed to work with Ollama for local AI inference.

Required models:

### Embedding Model

```bash
ollama pull nomic-embed-text
```

### Code LLM

```bash
ollama pull qwen2.5-coder:7b
```

Verify installed models:

```bash
ollama list
```

---

## 📋 Prerequisites

Before running Code Sherpa, make sure you have:

* **Python 3.10+**
* **Node.js 18+**
* **npm**
* **Ollama**
* **Git**

For the PostgreSQL configuration:

* PostgreSQL
* pgvector extension

---

## 📁 Project Structure

A typical project structure looks like:

```text
Code-Sherpa/
│
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   └── ...
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── ...
│
├── docs/
│   └── images/
│       ├── dashboard.png
│       ├── semantic-explorer.png
│       └── code-exploration.png
│
├── .gitignore
├── start.bat
└── README.md
```

---

# 🚀 Setup & Run

## 1. Clone the Repository

```bash
git clone https://github.com/<github-username>/<repository-name>.git
```

Move into the project:

```bash
cd Code-Sherpa
```

---

## 2. Start Ollama

Make sure Ollama is running locally.

Pull the required models:

```bash
ollama pull nomic-embed-text
ollama pull qwen2.5-coder:7b
```

---

## 3. Run the Backend

Open a terminal:

```bash
cd backend
```

Install Python dependencies:

```bash
python -m pip install -r requirements.txt
```

Start the backend:

```bash
python main.py
```

Or, if using Uvicorn directly:

```bash
uvicorn main:app --reload
```

Backend will be available at:

```text
http://localhost:8000
```

---

## 4. Run the Frontend

Open another terminal:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

Frontend will be available at:

```text
http://localhost:5173
```

---

## ⚡ Run Everything Using `start.bat`

A startup script is included to simplify local development.

From the project root:

```powershell
./start.bat
```

Or double-click:

```text
start.bat
```

The script can be used to launch the frontend and backend together.

---

## 🌐 Local Application Links

Once the application is running:

### Frontend

http://localhost:5173/

### FastAPI Swagger Documentation

http://localhost:8000/docs

### FastAPI OpenAPI Schema

http://localhost:8000/openapi.json

---

## 🔄 Code Exploration Workflow

The typical Code Sherpa workflow is:

```text
1. Start Code Sherpa
        │
        ▼
2. Select / ingest a project
        │
        ▼
3. Parse source files
        │
        ▼
4. Generate semantic chunks
        │
        ▼
5. Generate embeddings
        │
        ▼
6. Index code
        │
        ▼
7. Ask a natural-language question
        │
        ▼
8. Hybrid search retrieves relevant code
        │
        ▼
9. LLM analyzes retrieved context
        │
        ▼
10. AI generates explanation
        │
        ▼
11. Developer explores referenced code
```

---

## 💬 Example Queries

Once a project has been indexed, you can ask questions like:

### Project Structure

```text
Give me a map of the project structure.
```

### Authentication

```text
Where is authentication implemented?
```

### Database

```text
Explain how the application connects to the database.
```

### API Flow

```text
Trace the flow of a request from the API endpoint to the database.
```

### Function Explanation

```text
Explain what this function does and why it is used.
```

### Dependencies

```text
Which files depend on this module?
```

### Debugging

```text
Where could this error originate from?
```

### Architecture

```text
Explain the overall architecture of this project.
```

---

## 🔎 Hybrid Search Architecture

Code Sherpa retrieves relevant code using two complementary approaches.

### Vector Search

Vector embeddings represent the semantic meaning of code.

For example:

```text
Query:
"Where is user authentication handled?"

        ↓

Embedding

        ↓

Semantic similarity search

        ↓

Relevant authentication code
```

### Full-Text Search

Full-text search finds exact keywords and identifiers.

```text
authentication
login
JWT
token
OAuth
```

### Reciprocal Rank Fusion

Results from both systems are combined using Reciprocal Rank Fusion.

```text
Vector Search
     │
     ├── Result A
     ├── Result B
     └── Result C
     
Full-Text Search
     │
     ├── Result B
     ├── Result D
     └── Result A

          ↓

   Reciprocal Rank Fusion

          ↓

   Final Ranked Results
```

---

## 🧠 Why Code Sherpa?

Traditional code exploration often requires developers to:

```text
Open File
   ↓
Read Code
   ↓
Search References
   ↓
Open Another File
   ↓
Understand Dependencies
   ↓
Repeat
```

Code Sherpa changes this workflow to:

```text
Ask a Question
      ↓
AI Searches the Codebase
      ↓
Relevant Code Retrieved
      ↓
AI Explains the Context
      ↓
Developer Opens Source
```

This makes unfamiliar codebases easier to understand and navigate.

---

## 🔐 Environment Variables

Depending on the configuration, Code Sherpa can use environment variables such as:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/code_sherpa

OLLAMA_BASE_URL=http://localhost:11434

OLLAMA_MODEL=qwen2.5-coder:7b

CORS_ORIGINS=http://localhost:5173
```

> **Note:** Do not commit `.env` files or production credentials to GitHub.

---

# 📦 GitHub Deployment

Initialize Git if required:

```bash
git init
```

Add files:

```bash
git add .
```

Commit:

```bash
git commit -m "feat: initial commit of Code Sherpa full-stack codebase"
```

Rename the branch:

```bash
git branch -M main
```

Add your GitHub repository:

```bash
git remote add origin https://github.com/<github-username>/<repository-name>.git
```

Push:

```bash
git push -u origin main
```

---

## 🚀 Production Deployment

Code Sherpa can be deployed by hosting the frontend and backend separately.

### Backend

Possible platforms:

* Render
* Railway
* AWS EC2
* DigitalOcean
* Other VPS/cloud providers

Recommended backend configuration:

```text
Root Directory:
backend

Build Command:
pip install -r requirements.txt

Start Command:
uvicorn main:app --host 0.0.0.0 --port $PORT
```

Configure production environment variables:

```env
DATABASE_URL=<production-postgresql-url>

OLLAMA_BASE_URL=<hosted-ollama-url>

CORS_ORIGINS=<deployed-frontend-url>
```

---

## 🌐 Frontend Deployment

The React/Vite frontend can be deployed using:

* Vercel
* Netlify
* GitHub Pages

### Vercel Configuration

```text
Framework:
Vite

Root Directory:
frontend

Build Command:
npm run build

Output Directory:
dist
```

Set the API URL:

```env
VITE_API_URL=https://your-backend-url.com
```

---

## 🛡️ Security Considerations

Before deploying Code Sherpa publicly:

* Never commit `.env` files.
* Never expose database passwords.
* Never expose private API keys.
* Configure CORS correctly.
* Use HTTPS in production.
* Restrict database access.
* Use authentication for sensitive deployments.
* Keep Ollama endpoints private unless properly secured.

---

## 🧪 Development

For development, it is recommended to run:

### Backend

```bash
cd backend
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm run dev
```

This allows frontend and backend changes to be tested independently.

---

## 📌 Current Status

Code Sherpa is currently being developed as a full-stack AI-powered semantic code exploration platform.

### Implemented

* [x] React frontend
* [x] FastAPI backend
* [x] Three-panel explorer interface
* [x] Semantic AI chat
* [x] Repository explorer
* [x] Code viewer
* [x] Ollama integration
* [x] Code embeddings
* [x] Hybrid search architecture
* [x] PostgreSQL/pgvector support
* [x] SQLite fallback
* [x] Tree-sitter AST parsing
* [x] Agentic memory architecture
* [x] Follow-up conversation mode
* [x] Swagger/OpenAPI documentation

### Future Improvements

* [ ] GitHub repository integration
* [ ] GitLab repository integration
* [ ] Improved dependency graph visualization
* [ ] Multi-language AST support
* [ ] Advanced code-flow visualization
* [ ] Authentication and user accounts
* [ ] Cloud-based LLM support
* [ ] Team/project collaboration
* [ ] Advanced project analytics
* [ ] Production-grade vector database optimization

---

## 🤝 Contributing

Contributions are welcome.

### 1. Fork the repository

```bash
git fork <repository-url>
```

### 2. Create a feature branch

```bash
git checkout -b feature/your-feature
```

### 3. Make your changes

Implement and test your changes locally.

### 4. Commit your changes

```bash
git add .
git commit -m "feat: add your feature"
```

### 5. Push your branch

```bash
git push origin feature/your-feature
```

### 6. Create a Pull Request

Open a pull request describing your changes.

---

## 📄 License

This project is currently intended for educational, experimental, and development purposes.

Add your preferred open-source license before publishing the project for external contributions.

---

## 👨‍💻 Author

**Suprit Totiger**

Full-Stack Developer | AI/ML Enthusiast | Generative AI Developer

Interested in:

* Artificial Intelligence
* Machine Learning
* Generative AI
* Full-Stack Development
* Backend Engineering
* Semantic Search
* Developer Tools

---

## ⭐ Support

If you find **Code Sherpa** useful, consider giving the repository a ⭐ on GitHub.

Your feedback and contributions are welcome!

---

## 🧭 Code Sherpa

> **"Don't read the entire codebase. Ask it."**

---
