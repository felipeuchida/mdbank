from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
import os

load_dotenv()

_llm = init_chat_model(
    model="gpt-4.1-nano",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.7
)

agente_cartao_credito = create_agent(
    _llm,
    tools=[],
    system_prompt=(
        "Você é um especialista em cartão de crédito do banco MDBank. "
        "Os cartões que existem no MDBank são: [platinum, gold, silver, mdzao] "
        "Quando o cliente solicitar um cartao o tipo platinum, ele tem os seguintes benefícios: [Hotel, Restaurante, pontos de cashback]. "
        "Quando o cliente informar que gostaria do platinum, você deve informar que tem uma anuidade de 500 reais. "
        "Ajude o cliente com dúvidas, solicitação e limites."
    )
)

async def run_agent(mensagem: str):
    resultado = agente_cartao_credito.invoke(
        {"messages": [HumanMessage(content=mensagem)]}
    )

    return resultado["messages"][-1].content