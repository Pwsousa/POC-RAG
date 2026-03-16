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

Conjunto de testes sugerido:
- 10–20 perguntas rotuladas. Exemplos:
  - Tendência do nível do mar.
  - Principais drivers do aquecimento pós‑1850 
  - Mudanças em extremos de precipitação.
  - Projeções de nível do mar por cenário SSP .
  - Evidências sobre criosfera .
  - Perguntas ambíguas que exigem clarificação (p.ex., “E a chuva no Brasil?”).

Métricas:
- Context Precision / Context Recall.
- Faithfulness.
- Answer Relevancy.
- Latência end‑to‑end.

RAGAS/Giskard:
- RAGAS para medir Faithfulness, Answer Relevancy, Context Precision/Recall (docs em https://docs.ragas.io).
- Giskard para testes de regressão e validações de qualidade.

## 📝 Licença
Este projeto é distribuído sob a licença MIT.

## ⚙️ Automação (Mínimo Viável)
- Tarefas:
  - Brief semanal dos principais achados (Input: corpus atual; Output: markdown em `data/output`).
  - Sumário de evidências por tema (Input: termo, ex. “nível do mar”; Output: bullets com citações).
  - Relatório de incertezas (Input: tópico; Output: lista de incertezas com níveis de confiança).
  - Top‑N trechos por pergunta (Input: query; Output: N trechos com links).
  - Auditoria de citações (Input: resposta; Output: verificação e score de fidelidade).
- Medir:
  - Taxa de sucesso por tarefa.
  - Nº médio de passos na execução.
  - Tempo médio por tarefa.

## 🧩 MCP (Model Context Protocol)
- Servidor local em `backend/mcp/server.py`.
- Ferramentas:
  - `write_report(filename, content)`: grava `.txt`/`.md` em `data/output`.
  - `list_reports()`: lista arquivos em `data/output`.
- Controles:
  - Allowlist de extensões: apenas `.txt` e `.md`.
  - Escopo de escrita restrito a `data/output`.
  - Logs via API e console do backend.
  - O que o agente não pode fazer: escrever fora de `data/output`, criar outros tipos de arquivo, acessar recursos remotos sem rota definida.

## 🔬 Prompt e Recuperação
- Prompt reforçado para:
  - Responder apenas com base no contexto.
  - Incluir citações numeradas [n] vinculadas aos trechos.
  - Recusar quando não houver evidência.
- Recuperação otimizada:
  - MMR com `k` e `fetch_k` configuráveis.
  - Deduplicação por fonte/página.
  - Limite de contexto enviado ao LLM para reduzir latência.
