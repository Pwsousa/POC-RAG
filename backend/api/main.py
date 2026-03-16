import os
import sys
import json
import asyncio
import threading
import re
import time

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
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.session import ClientSession

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

async def call_mcp_write_report(filename: str, content: str) -> str:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "backend.mcp.server"],
        env=dict(os.environ),
    )
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await asyncio.wait_for(session.initialize(), timeout=10)
            result = await asyncio.wait_for(
                session.call_tool("write_report", arguments={"filename": filename, "content": content}),
                timeout=10
            )
            return str(result.content)

async def call_generic_mcp(command: str, args: list, tool: str, tool_args: dict) -> str:
    params = StdioServerParameters(
        command=command,
        args=args,
        env=dict(os.environ),
    )
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await asyncio.wait_for(session.initialize(), timeout=20)
            result = await asyncio.wait_for(
                session.call_tool(tool, arguments=tool_args),
                timeout=60
            )
            return str(result.content)

def extract_urls(text: str):
    urls = re.findall(r"https?://[^\s)>\]\"']+", text or "")
    return list(dict.fromkeys(urls))

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
    get_workflow()
    model_name = None
    try:
        model_name = getattr(agent_instance.llm, "model", None)
    except Exception:
        model_name = os.getenv("OLLAMA_MODEL", "llama3.1")
    raw_files = os.listdir("data/raw")
    return {
        "files_indexed": len(raw_files),
        "file_list": raw_files,
        "last_update": datetime.now().isoformat(),
        "llm_model": model_name
    }

@app.post("/bootstrap-ar6")
async def bootstrap_ar6(max_pdfs: int = 8, max_pages: int = 8):
    ensure_data_dirs()
    workflow_instance = get_workflow()
    try:
        count = processor.bootstrap_index_ipcc_ar6(max_pdfs=max_pdfs, max_pages=max_pages)
        return {"status": "success", "chunks_indexed": count, "max_pdfs": max_pdfs, "max_pages": max_pages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/bootstrap-firecrawl")
async def bootstrap_firecrawl(start_url: str, max_pages: int = 20):
    ensure_data_dirs()
    get_workflow()
    try:
        cmd = os.getenv("FIRECRAWL_COMMAND", "firecrawl-mcp")
        raw_args = os.getenv("FIRECRAWL_ARGS", "")
        args = [a for a in raw_args.split() if a]
        tool = os.getenv("FIRECRAWL_TOOL", "crawl")
        content = await call_generic_mcp(cmd, args, tool, {"url": start_url, "max_pages": max_pages})
        urls = [u for u in extract_urls(content) if "ipcc.ch" in u]
        if not urls:
            urls = [start_url]
        count = processor.index_documents([], web_urls=urls[:max_pages])
        return {"status": "success", "web_urls_indexed": len(urls[:max_pages]), "chunks_indexed": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/bootstrap-exa")
async def bootstrap_exa(query: str, limit: int = 20):
    ensure_data_dirs()
    get_workflow()
    try:
        cmd = os.getenv("EXA_COMMAND", "exa-mcp")
        raw_args = os.getenv("EXA_ARGS", "")
        args = [a for a in raw_args.split() if a]
        tool = os.getenv("EXA_TOOL", "search")
        content = await call_generic_mcp(cmd, args, tool, {"query": query, "limit": limit})
        urls = [u for u in extract_urls(content) if "ipcc.ch" in u]
        if not urls:
            raise HTTPException(status_code=400, detail="Nenhuma URL relevante encontrada")
        count = processor.index_documents([], web_urls=urls[:limit])
        return {"status": "success", "web_urls_indexed": len(urls[:limit]), "chunks_indexed": count}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _auto_brief_loop():
    try:
        interval = int(os.getenv("AUTO_BRIEF_INTERVAL_MINUTES", "0"))
    except Exception:
        interval = 0
    if interval <= 0:
        return
    while True:
        try:
            wf = get_workflow()
            state: AgentState = {
                "query": "Gere um brief semanal resumindo os principais dados climáticos dos documentos indexados.",
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
            result_state = wf.invoke(state)
            filename = f"brief_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            try:
                asyncio.run(call_mcp_write_report(filename, result_state["answer"]))
            except Exception:
                path = os.path.join("data/output", filename)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(result_state["answer"])
        except Exception as e:
            pass
        time.sleep(interval * 60)

def _auto_bootstrap_on_start():
    try:
        flag = os.getenv("AUTO_BOOTSTRAP_AR6_ON_START", "false").lower() in ("1", "true", "yes")
    except Exception:
        flag = False
    if not flag:
        return
    try:
        wf = get_workflow()
        processor.bootstrap_index_ipcc_ar6(max_pdfs=int(os.getenv("AUTO_BOOTSTRAP_MAX_PDFS", "6")),
                                           max_pages=int(os.getenv("AUTO_BOOTSTRAP_MAX_PAGES", "10")))
    except Exception:
        pass

@app.on_event("startup")
def _startup_tasks():
    threading.Thread(target=_auto_bootstrap_on_start, daemon=True).start()
    threading.Thread(target=_auto_brief_loop, daemon=True).start()

@app.get("/briefs")
async def list_briefs():
    """List generated briefs."""
    ensure_data_dirs()
    files = os.listdir("data/output")
    return {"briefs": files}

@app.post("/generate-brief")
async def generate_brief_on_demand(background_tasks: BackgroundTasks):
    """Trigger a weekly brief generation."""
    try:
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
        
        try:
            result_state = await asyncio.wait_for(
                asyncio.to_thread(workflow_instance.invoke, state),
                timeout=300
            )
        except asyncio.TimeoutError:
            raise HTTPException(status_code=504, detail="Tempo limite excedido ao gerar o brief.")
        
        filename = f"brief_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        mcp_result = ""
        try:
            mcp_result = await call_mcp_write_report(filename, result_state["answer"])
        except Exception as e:
            path = os.path.join("data/output", filename)
            with open(path, "w", encoding="utf-8") as f:
                f.write(result_state["answer"])
            mcp_result = f"Fallback local: {path}. Erro MCP: {str(e)}"
        return {"status": "success", "filename": filename, "mcp_result": mcp_result}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"ERRO NO BRIEF: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
