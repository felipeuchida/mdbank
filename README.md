# MDBank

MDBank é um **banco digital de demonstração** construído sobre uma arquitetura de **múltiplos agentes de IA**. O sistema simula o atendimento de um banco (abertura de conta e emissão de cartão de crédito) usando LLMs orquestrados por um agente supervisor.

A solução combina três padrões/protocolos modernos:

- **A2A (Agent-to-Agent)** — comunicação entre agentes via `AgentCard` e `skills`.
- **MCP (Model Context Protocol)** — exposição de recursos, prompts e *tools* de dados (via `fastmcp`).
- **AG-UI** — protocolo de eventos em *streaming* (SSE) entre backend e frontend React.

---

## Arquitetura

```
                         ┌──────────────────────────┐
                         │  frontend2 (React/AG-UI)  │  :3000
                         │  frontend  (Streamlit)    │  :9090
                         └─────────────┬────────────┘
                                       │ HTTP / SSE
                                       ▼
                         ┌──────────────────────────┐
                         │  supervisor (FastAPI)     │  :8080→8000
                         │  Roteador LangGraph +     │
                         │  classificador (LLM)      │
                         └───────┬──────────┬────────┘
                                 │ A2A      │ A2A
                  ┌──────────────▼──┐   ┌───▼───────────────┐
                  │ abrir_conta     │   │ cartao_credito    │
                  │ agent  :8081    │   │ agent   :8082     │
                  └────────┬────────┘   └────────┬──────────┘
                           │ MCP (tools)         │ MCP (tools)
                           └──────────┬──────────┘
                                      ▼
                          ┌──────────────────────┐
                          │  recursos (FastMCP)   │  :8084
                          │  contas / cartões     │
                          │  db.json (persistência)│
                          └──────────────────────┘

   bfa (Backend for Agents) :8083 — descoberta + busca BM25 de agentes/tools
```

**Fluxo típico:** o usuário envia uma mensagem no frontend → o `supervisor` classifica a intenção com um LLM e roteia para um ou mais agentes via A2A → cada agente usa *tools* MCP do serviço `recursos` para consultar/criar contas e cartões → as respostas são agregadas e devolvidas em *streaming*.

---

## Serviços (portas)

| Serviço | Porta (host→container) | Tecnologia | Descrição |
|---|---|---|---|
| `supervisor` | `8080→8000` | FastAPI + LangGraph | Orquestra/roteia os agentes |
| `frontend` | `9090` | Streamlit | UI simples de chat (legado) |
| `frontend-ag-ui` | `3000` | React + AG-UI | UI moderna com *streaming* e painel de estado |
| `abrir_conta_agent` | `8081→8000` | A2A + LangChain | Agente de abertura de conta |
| `cartao_credito_agent` | `8082→8000` | A2A + LangChain | Agente de cartões de crédito |
| `recursos` | `8084→8000` | FastMCP | Servidor MCP de dados (contas/cartões) |
| `bfa` | `8083→8000` | FastAPI | Descoberta e busca (BM25) de agentes e tools |

---

## Como executar

Pré-requisitos: **Docker** e **Docker Compose**.

1. Defina a variável de ambiente `OPENAI_API_KEY` (usada pelos agentes e pelo supervisor). Os serviços carregam variáveis via `python-dotenv`, então um arquivo `.env` em cada serviço Python também funciona.
2. Suba toda a stack:

```bash
docker compose up --build
```

3. Acesse as interfaces:
   - Frontend moderno (React/AG-UI): http://localhost:3000
   - Frontend simples (Streamlit): http://localhost:9090

> **Nota:** É necessário configurar `OPENAI_API_KEY` para os agentes que usam modelos OpenAI (`gpt-4.1-nano`). Sem a chave, a classificação e as respostas dos agentes falharão.

---

## Estrutura de pastas e arquivos

### Raiz

| Arquivo | Descrição |
|---|---|
| `docker-compose.yml` | Orquestração de todos os serviços (build, portas, volumes, dependências). |
| `README.md` | Este documento. |

---

### `supervisor/` — Orquestrador de agentes (FastAPI + LangGraph)

Recebe a mensagem do usuário, classifica a intenção com um LLM e roteia para os agentes corretos via A2A, agregando as respostas (com suporte a *streaming* AG-UI).

