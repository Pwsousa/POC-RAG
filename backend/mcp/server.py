import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from mcp.server.fastmcp import FastMCP, Context
from mcp.types import CallToolResult

app = FastMCP("mcp-docstore")

@app.tool("write_report")
async def write_report(ctx: Context, filename: str, content: str) -> CallToolResult:
    if not filename.endswith((".txt", ".md")):
        return CallToolResult(content="Erro: Apenas arquivos .txt ou .md são permitidos.")
    safe_filename = os.path.basename(filename)
    os.makedirs("data/output", exist_ok=True)
    path = os.path.join("data/output", safe_filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return CallToolResult(content=f"Relatório salvo com sucesso em {path}")

@app.tool("list_reports")
async def list_reports(ctx: Context) -> CallToolResult:
    os.makedirs("data/output", exist_ok=True)
    files = os.listdir("data/output")
    return CallToolResult(content="\n".join(files) if files else "Nenhum relatório encontrado.")

if __name__ == "__main__":
    app.run(transport="stdio")
