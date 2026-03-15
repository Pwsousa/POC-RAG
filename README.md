# POC-RAG: Sistema de Inteligência Climática (IPCC AR6)

Sistema de RAG (Retrieval-Augmented Generation) agentic para consulta e automação sobre os relatórios do IPCC AR6, operando 100% localmente.

## 🚀 Funcionalidades Principais

- **Ingestão Inteligente**: Download e indexação automática de PDFs e sites do IPCC.
- **Orquestração LangGraph**: Fluxo de agentes (Supervisor, Retriever, Safety, Writer, Self-Check).
- **Citações com Metadados**: Respostas estruturadas com fontes, páginas e trechos originais.
- **Automação (Brief Semanal)**: Geração e arquivamento automático de relatórios comparativos.
- **Model Context Protocol (MCP)**: Integração com servidor de arquivos local para logs e outputs.
- **Processamento Local**: Uso de Ollama (Llama 3.1) e HuggingFace Embeddings (BGE-M3).

## 📁 Estrutura do Projeto

```text
POC-RAG/
├── backend/            # API FastAPI, Agentes e Ingestão
│   ├── api/            # Endpoints da API
│   ├── agents/         # Grafos de agentes (LangGraph)
│   ├── ingest/         # Processamento de documentos e ChromaDB
│   ├── mcp/            # Servidor MCP local
│   ├── tests/          # Testes unitários
│   ├── Dockerfile      # Configuração Docker
│   └── requirements.txt # Dependências do backend
├── frontend/           # Interface Vue 3 + Vite
├── data/               # Armazenamento persistente (Raw PDFs, Chroma, Output)
└── README.md           # Este arquivo
```

## 🛠️ Instalação e Requisitos

Este projeto requer que você tenha instalado:
- **Python 3.10+**
- **Node.js 18+** (para o frontend)
- **Ollama** (para rodar os modelos LLM localmente)

### 1. Configurar o Ollama
- Baixe e instale o [Ollama](https://ollama.com/).
- Após instalar, certifique-se de que o serviço está rodando.
- Baixe o modelo Llama 3.1:
  ```bash
  ollama pull llama3.1
  ```

### 2. Configurar o Backend
- Navegue até a pasta `POC-RAG/backend`.
- Crie um ambiente virtual (opcional, mas recomendado):
  ```bash
  python -m venv venv
  .\venv\Scripts\activate  # No Windows
  source venv/bin/activate # No Linux/Mac
  ```
- Instale as dependências:
  ```bash
  pip install -r requirements.txt
  ```

### 3. Configurar o Frontend
- Navegue até a pasta `POC-RAG/frontend`.
- Instale as dependências do Node:
  ```bash
  npm install
  ```

## 🚀 Como Executar

### 1. Iniciar o Backend
Na raiz da pasta `POC-RAG`, execute:
```bash
python backend/api/main.py
```
A API estará disponível em `http://localhost:8000`.

### 2. Iniciar o Servidor MCP (Opcional)
```bash
python backend/mcp/server.py
```

### 3. Iniciar o Frontend
Na pasta `POC-RAG/frontend`, execute:
```bash
npm run dev
```
Acesse `http://localhost:5173`.

### 4. Indexação Inicial (Primeiro Uso)
Para carregar e indexar os documentos iniciais do IPCC, você pode rodar:
```bash
python backend/ingest/processor.py
```

## 🛡️ Segurança e Políticas

- **Privacidade**: Todos os dados são processados localmente. Nenhuma informação é enviada para APIs pagas (OpenAI, etc.).
- **Allowlist MCP**: O servidor MCP restringe a escrita apenas a arquivos `.txt` e `.md` na pasta `data/output`.
- **Disclaimer**: Todas as respostas incluem um aviso sobre a natureza das projeções climáticas e a importância de consultar a fonte original.

## 📊 Avaliação

Utilize o framework `Ragas` localizado em `backend/eval/` para medir:
- **Faithfulness**: Garantia de que a resposta não alucina.
- **Answer Relevancy**: Precisão da resposta em relação à pergunta.
- **Context Recall**: Eficiência da recuperação de documentos.

## 📝 Licença
Este projeto é distribuído sob a licença MIT.
