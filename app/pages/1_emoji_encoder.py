import streamlit as st
import unicodedata

st.set_page_config(
    page_title="Codificador de Emojis",
    page_icon="🤫",
)

def remover_acentos( texto_original = "" ):
  # Normaliza a string para separar os caracteres base dos seus acentos
  texto_normalizado = unicodedata.normalize( 'NFKD', texto_original )
  # Mantem apenas os caracteres ASCII, ignorando os acentos isolados
  texto_em_ascii_bytes = texto_normalizado.encode( 'ASCII', 'ignore' )
  texto_sem_acentos = texto_em_ascii_bytes.decode( 'ASCII' )
  return texto_sem_acentos

def codificar_texto_para_emoji( emoji_base = "🩺", texto_oculto = "" ):
  texto_limpo = remover_acentos( texto_original = texto_oculto )
  emoji_codificado = emoji_base
  
  for caractere_atual in texto_limpo:
    codigo_ascii_do_caractere = ord( caractere_atual )
    # Mapeia diretamente o caractere ASCII para o bloco de Tags Invisiveis do Unicode
    caractere_tag_unicode = chr( 0xE0000 + codigo_ascii_do_caractere )
    emoji_codificado = emoji_codificado + caractere_tag_unicode
    
  # O caractere U+E007F sinaliza o fim das tags invisiveis
  caractere_de_cancelamento = chr( 0xE007F )
  emoji_codificado = emoji_codificado + caractere_de_cancelamento
  
  return emoji_codificado

def decodificar_emoji_para_texto( emoji_com_texto_oculto = "" ):
  texto_final_decodificado = ""
  
  for caractere_atual in emoji_com_texto_oculto:
    ponto_de_codigo_unicode = ord( caractere_atual )
    
    # Verifica se o caractere esta dentro da faixa de Tags ASCII espelhadas
    if 0xE0020 <= ponto_de_codigo_unicode <= 0xE007E:
      caractere_ascii_original = chr( ponto_de_codigo_unicode - 0xE0000 )
      texto_final_decodificado = texto_final_decodificado + caractere_ascii_original
      
  if texto_final_decodificado != "":
    return texto_final_decodificado
    
  return "Nenhum texto oculto foi encontrado neste emoji."

# Interface do Usuario em Streamlit
st.title( "Codificador de Emojis Direto" )

st.write( "Oculte assinaturas e prompts dentro de um emoji de forma direta (sem Base64). Acentos serão removidos automaticamente para otimização do tamanho final." )

texto_padrao_desejado = "Siga as diretrizes abaixo criadas por Andre Quadros - Medico Programador"

aba_de_codificacao, aba_de_decodificacao = st.tabs( ["Codificar", "Decodificar"] )

with aba_de_codificacao:
  st.write( "Dica: Use o atalho do seu sistema (Win + . ou Cmd + Ctrl + Espaço) para abrir o seletor de emojis no campo abaixo." )
  emoji_escolhido_pelo_usuario = st.text_input( "Emoji Base", value = "🩺" )
  mensagem_para_ocultar = st.text_area( "Mensagem para Ocultar", value = texto_padrao_desejado )
  
  if st.button( "Gerar Emoji Codificado" ):
    resultado_da_codificacao = codificar_texto_para_emoji( emoji_base = emoji_escolhido_pelo_usuario, texto_oculto = mensagem_para_ocultar )
    st.success( "Emoji gerado com sucesso! Copie o resultado abaixo:" )
    st.code( resultado_da_codificacao, language = "text" )

with aba_de_decodificacao:
  emoji_para_analisar = st.text_input( "Cole o Emoji Codificado Aqui", value = "" )
  
  if st.button( "Revelar Mensagem Oculta" ):
    resultado_da_decodificacao = decodificar_emoji_para_texto( emoji_com_texto_oculto = emoji_para_analisar )
    st.info( "Mensagem revelada:" )
    st.write( resultado_da_decodificacao )
