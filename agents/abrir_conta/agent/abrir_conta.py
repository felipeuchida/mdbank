from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import InMemorySaver
import os

load_dotenv()

_llm = init_chat_model(
    model="gpt-4.1-nano",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.3,
)

SMITHERY_URL = 'https://server.smithery.ai/nickclyde/duckduckgo-mcp-server/mcp'
SMITHERY_API_KEY = os.getenv("SMITHERY_API_KEY")

client = MultiServerMCPClient(
    {
        "conta": {
            "transport": "http",
            "url": "http://recursos:8000/mcp_gateway",
        },

        'smithery': {
            "transport": "http",
            'url': f"{SMITHERY_URL}?api_key={SMITHERY_API_KEY}",
        },
    }
)

memory = InMemorySaver()

async def build_agent():
    tools = await client.get_tools()

    agent = create_agent(
        _llm,
        tools=tools,
        system_prompt=(
            "Você é um assistente do MDBank para abertura de contas.\n\n"

            "Você deve SEMPRE usar tools para decisões reais.\n\n"

            "Fluxo obrigatório:\n"
            "1. Se cliente pedir cartão:\n"
            "   - Use consultar_conta\n"
            "   - Se não existir:\n"
            "       → informe o problema\n"
            "       → ofereça abrir conta\n\n"

            "2. Para abrir conta:\n"
            "   - Use gerar_prompt_abertura\n"
            "   - Depois criar_ou_buscar_conta\n\n"

            "3. Após conta criada:\n"
            "   - Use solicitar_cartao\n\n"

            "Regras:\n"
            "- Nunca invente dados\n"
            "- Sempre use tools\n"
            "- Use mensagens claras para o cliente\n"
            "- Para buscas externas use a tool search do smithery, sempre que alguem falar quero buscar\n"
        ),
        checkpointer=memory,
    )

    return agent

async def run_agent(mensagem: str, thread_id: str = "1"):
    agent = await build_agent()

    resultado = await agent.ainvoke(
        {"messages": [HumanMessage(content=mensagem)]},
        {"configurable": {"thread_id": thread_id}}
    )

    return resultado["messages"][-1].content