import logging
from typing import TypedDict, Annotated, Sequence, Optional
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

logger = logging.getLogger(__name__)

# Heptatomo System Prompt injected into the Agent
HEPTATOMO_SYSTEM_PROMPT = """Você é um analista especializado na Teoria Heptatomo do ContentOS.
Sua única função é analisar o texto fornecido e avaliar seu balanceamento nas 7 Dimensões:
1. LOGOS (Lógica/Razão): Dados, fatos, argumentos lógicos, pesquisa.
2. TECHNE (Técnica/Prática): Tutoriais, step-by-step, ferramentas, metodologias.
3. ETHOS (Ética/Autoridade): Credibilidade, moralidade, princípios, confiança.
4. BIOS (Vida/Storytelling): Narrativas pessoais, histórias de vida, jornada do herói.
5. STRATEGOS (Estratégia/Visão): Planejamento, visão de longo prazo, posicionamento competitivo.
6. POLIS (Comunidade/Tribo): Pertencimento, networking, cultura de grupo, causas compartilhadas.
7. PATHOS (Emoção/Paixão): Inspiração, dor, desejo, humor, conexões emocionais intensas.

Para o texto fornecido pelo usuário, gere uma crítica estruturada:
- Quais dimensões estão mais fortes (Dominantes)?
- Quais dimensões estão fracas ou ausentes (Gaps)?
- Sugestão prática de como injetar as dimensões ausentes para tornar o conteúdo mais persuasivo.

Seja direto, técnico e use o jargão do Heptatomo. Formate sua resposta em Markdown.
"""

# 1. Define the State
class ContentOSState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    document_id: Optional[str]

# 2. Define the Nodes
def analyze_dimensions(state: ContentOSState):
    """
    Node that processes the text through the Heptatomo lens.
    """
    logger.info("Agent Node: Analyzing Dimensions via Heptatomo Lens")
    
    # We rely on the dual-initialized ADC credentials from the authenticator logic.
    # The Langchain Google GenAI wrapper will pick up the ADC standard env vars.
    # But just to be sure we are using the standard config:
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.3,
        max_output_tokens=1024
    )
    
    # Prepend the system prompt if it's the first execution
    messages = state["messages"]
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=HEPTATOMO_SYSTEM_PROMPT)] + list(messages)
    
    # Invoke the LLM
    response = llm.invoke(messages)
    
    # State update
    return {"messages": [response]}

# 3. Build the Graph
workflow = StateGraph(ContentOSState)

# Add nodes
workflow.add_node("analyzer", analyze_dimensions)

# Add edges
workflow.add_edge(START, "analyzer")
workflow.add_edge("analyzer", END)

# Compile the graph
contentos_agent = workflow.compile()
