import streamlit as st
from supabase import create_client, Client
import uuid # Para gerar nomes únicos para as fotos

# ==========================================
# CONFIGURAÇÕES E CONEXÃO SUPABASE
# ==========================================
st.set_page_config(page_title="Tático Intel", page_icon="🛡️", layout="centered")

# Mantém o sistema de barreira de senha
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["SENHA_ACESSO"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    if st.session_state.get("password_correct", False):
        return True
    st.markdown("### 🔒 Acesso Restrito - FT20")
    st.text_input("Insira a Senha de Acesso:", type="password", on_change=password_entered, key="password")
    if "password_correct" in st.session_state:
        st.error("❌ Senha incorreta. Acesso negado.")
    return False

if not check_password():
    st.stop()

# Conecta ao Supabase usando as chaves do Cofre (Secrets)
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# ==========================================
# INTERFACE PRINCIPAL
# ==========================================
st.title("🛡️ FT20")

# Criação de duas abas operacionais
aba_alvo, aba_local = st.tabs(["👤 Cadastrar Indivíduo", "🏠 Cadastrar Local/Fato"])

# ----------------- ABA 1: PESSOAS -----------------
with aba_alvo:
    st.subheader("Qualificação de Alvo")
    with st.form("form_alvo", clear_on_submit=True):
        nome = st.text_input("Nome Completo *")
        vulgo = st.text_input("Vulgo")
        cpf = st.text_input("CPF")
        faccao = st.selectbox("Facção/Grupo", ["Nenhuma", "CV", "PCC", "Outra"])
        endereco = st.text_input("Endereço Principal")
        obs = st.text_area("Observações / Passagens / Tatuagens")
        foto_alvo = st.file_uploader("Fotografia do Alvo", type=["png", "jpg", "jpeg"])
        
        submit_alvo = st.form_submit_button("Gravar Alvo na Base")

        if submit_alvo:
            if not nome:
                st.error("O campo Nome é obrigatório!")
            else:
                url_foto = ""
                # Lógica de Upload da Foto se existir
                if foto_alvo:
                    ext = foto_alvo.name.split('.')[-1]
                    nome_arquivo = f"alvos_{uuid.uuid4()}.{ext}" # Gera um nome único
                    # Faz o upload para o bucket 'fotos_alvos'
                    supabase.storage.from_('fotos_alvos').upload(nome_arquivo, foto_alvo.getvalue(), {"content-type": foto_alvo.type})
                    # Pega o link público da imagem
                    url_foto = supabase.storage.from_('fotos_alvos').get_public_url(nome_arquivo)

                # Estrutura os dados para o banco
                dados = {
                    "nome": nome, "vulgo": vulgo, "cpf": cpf,
                    "faccao_grupo": faccao, "endereco": endereco,
                    "observacoes": obs, "caminho_foto": url_foto
                }
                # Insere na tabela
                supabase.table("dim_pessoas").insert(dados).execute()
                st.success(f"✅ Alvo '{nome}' registado com sucesso!")

# ----------------- ABA 2: LOCAIS / FATOS -----------------
with aba_local:
    st.subheader("Registo de Local ou Denúncia")
    with st.form("form_local", clear_on_submit=True):
        tipo_evento = st.selectbox("Tipo de Registo *", ["Denúncia Biqueira", "Local de Reunião", "Apreensão", "Outro"])
        bairro = st.text_input("Bairro / Rua / Referência *")
        resumo = st.text_area("Resumo da Denúncia / Observações")
        foto_local = st.file_uploader("Fotografia do Local (Fachada/Muro)", type=["png", "jpg", "jpeg"])
        
        submit_local = st.form_submit_button("Gravar Fato na Base")

        if submit_local:
            if not bairro:
                st.error("O campo Bairro/Referência é obrigatório!")
            else:
                url_foto_local = ""
                if foto_local:
                    ext = foto_local.name.split('.')[-1]
                    nome_arquivo = f"locais_{uuid.uuid4()}.{ext}"
                    supabase.storage.from_('fotos_alvos').upload(nome_arquivo, foto_local.getvalue(), {"content-type": foto_local.type})
                    url_foto_local = supabase.storage.from_('fotos_alvos').get_public_url(nome_arquivo)

                dados_fato = {
                    "tipo_evento": tipo_evento,
                    "bairro_setor": bairro,
                    "resumo_obs": resumo,
                    "caminho_foto": url_foto_local
                }
                supabase.table("fato_eventos").insert(dados_fato).execute()
                st.success("✅ Denúncia / Local registado com sucesso!")
