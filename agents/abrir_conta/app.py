from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from pydantic import BaseModel
import os

load_dotenv()

_llm = init_chat_model(
    model="gpt-4.1-nano",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.7
)

app = FastAPI()

agente_abertura_conta = create_agent(
    _llm,
    tools=[],
    system_prompt=(
        "Você é um especialista em abertura de contas do banco MDBank. "
        "Ajude o cliente a abrir uma conta e explique os tipos disponíveis."
    ),
)

class AbrirContaRequest(BaseModel):
    message: str


@app.post("/send")
async def consultar(request: AbrirContaRequest):
    mensagem = request.message

    if not mensagem:
        raise HTTPException(
            status_code=400,
            detail="Campo 'message' obrigatório"
        )

    try:
        resultado = agente_abertura_conta.invoke(
            {"messages": [HumanMessage(content=mensagem)]}
        )

        mensagem_ia = resultado["messages"][-1]

        return {"resposta": mensagem_ia.content}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )