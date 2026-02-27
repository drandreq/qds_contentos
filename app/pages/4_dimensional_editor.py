import streamlit as st
import os
import json
import requests
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Editor Dimensional", page_icon="🕸️", layout="wide")

st.title("🕸️ Editor Dimensional (7D)")
st.markdown("Visualize o equilíbrio do seu conteúdo através da Lente Heptatomo.")

VAULT_DIR = "/vault"

@st.cache_data(ttl=5)
def get_vault_files():
    """Fetches all JSON files from the vault."""
    files = []
    for root, dirs, filenames in os.walk(VAULT_DIR):
        # Prevent traversal into .history or other hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for filename in filenames:
            if filename.endswith(".json"):
                # Store paths relative to vault base for cleaner UI and API parsing
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, VAULT_DIR)
                files.append(rel_path)
    return files

def draw_radar_chart(tensor: dict):
    """Draws a beautiful 7D Plotly Radar Chart."""
    categories = ['LOGOS', 'TECHNE', 'ETHOS', 'BIOS', 'STRATEGOS', 'POLIS', 'PATHOS']
    
    # Extract values. Default to 0 if missing.
    values = [
        tensor.get("logos", 0.0),
        tensor.get("techne", 0.0),
        tensor.get("ethos", 0.0),
        tensor.get("bios", 0.0),
        tensor.get("strategos", 0.0),
        tensor.get("polis", 0.0),
        tensor.get("pathos", 0.0)
    ]
    
    # Close the polygon by appending the first value to the end
    categories.append(categories[0])
    values.append(values[0])

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name='Atonia Dimensional',
        line=dict(color='#00F0FF', width=2),
        fillcolor='rgba(0, 240, 255, 0.3)'
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1.0],
                gridcolor="rgba(255, 255, 255, 0.2)",
                linecolor="rgba(255, 255, 255, 0.2)"
            ),
            angularaxis=dict(
                gridcolor="rgba(255, 255, 255, 0.2)",
                linecolor="rgba(255, 255, 255, 0.2)",
            ),
            bgcolor="rgba(0,0,0,0)"
        ),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=40, t=20, b=20)
    )
    
    return fig

# --- UI Layout ---

files = get_vault_files()

if not files:
    st.info("O Vault está vazio. Adicione conteúdo (ex: Áudios no Telegram) para começar.")
    st.stop()

selected_file = st.selectbox("Selecione o Documento do Vault:", files)

if selected_file:
    # Load the JSON
    full_path = os.path.join(VAULT_DIR, selected_file)
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo: {e}")
        st.stop()
        
    # Extract Tensor and Text
    tensor = data.get("dimensional_tensor", {})
    
    raw_text = ""
    if data.get("type", "") == "transcription":
        raw_text = data.get("raw_text", "")
    elif data.get("type", "") == "lesson":
        raw_text = data.get("raw_markdown", "")
        
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Radar de Balanceamento")
        if tensor:
            fig = draw_radar_chart(tensor)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum Tensor Dimensional encontrado neste arquivo.")
            
    with col2:
        st.subheader("Conteúdo Fonte")
        # Text Editor
        edited_text = st.text_area("Markdown Bruto", value=raw_text, height=350)
        
        # Linter Integration (Sprint 13)
        st.markdown("---")
        st.subheader("🤖 Linter de Tom (Agente Heptatomo)")
        
        linter_instruction = st.text_input(
            "Comando para o Agente:", 
            value="Analise a arrogância ou a falta de empatia neste texto. Como o PATHOS pode quebrar uma percepção de prepotência (ETHOS excessivo)?"
        )
        
        if st.button("Executar Agent Linter", type="primary"):
            with st.spinner("Conectando ao Connectome Agentic..."):
                try:
                    payload = {
                        "filepath": selected_file,
                        "instruction": linter_instruction
                    }
                    response = requests.post("http://backend-engine:8000/v1/agent/analyze", json=payload, timeout=90)
                    
                    if response.status_code == 200:
                        st.session_state.linter_result = response.json().get("heptatomo_critique", "Nenhuma crítica retornada.")
                    else:
                        st.error(f"Erro do Backend: {response.text}")
                except Exception as e:
                    st.error(f"Falha na conexão: {e}")
                    
        if "linter_result" in st.session_state:
            st.success("Análise Concluída:")
            st.markdown(st.session_state.linter_result)
