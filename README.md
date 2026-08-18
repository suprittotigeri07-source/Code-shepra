# Code Sherpa 🧭

Code Sherpa is a full-stack **Semantic Code Exploration Tool** that helps developers make sense of large, unfamiliar codebases using natural language queries instead of reading files top-to-bottom.

Under the hood, Code Sherpa parses source files into semantic chunks, generates vector embeddings, indexes them using a **hybrid search** (vector similarity + full-text indexing), and orchestrates an LLM agent with memory support to answer queries, trace code flows, and map project structures.

---

## 🚀 Active Local Links

Once the servers are running, access the services using these links:

* **React Frontend Application**: [http://localhost:5173/](http://localhost:5173/)
* **FastAPI Backend Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🛠️ Features

* **3-Panel Explorer Interface**:
  * **Repository Tree Panel (Left)**: Real-time file-tree overview with fuzzy search filter.
  * **Semantic Explorer Panel (Center)**: Agentic chat with markdown explanations, real-time agent execution chains, and interactive expandable source citations.
  * **Code Viewer Panel (Right)**: Fully-functional code visualizer featuring syntax highlighting and line numbers.
* **Hybrid Search Engine**: Melds **vector cosine similarity** (via pgvector or local SQLite fallback) with **PostgreSQL/SQLite Full-Text search** using Reciprocal Rank Fusion (RRF).
* **Dual Database Architecture**: Transparently connects to PostgreSQL/pgvector in Docker but includes an automatic **SQLite fallback** (`code_sherpa.db`) with Python-registered functions for cosine distance computations.
* **Agentic Memory**:
  * *Episodic memory*: Remembers previous exploration tracks to build on top of prior context.
  * *Semantic memory*: Allows developer-asserted contexts (assertions, deprecation notes, project choices) to guide LLM responses.
* **AST Parser**: Leverages `tree-sitter` for boundary-aware chunking (functions, classes, modules) rather than arbitrary splits.

---

## 📸 Application Screenshots / Outputs

### 1. 🧭 Code Explorer Dashboard
![Code Explorer Dashboard](C:\Users\supri\Pictures\Screenshots\Screenshot (40).png)
*Clean 3-Panel Explorer layout with Repository Tree, Semantic Explorer Chat with quick prompts, and Code Viewer.*

---

### 2. 🧠 Agent Memory & Context
![Agent Memory and Context](docs/screenshots/02_agent_memory_and_context.png)
*Memory dashboard showing developer-asserted Semantic Context Notes, auto-logged Episodic History, and similarity search.*

---

### 3. ⚙️ Real-Time Agent Execution Chain
![Agent Execution Chain](docs/screenshots/03_agent_execution_chain.png)
*Live streaming of query intent classification and multi-step reasoning steps powered by Server-Sent Events (SSE).*

---

### 4. 🔍 Autonomous Tool Execution & Response
![Agent Response and Tool Calls](docs/screenshots/04_agent_response_and_tool_call.png)
*Agent dynamically executing tools (`search_code`, `read_file`, `list_files`) to synthesize cited codebase explanations.*

---

## 💻 Setup & Run Instructions

### Prerequisites
* **Python 3.10+**
* **Node.js v18+**
* **Ollama** running locally with:
  ```bash
  ollama pull nomic-embed-text
  ollama pull qwen2.5-coder:7b
  ```

### Run using startup script
We've bundled a script to run both servers concurrently and launch the web interface:

```powershell
# Double-click the file or run via terminal:
./start.bat
```

### Run manually
If you prefer running the servers in separate terminals:

**1. Run Backend Server**
```bash
cd backend
python -m pip install -r requirements.txt
python main.py
```

**2. Run Frontend Web App**
```bash
cd frontend
npm install
npm run dev
```

---

## 📦 Pushing to GitHub

Follow these steps to initialize and push your Code Sherpa project to your GitHub repository:

> [!NOTE]
> We have preconfigured a `.gitignore` file to ensure database files (`*.db`), node dependencies (`node_modules`), python cache (`__pycache__`), and virtual environments (`.venv`) are not committed.

```bash
# 1. Initialize Git repository (if not already done)
git init

# 2. Add all files to staging
git add .

# 3. Create initial commit
git commit -m "feat: initial commit of Code Sherpa full-stack codebase"

# 4. Rename default branch to main (standard)
git branch -M main

# 5. Link to your remote GitHub repository
# Replace <github-username> and <repository-name> with your repository info
git remote add origin https://github.com/<github-username>/<repository-name>.git

# 6. Push code to GitHub
git push -u origin main
```

---

## 🌐 Production Deployment Guide

To deploy Code Sherpa to production, you will deploy the **React frontend** and **FastAPI backend** separately.

### 1. Deploy the Backend (FastAPI + Database)
You can deploy the backend to platforms like **Render**, **Railway**, or a **VPS** (AWS EC2, DigitalOcean).

#### Render / Railway (Fastest)
1. Link your GitHub repository.
2. Set the root directory to `backend`.
3. Set the Build Command to: `pip install -r requirements.txt`
4. Set the Start Command to: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Configure Environment Variables:
   - `DATABASE_URL`: Your production PostgreSQL URL (e.g. `postgresql+asyncpg://...`). If not set, it will automatically default to the SQLite file DB.
   - `OLLAMA_BASE_URL`: Your hosted Ollama instance URL (or cloud provider endpoint).
   - `CORS_ORIGINS`: Your deployed frontend URL (e.g. `https://code-sherpa.vercel.app`).

### 2. Deploy the Frontend (React + Vite)
The frontend can be deployed for free on **Vercel**, **Netlify**, or **GitHub Pages**.

#### Vercel
1. Link your GitHub repository.
2. Import the repository in Vercel.
3. Configure the settings:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Add the Environment Variable:
   - `VITE_API_URL`: Your deployed FastAPI backend URL (e.g. `https://code-sherpa-backend.onrender.com`)

