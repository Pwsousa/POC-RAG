import os
import sys
import json
import asyncio
import threading

# Adiciona o diretório raiz ao sys.path para suportar importações do pacote 'backend'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from backend.ingest.processor import DocumentProcessor
from backend.agents.graph import AgentGraph, create_graph, AgentState
import uuid
from datetime import datetime

app = FastAPI(title="IPCC RAG API")

# Enable CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

processor = None
agent_instance = None
retriever = None
workflow = None
init_lock = threading.Lock()
history = []

def ensure_data_dirs():
    os.makedirs("data/raw", exist_ok=True)
    os.makedirs("data/chroma", exist_ok=True)
    os.makedirs("data/output", exist_ok=True)
    os.makedirs("data/models", exist_ok=True)

def get_workflow():
    global processor, agent_instance, retriever, workflow
    if workflow is None:
        with init_lock:
            if workflow is None:
                ensure_data_dirs()
                processor = DocumentProcessor()
                agent_instance = AgentGraph()
                retriever = processor.get_retriever()
                workflow = create_graph(agent_instance, retriever)
    return workflow

class ChatRequest(BaseModel):
    query: str
    mode: str = "qa"

class ChatResponse(BaseModel):
    id: str
    query: str
    mode: str
    answer: str
    blocks: List[Dict[str, Any]]
    citations: List[Dict[str, Any]]
    disclaimer: str
    timestamp: str

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        workflow_instance = get_workflow()
        # Initial state
        state: AgentState = {
            "query": request.query,
            "mode": request.mode,
            "messages": [],
            "context": [],
            "answer": "",
            "blocks": [],
            "citations": [],
            "is_faithful": False,
            "is_safe": False,
            "retry_count": 0,
            "steps": [],
            "is_complete": False
        }
        
        # Run workflow with timeout to avoid hanging requests
        result_state = await asyncio.wait_for(
            asyncio.to_thread(workflow_instance.invoke, state),
            timeout=300
        )
        
        response = ChatResponse(
            id=str(uuid.uuid4()),
            query=request.query,
            mode=result_state["mode"],
            answer=result_state["answer"],
            blocks=result_state["blocks"],
            citations=result_state["citations"],
            disclaimer="As projeções climáticas contêm incertezas. Este sistema não substitui a leitura integral dos relatórios do IPCC.",
            timestamp=datetime.now().strftime("%d/%m/%Y %H:%M")
        )
        
        # Store in history
        history.insert(0, response)
        return response
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Tempo limite excedido ao gerar resposta.")
    except Exception as e:
        import traceback
        print(f"ERRO NO CHAT: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history", response_model=List[ChatResponse])
async def get_history():
    return history

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload and index a new document."""
    ensure_data_dirs()
    workflow_instance = get_workflow()
    file_path = os.path.join("data/raw", file.filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())
        
    # Index the new file
    count = processor.index_documents([file_path])
    return {"status": "success", "chunks_indexed": count}

@app.get("/logs")
async def get_logs():
    """Get indexing logs."""
    ensure_data_dirs()
    log_path = os.path.join("data", "indexing_log.json")
    if os.path.exists(log_path):
        with open(log_path, 'r') as f:
            return json.load(f)
    return []

@app.get("/status")
async def get_status():
    """Get indexing status."""
    ensure_data_dirs()
    raw_files = os.listdir("data/raw")
    return {
        "files_indexed": len(raw_files),
        "file_list": raw_files,
        "last_update": datetime.now().isoformat()
    }

@app.get("/briefs")
async def list_briefs():
    """List generated briefs."""
    ensure_data_dirs()
    files = os.listdir("data/output")
    return {"briefs": files}

@app.post("/generate-brief")
async def generate_brief_on_demand(background_tasks: BackgroundTasks):
    """Trigger a weekly brief generation."""
    # This would typically be a longer task, so we use background tasks
    workflow_instance = get_workflow()
    query = "Gere um brief semanal resumindo os principais dados climáticos dos documentos indexados."
    state: AgentState = {
        "query": query,
        "mode": "brief",
        "messages": [],
        "context": [],
        "answer": "",
        "blocks": [],
        "citations": [],
        "is_faithful": False,
        "is_safe": False,
        "retry_count": 0,
        "steps": [],
        "is_complete": False
    }
    
    result_state = await asyncio.wait_for(
        asyncio.to_thread(workflow_instance.invoke, state),
        timeout=300
    )
    
    # Use MCP to save (mock for now as MCP client needs more setup)
    filename = f"brief_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    path = os.path.join("data/output", filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(result_state["answer"])
        
    return {"status": "success", "filename": filename}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