| Arquivo | Descrição |
|---|---|
| `app.py` | App FastAPI. Expõe `POST /chat` (resposta simples) e `POST /` (eventos AG-UI em *streaming* SSE). Configura CORS. |
| `src/agents.py` | Define o **roteador**: inicializa o LLM (`gpt-4.1-nano`), o *system prompt* com as regras de negócio do MDBank e a função `classifique_intencao_do_usuario`, que decide quais agentes (`abrir_conta`, `cartao_credito`) devem responder. |
| `src/services.py` | Constrói o grafo **LangGraph** (nós de roteamento e dos agentes), implementa a chamada A2A `request_agent`, e os executores `executar_supervisor` (normal) e `executar_supervisor_stream` (eventos AG-UI + *state*). |
| `src/schemas.py` | Modelo Pydantic `ChatRequest` (`message`, `session_id`, `client_id`). |
| `requirements.txt` | Dependências: FastAPI, a2a-sdk, ag-ui-protocol, langgraph, langchain, etc. |
| `Dockerfile` | Imagem Python 3.13; roda `uvicorn app:app` com `--reload`. |
| `.dockerignore` / `.gitignore` | Exclusões de build/versionamento. |

---

### `agents/` — Agentes A2A especializados

Cada agente é um serviço A2A independente que expõe um `AgentCard` com suas `skills` e usa *tools* MCP do serviço `recursos`.

#### `agents/abrir_conta/`

| Arquivo | Descrição |
|---|---|
| `server.py` | Define a `AgentSkill` (`abrir_conta`) e o `AgentCard`, monta o `A2AStarletteApplication` e expõe `app` para o uvicorn. |
| `executor.py` | `AbrirContaExecutor`: recebe a mensagem do usuário (contexto A2A) e chama o agente LangChain, enfileirando a resposta no `EventQueue`. |
| `agent/abrir_conta.py` | Lógica do agente LangChain (`gpt-4.1-nano`) conectado às *tools* MCP em `recursos`. Define o *system prompt* com o fluxo obrigatório de abertura de conta. |
| `requirements.txt` | Dependências: a2a-sdk, langchain, langchain-mcp-adapters, etc. |
| `Dockerfile` | Imagem Python 3.13; roda `uvicorn server:app`. |
| `.dockerignore` / `.gitignore` | Exclusões de build/versionamento. |

#### `agents/cartao_credito/`

| Arquivo | Descrição |
|---|---|
| `server.py` | Define a `AgentSkill` (`cartao_credito`, tipos *platinum/gold/silver/mdzao*) e o `AgentCard`, monta o app A2A. |
| `executor.py` | `CartaoDeCreditoExecutor`: ponte entre o contexto A2A e o agente LangChain. |
| `agent/cartoes.py` | Agente LangChain (`gpt-4.1-nano`) com *tools* MCP. *System prompt* exige consultar a conta antes de emitir cartão. |
| `requirements.txt` | Dependências do agente. |
| `Dockerfile` | Imagem Python 3.13; roda `uvicorn server:app`. |
| `.dockerignore` / `.gitignore` | Exclusões de build/versionamento. |

---

### `recursos/` — Servidor MCP de dados (FastMCP)

Fonte de dados central do banco. Expõe *resources*, *prompts* e *tools* via MCP, além de uma rota REST auxiliar `/tools`.

| Arquivo | Descrição |
|---|---|
| `app.py` | Servidor `FastMCP("ContaService")`. Define: *resources* (`conta://{cpf}`, `cartao://{cpf}`), *prompts* (`abrir_conta_prompt`, `solicitar_cartao_prompt`), *tools* (`consultar_conta`, `consultar_cartao`, `criar_ou_buscar_conta`, `solicitar_cartao`, `gerar_prompt_abertura`) e a rota `GET /tools`. Persiste em `db.json`. |
| `db.json` | Banco de dados em arquivo JSON (contas e cartões por CPF). |
| `requirements.txt` | Dependências: fastmcp, httpx, langchain, etc. |
| `Dockerfile` | Imagem Python 3.13; roda `fastmcp run app.py:mcp` em HTTP no path `/mcp_gateway`. |
| `.dockerignore` / `.gitignore` | Exclusões de build/versionamento. |

---

### `bfa/` — Backend for Agents (descoberta + busca)

Serviço de **descoberta e busca** de agentes (A2A) e de *tools* (MCP), com ranqueamento por relevância usando **BM25**. Útil para "resolver" qual agente/tool atende melhor uma consulta.

