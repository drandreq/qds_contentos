import streamlit as st
import os
import json
import requests

st.set_page_config(page_title="Content Studio", page_icon="🎬", layout="wide")

st.title("🎬 Content Studio")
st.markdown("Visualizador de Timeline, Preview de Slides e Compilador Atômico.")

VAULT_DIR = "/vault"

@st.cache_data(ttl=5)
def get_vault_files():
    """Fetches all JSON files from the vault."""
    files = []
    if not os.path.exists(VAULT_DIR):
        return []

    for root, _, filenames in os.walk(VAULT_DIR):
        for filename in filenames:
            if filename.endswith(".json"):
                # Store paths relative to vault base for cleaner UI and API parsing
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, VAULT_DIR)
                files.append(rel_path)
    return files

files = get_vault_files()

col1, col2 = st.columns([1, 2])

with col1:
    st.header("1. Selecione o Documento")
    if not files:
        st.info("Nenhum arquivo JSON encontrado no Vault.")
        selected_file = None
    else:
        selected_file = st.selectbox("Documentos no Vault", files)
        
    st.markdown("---")
    st.header("Compilar Vault")
    st.write("Força o MP-Dialect parser a varrer os arquivos `.md` e gerar os metadados `.json` na timeline.")
    
    if st.button("Trigger Atomic Compile", type="primary"):
        with st.spinner("Conectando ao backend-engine e compilando..."):
            try:
                resp = requests.post("http://backend-engine:8000/v1/compile", timeout=30)
                if resp.status_code == 200:
                    st.success("Compilação Atômica concluída com sucesso.")
                    st.json(resp.json())
                    st.cache_data.clear()
                else:
                    st.error(f"Erro na compilação: {resp.status_code} - {resp.text}")
            except Exception as e:
                st.error(f"Falha de conexão com backend: {e}")

with col2:
    if selected_file:
        full_path = os.path.join(VAULT_DIR, selected_file)
        st.header(f"2. Visualização: `{selected_file}`")
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            st.subheader("⏱️ Metadados Atômicos")
            col_a, col_b = st.columns(2)
            col_a.metric("Tipo", str(data.get("type", "Desconhecido")).title())
            col_b.metric("Tempo Estimado", f"{data.get('estimated_time_seconds', 0)}s")
            
            st.markdown("---")
            
            # Show Slides
            slides = data.get("slides", [])
            if slides:
                st.subheader("🖼️ Preview de Slides (CSS Renderizado)")
                for i, slide in enumerate(slides):
                    layout = slide.get("layout", "default")
                    content = slide.get("content", "")
                    
                    st.markdown(f"**Slide {i+1}** (Layout: `{layout}`)")
                    # Simple structural layout using markdown
                    st.info(content)
                    
            # Show Timeline (if any)
            timeline = data.get("timeline", [])
            if timeline:
                st.markdown("---")
                st.subheader("📜 Timeline Rítmica (MP-Dialect)")
                for idx, node in enumerate(timeline):
                    node_type = node.get("type", "text")
                    node_content = node.get("content", "")
                    
                    if node_type == "text":
                        st.write(node_content)
                    elif node_type == "pause":
                        st.warning(f"⏸️ Pausa Rítmica ({node.get('duration_seconds', 2)}s)")
                    elif node_type == "slide":
                        st.success(f"🖼️ Slide: {node_content}")

            # Fallback for raw text if no timeline/slides
            if not timeline and not slides and "raw_text" in data:
                st.markdown("---")
                st.subheader("📝 Texto Bruto")
                st.write(data["raw_text"])
                
        except Exception as e:
            st.error(f"Erro ao ler arquivo JSON: {e}")
