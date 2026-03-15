import os
import sys

# Adiciona o diretório raiz ao sys.path para suportar importações do pacote 'backend'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from typing import Annotated, List, Dict, Any, Optional
from mcp.server.fastapi import Context, Server
from mcp.types import Tool, Resource, CallToolResult
from pydantic import BaseModel, Field
import os

app = Server("mcp-docstore")

class FileWriteRequest(BaseModel):
    filename: str = Field(description="O nome do arquivo a ser criado")
    content: str = Field(description="O conteúdo do arquivo")

@app.tool("write_report")
async def write_report(
    ctx: Context,
    filename: str,
    content: str
) -> CallToolResult:
    """Escreve um relatório de brief semanal na pasta de output."""
    # Allowlist: apenas arquivos .txt ou .md na pasta data/output
    if not filename.endswith((".txt", ".md")):
        return CallToolResult(content="Erro: Apenas arquivos .txt ou .md são permitidos.")
    
    # Path traversal protection
    safe_filename = os.path.basename(filename)
    path = os.path.join("data/output", safe_filename)
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
        
    return CallToolResult(content=f"Relatório salvo com sucesso em {path}")

@app.tool("list_reports")
async def list_reports(ctx: Context) -> CallToolResult:
    """Lista todos os relatórios disponíveis na pasta de output."""
    files = os.listdir("data/output")
    return CallToolResult(content="\n".join(files) if files else "Nenhum relatório encontrado.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