| Arquivo | Descrição |
|---|---|
| `app.py` | App FastAPI. No *startup* descobre agentes e tools e constrói o índice. Endpoints: `/skills`, `/skills/agents`, `/skills/tools`, `/resolve`, `/resolve/agents`, `/resolve/tools` e `/` (health). |
| `discovery.py` | `discover_agents`: usa `A2ACardResolver` para ler os `AgentCard` dos agentes e registrar suas *skills*. |
| `mcp_discovery.py` | `discover_tools`: consulta o endpoint `/tools` do serviço `recursos` e registra as *tools* MCP. |
| `registry.py` | Registro unificado e busca **BM25** (`build_index`, `search_bm25`, `resolve_agent`) com normalização de texto e *boost* para *tools*. |
| `requirements.txt` | Dependências: rank-bm25, numpy, httpx, a2a-sdk, etc. |
| `Dockerfile` | Imagem do serviço. |
| `.dockerignore` / `.gitignore` | Exclusões de build/versionamento. |
| `__pycache__/` | Cache de bytecode Python (gerado automaticamente). |

---

### `frontend/` — UI simples (Streamlit)

Interface de chat mínima (legado) que consome `POST /chat` do supervisor.

| Arquivo | Descrição |
|---|---|
| `app.py` | App Streamlit de chat; envia mensagens para `http://supervisor:8000/chat`. |
| `requirements.txt` | Dependências: streamlit, requests. |
| `Dockerfile` | Imagem Python; roda `streamlit run app.py` na porta 9090. |

---

### `frontend2/` — UI moderna (React + AG-UI)

Interface React com Tailwind, *streaming* de eventos (AG-UI/SSE), painel de *state* compartilhado e visualização de cartões.

| Caminho | Descrição |
|---|---|
| `package.json` | Dependências (React 18, react-router-dom, @ag-ui/client, tailwindcss, framer-motion, react-markdown, lucide-react) e *scripts*. |
| `tailwind.config.js` | Configuração do Tailwind CSS. |
| `Dockerfile` | Imagem Node 20; roda `npm start` na porta 3000 (com *hot reload*). |
| `public/index.html` | HTML base da aplicação React. |
| `src/index.jsx` | Ponto de entrada React (renderiza `App`). |
| `src/index.css` | Estilos globais / Tailwind. |
| `src/App.jsx` | Define as rotas: `/` (Chat) e `/state-util` (histórico). Envolve tudo no `StateProvider`. |
| `src/StateContext.js` | Context API com o *state* compartilhado, mensagens e *flags* de UI. |
| `src/Layout.jsx` | Layout com cabeçalho, navegação e painel lateral do *state* (JSON). |
| `src/ChatPage.jsx` | Página de chat: envia o *payload* AG-UI para o supervisor e processa o *stream* SSE (`TEXT_MESSAGE_CONTENT`, `STATE_UPDATE`, `RUN_FINISHED`). |
| `src/StateUtilPage.jsx` | Página "Conversa": extrai dados das respostas (nome, CPF, conta, cartão) e renderiza cartões visuais animados. |
| `src/services/agentAdapter.js` | `MDBankAgent`: *wrapper* HTTP/`HttpAgent` para chamar um agente. |
| `src/components/ChatBox.jsx` | Caixa de chat (mensagens, *markdown*, copiar/editar, input). |
| `src/components/PromptSuggestions.jsx` | Sugestões de prompts iniciais. |
| `src/components/AgentSelector.jsx` | Seletor de agente (conta/cartão/supervisor). |
| `src/components/EventStream.jsx` | Lista de eventos recebidos. |
| `src/components/StatusPanel.jsx` | Painel de alertas/status. |
| `.dockerignore` / `.gitignore` | Exclusões de build/versionamento. |

---

## Modelos de IA utilizados

| Componente | Modelo |
|---|---|
| `supervisor` (roteador) | `gpt-4.1-nano` |
| `abrir_conta` agent | `gpt-4.1-nano` |
| `cartao_credito` agent | `gpt-4.1-nano` |

---

## Protocolos e bibliotecas-chave

- **A2A** (`a2a-sdk`) — `AgentCard`, `AgentSkill`, `A2ACardResolver`, `ClientFactory`.
- **MCP / FastMCP** (`fastmcp`, `langchain-mcp-adapters`) — *resources*, *prompts*, *tools*.
- **AG-UI** (`ag-ui-protocol`, `@ag-ui/client`) — eventos em *streaming* (SSE).
- **LangChain / LangGraph** — agentes, grafo de roteamento e memória em sessão.
- **BM25** (`rank-bm25`) — ranqueamento textual no serviço `bfa`.
