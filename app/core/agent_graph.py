import logging
from typing import TypedDict, Annotated, Sequence, Optional
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from core.agent_tools import search_knowledge_tool, save_document_tool

logger = logging.getLogger(__name__)

# Heptatomo System Prompt injected into the Agent
HEPTATOMO_SYSTEM_PROMPT = """Você é o Agente Polímata do ContentOS, mestre na Teoria Heptatomo.
As 7 Dimensões do Conhecimento são:
1. LOGOS (Fatos/Lógica)
2. TECHNE (Prática/Tutoriais)
3. ETHOS (Autoridade/Ética)
4. BIOS (Storytelling/Vida)
5. STRATEGOS (Estratégia/Visão)
6. POLIS (Comunidade/Tribo)
7. PATHOS (Emoção/Dor)

Você tem ferramentas ('tools') para ajudar o usuário a balancear seus textos.
Sempre que o usuário pedir para reescrever, analisar ou aplicar dimensões:
1. Se precisar de fatos adicionais, use a ferramenta 'search_knowledge_tool' para buscar na memória do Vault.
2. Identifique qual dimensão está faltando ou como o texto deve ser modificado com base no pedido do usuário.
3. Você mesmo deve REESCREVER e melhorar o texto para injetar as dimensões solicitadas.
4. Após gerar o texto final, OBJETIVAMENTE chame a ferramenta 'save_document_tool' enviando TODO O NOVO TEXTO no parâmetro 'updated_content'.
5. Não responda com o texto longo no chat, apenas informe que salvou com sucesso.
"""

# 1. Define the State
class ContentOSState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    document_id: Optional[str]
    instruction: Optional[str] # What the user wants the agent to do

# 2. Define the Nodes
def agent_reasoner(state: ContentOSState):
    """
    Node that processes the text and decides to use tools or respond.
    """
    logger.info("Agent Node: Reasoning")
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.3,
        max_output_tokens=2048
    )
    
    # Bind our hands (tools)
    tools = [search_knowledge_tool, save_document_tool]
    llm_with_tools = llm.bind_tools(tools)
    
    # Prepend the system prompt if it's the first execution
    messages = state["messages"]
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=HEPTATOMO_SYSTEM_PROMPT)] + list(messages)
    
    # Invoke the LLM
    response = llm_with_tools.invoke(messages)
    
    # State update
    return {"messages": [response]}

# Build the prebuilt ToolNode
tools = [search_knowledge_tool, save_document_tool]
tool_node = ToolNode(tools)

# 3. Build the Graph
workflow = StateGraph(ContentOSState)

# Add nodes
workflow.add_node("agent", agent_reasoner)
workflow.add_node("tools", tool_node)

# Add edges (The ReAct Loop)
workflow.add_edge(START, "agent")
# Conditional routing: If agent returned tool_calls, go to tools. Else go to END.
workflow.add_conditional_edges("agent", tools_condition)
workflow.add_edge("tools", "agent")

# Compile the graph
contentos_agent = workflow.compile()
