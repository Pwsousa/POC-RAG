from typing import Annotated, TypedDict, List, Dict, Any, Sequence, Union
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.documents import Document
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
import re
import os
from collections import OrderedDict

# Define the state of our agentic workflow
class AgentState(TypedDict):
    query: str
    mode: str  # 'qa' or 'brief'
    messages: Annotated[Sequence[BaseMessage], "The messages in the conversation"]
    context: List[Document]
    answer: str
    blocks: List[Dict[str, Any]]
    citations: List[Dict[str, Any]]
    is_faithful: bool
    is_safe: bool
    retry_count: int
    steps: List[str]
    is_complete: bool

def parse_answer_to_blocks(answer: str, citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse a string like 'O nível subiu [1] e continuará subindo [2].' into blocks."""
    blocks = []
    # Regex to find [1], [2], etc.
    parts = re.split(r'(\[\d+\])', answer)
    
    for part in parts:
        if not part:
            continue
        citation_match = re.match(r'\[(\d+)\]', part)
        if citation_match:
            citation_id = int(citation_match.group(1))
            # Find the corresponding citation content
            citation = next((c for c in citations if c['id'] == citation_id), None)
            if citation:
                blocks.append({
                    "type": "citation",
                    "content": citation['text'][:100], # Or some relevant snippet
                    "citationId": citation_id
                })
            else:
                blocks.append({"type": "text", "content": part})
        else:
            blocks.append({"type": "text", "content": part})
    return blocks

class AgentGraph:
    def __init__(self, model_name: str = None):
        selected_model = model_name or os.getenv("OLLAMA_MODEL", "llama3.1")
        base_url = os.getenv("OLLAMA_BASE_URL", None)
        temperature = float(os.getenv("OLLAMA_TEMPERATURE", "0"))
        if base_url:
            self.llm = ChatOllama(model=selected_model, temperature=temperature, base_url=base_url)
        else:
            self.llm = ChatOllama(model=selected_model, temperature=temperature)
        print(f"[AgentGraph] LLM: ChatOllama model={selected_model} base_url={base_url or 'default'} temp={temperature}")
        self._cache = OrderedDict()
        self._cache_capacity = int(os.getenv("RETRIEVER_CACHE_SIZE", "128"))
        
    def supervisor(self, state: AgentState) -> Dict[str, Any]:
        """Routes the user query."""
        content = state["query"].lower()
        route = 'qa'
        if 'brief' in content or 'relatório' in content or 'resumo' in content:
            route = 'brief'
        elif 'olá' in content or 'oi' in content:
            route = 'qa'
        
        return {"mode": route, "steps": state.get("steps", []) + ["supervisor_route"]}

    def retriever(self, state: AgentState, retriever_obj) -> Dict[str, Any]:
        """Retrieves documents from vector store."""
        q = state['query'].strip()
        if q in self._cache:
            docs = self._cache.pop(q)
            self._cache[q] = docs
        else:
            docs = retriever_obj.invoke(q)
            if len(self._cache) >= self._cache_capacity:
                self._cache.popitem(last=False)
            self._cache[q] = docs
        # Deduplicate by (source_url or source, page)
        unique = []
        seen = set()
        for d in docs:
            key = (d.metadata.get("source_url") or d.metadata.get("source"), d.metadata.get("page", 0))
            if key in seen:
                continue
            seen.add(key)
            unique.append(d)
        # Cap to a small number for faster context-to-LLM interaction
        max_docs = int(os.getenv("MAX_CTX_DOCS", "3"))
        docs = unique[:max_docs]
        try:
            sources = [d.metadata.get("source", "N/A") for d in docs]
            print(f"[AgentGraph] Retrieved {len(docs)} docs | sources={sources[:5]}")
        except Exception:
            pass
        return {"context": docs, "steps": state.get("steps", []) + ["retriever"]}

    def safety(self, state: AgentState) -> Dict[str, Any]:
        """Adds disclaimer and checks safety."""
        disclaimer = "As projeções climáticas contêm incertezas. Consulte os relatórios originais do IPCC AR6 para decisões críticas."
        if not state.get("answer"):
            refusal = "Não encontrei evidências suficientes nos documentos indexados para responder com segurança."
            return {
                "is_safe": True,
                "answer": refusal + f"\n\n---\n{disclaimer}",
                "blocks": [],
                "citations": [],
                "steps": state.get("steps", []) + ["safety"]
            }
        return {
            "is_safe": True,
            "answer": state.get("answer", "") + f"\n\n---\n{disclaimer}",
            "steps": state.get("steps", []) + ["safety"]
        }

    def writer(self, state: AgentState) -> Dict[str, Any]:
        """Writes the answer with citations."""
        if not state.get("context"):
            refusal = "Não encontrei evidências suficientes nos documentos indexados para responder com citações."
            return {
                "answer": refusal,
                "blocks": [],
                "citations": [],
                "steps": state.get("steps", []) + ["writer_empty_context"]
            }
        prompt = ChatPromptTemplate.from_template(
            "Responda APENAS com base no contexto fornecido e insira citações numeradas [1], [2] correspondentes aos trechos.\n"
            "Se o contexto não trouxer evidência suficiente, responda: \"Não encontrei evidências suficientes nos documentos indexados para responder com segurança.\"\n"
            "Contexto:\n{context}\n"
            "Pergunta: {query}\n"
            "Resposta em Português com citações numeradas:"
        )
        max_ctx = min(2, len(state['context']))
        context_str = "\n".join([
            f"[{i+1}] {d.page_content[:600]} (Fonte: {os.path.basename(d.metadata.get('source', 'N/A')) if isinstance(d.metadata.get('source', ''), str) else d.metadata.get('source', 'N/A')})"
            for i, d in enumerate(state['context'][:max_ctx])
        ])
        print(f"[AgentGraph] Writing answer using {len(state['context'])} context docs")
        msg = self.llm.invoke(prompt.format(context=context_str, query=state['query']))
        
        # Extract citations
        citations = []
        for i, doc in enumerate(state['context'][:max_ctx]):
            src = doc.metadata.get("source", "IPCC AR6")
            is_url = isinstance(src, str) and src.startswith("http")
            document_name = src if is_url else os.path.basename(src) if isinstance(src, str) else "IPCC AR6"
            url = doc.metadata.get("source_url")
            if not url and is_url:
                url = src
            citations.append({
                "id": i + 1,
                "text": doc.page_content,
                "document": document_name,
                "page": doc.metadata.get("page", 0),
                "url": url
            })
        
        print(f"[AgentGraph] Answer length={len(msg.content)} chars | citations={len(citations)}")
        blocks = parse_answer_to_blocks(msg.content, citations)
        return {"answer": msg.content, "blocks": blocks, "citations": citations, "steps": state.get("steps", []) + ["writer"]}

    def self_check(self, state: AgentState) -> Dict[str, Any]:
        """Checks if the answer is faithful to the context."""
        if not state.get("context"):
            return {
                "is_faithful": True,
                "steps": state.get("steps", []) + ["self_check_empty_context"]
            }
        answer = state.get("answer", "")
        has_citations = bool(state.get("citations"))
        cites_in_text = bool(re.search(r"\[\d+\]", answer))
        is_faithful = has_citations and cites_in_text
        retry_count = state.get("retry_count", 0)
        if not is_faithful:
            retry_count += 1
        return {
            "is_faithful": is_faithful,
            "retry_count": retry_count,
            "steps": state.get("steps", []) + ["self_check"]
        }

    def automation_brief(self, state: AgentState) -> Dict[str, Any]:
        """Generates a weekly brief."""
        prompt = ChatPromptTemplate.from_template(
            "Gere um Brief Semanal sobre as principais mudanças e atualizações climáticas baseadas nos documentos indexados.\n"
            "Contexto Recente: {context}"
        )
        context_str = "\n".join([d.page_content for d in state.get("context", [])[:3]])
        msg = self.llm.invoke(prompt.format(context=context_str))
        return {
            "answer": msg.content,
            "blocks": [{"type": "text", "content": msg.content}],
            "citations": [],
            "mode": "brief",
            "steps": state.get("steps", []) + ["automation_brief"]
        }

def create_graph(graph_instance, retriever_obj):
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("supervisor", graph_instance.supervisor)
    workflow.add_node("retriever", lambda x: graph_instance.retriever(x, retriever_obj))
    workflow.add_node("safety", graph_instance.safety)
    workflow.add_node("writer", graph_instance.writer)
    workflow.add_node("self_check", graph_instance.self_check)
    workflow.add_node("automation", graph_instance.automation_brief)
    
    # Define edges
    workflow.set_entry_point("supervisor")
    
    def route_supervisor(state):
        if state["mode"] == "brief":
            return "automation_route"
        elif state["mode"] == "refuse":
            return "end_route"
        else:
            return "qa_route"
            
    workflow.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "automation_route": "retriever",
            "qa_route": "retriever",
            "end_route": END
        }
    )
    
    workflow.add_edge("retriever", "writer")
    workflow.add_edge("writer", "self_check")
    
    def route_self_check(state):
        if state["is_faithful"]:
            return "safety"
        if state.get("retry_count", 0) < 1:
            return "retriever"
        return "safety"
            
    workflow.add_conditional_edges("self_check", route_self_check, {"safety": "safety", "retriever": "retriever"})
    workflow.add_edge("safety", END)
    workflow.add_edge("automation", "safety")
    
    return workflow.compile()
