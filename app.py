import streamlit as st
from supabase import create_client, Client
import uuid

# ==========================================
# CONFIGURAÇÕES DA PÁGINA
# ==========================================
st.set_page_config(page_title="FT-20 | Informações de Serviço", page_icon="🛡️", layout="centered")

# ==========================================
# BARREIRA DE SEGURANÇA
# ==========================================
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["SENHA_ACESSO"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    
    if st.session_state.get("password_correct", False):
        return True
        
    st.markdown("### 🔒 Acesso Restrito - FT-20")
    st.text_input("Insira a Senha de Acesso:", type="password", on_change=password_entered, key="password")
    if "password_correct" in st.session_state:
        st.error("❌ Senha incorreta. Acesso negado.")
    return False

if not check_password():
    st.stop()

# ==========================================
# CONEXÃO SUPABASE E FUNÇÕES AUXILIARES
# ==========================================
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

def extrair_coordenadas(texto_coords):
    lat, lon = "", ""
    if texto_coords:
        if "," in texto_coords:
            partes = texto_coords.split(",")
            lat = partes[0].strip()
            lon = partes[1].strip()
        else:
            lat = texto_coords.strip()
    return lat, lon

# ==========================================
# CABEÇALHO
# ==========================================
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    try:
        st.image("logo.jpg", use_container_width=True)
    except:
        st.warning("A carregar brasão...")

st.markdown("<h2 style='text-align: center;'>Sistema de Informações de Serviço</h2>", unsafe_allow_html=True)
st.divider()

# ==========================================
# INTERFACE PRINCIPAL (ABAS)
# ==========================================
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
        
        coordenadas_alvo = st.text_input("Coordenadas (Cole do Google Maps, ex: -15.8932, -52.2599)")
        obs = st.text_area("Observações / Passagens / Tatuagens")
        foto_alvo = st.file_uploader("Fotografia do Alvo", type=["png", "jpg", "jpeg"])
        
        submit_alvo = st.form_submit_button("Gravar Alvo na Base")

        if submit_alvo:
            if not nome:
                st.error("O campo Nome é obrigatório!")
            else:
                url_foto = ""
                if foto_alvo:
                    try:
                        ext = foto_alvo.name.split('.')[-1]
                        nome_arquivo = f"alvos_{uuid.uuid4()}.{ext}"
                        file_bytes = foto_alvo.read()
                        supabase.storage.from_('Fotos').upload(nome_arquivo, file_bytes, {"content-type": foto_alvo.type})
                        url_foto = supabase.storage.from_('Fotos').get_public_url(nome_arquivo)
                    except Exception as e:
                        st.error(f"Erro ao subir a imagem: {e}")

                lat_alvo, lon_alvo = extrair_coordenadas(coordenadas_alvo)

                dados = {
                    "nome": nome, "vulgo": vulgo, "cpf": cpf,
                    "faccao_grupo": faccao, "endereco": endereco,
                    "latitude": lat_alvo, "longitude": lon_alvo,
                    "observacoes": obs, "caminho_foto": url_foto
                }
                supabase.table("dim_pessoas").insert(dados).execute()
                st.success(f"✅ Alvo '{nome}' registado com sucesso!")

# ----------------- ABA 2: LOCAIS / FATOS -----------------
with aba_local:
    st.subheader("Registo de Local ou Denúncia")
    
    # Sistema defensivo para puxar os alvos (Tenta id_pessoa, se falhar tenta id)
    try:
        resposta_alvos = supabase.table("dim_pessoas").select("id_pessoa, nome, vulgo").execute()
        lista_alvos = resposta_alvos.data
        dicionario_alvos = {f"{a['nome']} ({a['vulgo']})": a['id_pessoa'] for a in lista_alvos}
    except:
        try:
            resposta_alvos = supabase.table("dim_pessoas").select("id, nome, vulgo").execute()
            lista_alvos = resposta_alvos.data
            dicionario_alvos = {f"{a['nome']} ({a['vulgo']})": a['id'] for a in lista_alvos}
        except:
            dicionario_alvos = {}

    with st.form("form_local", clear_on_submit=True):
        tipo_evento = st.selectbox("Tipo de Registo *", ["Denúncia Biqueira", "Local de Reunião", "Apreensão", "Outro"])
        bairro = st.text_input("Bairro / Rua / Referência *")
        coordenadas_fato = st.text_input("Coordenadas (Cole do Google Maps, ex: -15.8932, -52.2599)")
        resumo = st.text_area("Resumo da Denúncia / Observações")
        foto_local = st.file_uploader("Fotografia do Local (Fachada/Muro)", type=["png", "jpg", "jpeg"])
        
        st.markdown("---")
        st.write("🔗 **Vincular a Alvos Conhecidos (Opcional)**")
        alvos_selecionados = st.multiselect("Selecione os indivíduos envolvidos neste fato:", options=list(dicionario_alvos.keys()))
        
        submit_local = st.form_submit_button("Gravar Fato na Base")

        if submit_local:
            if not bairro:
                st.error("O campo Bairro/Referência é obrigatório!")
            else:
                url_foto_local = ""
                if foto_local:
                    try:
                        ext = foto_local.name.split('.')[-1]
                        nome_arquivo = f"locais_{uuid.uuid4()}.{ext}"
                        file_bytes = foto_local.read()
                        supabase.storage.from_('Fotos').upload(nome_arquivo, file_bytes, {"content-type": foto_local.type})
                        url_foto_local = supabase.storage.from_('Fotos').get_public_url(nome_arquivo)
                    except Exception as e:
                        st.error(f"Erro ao subir a imagem: {e}")

                lat_fato, lon_fato = extrair_coordenadas(coordenadas_fato)

                dados_fato = {
                    "tipo_evento": tipo_evento,
                    "bairro_setor": bairro,
                    "latitude": lat_fato,
                    "longitude": lon_fato,
                    "resumo_obs": resumo,
                    "caminho_foto": url_foto_local
                }
                
                try:
                    resposta_fato = supabase.table("fato_eventos").insert(dados_fato).execute()
                    
                    if alvos_selecionados and resposta_fato.data:
                        # Defesa: puxa o ID independentemente de ser id_evento ou id
                        id_novo_evento = resposta_fato.data[0].get('id_evento') or resposta_fato.data[0].get('id')
                        
                        for alvo_nome in alvos_selecionados:
                            id_do_alvo = dicionario_alvos[alvo_nome]
                            supabase.table("ponte_vinculos").insert({"id_pessoa": id_do_alvo, "id_evento": id_novo_evento}).execute()
                            
                    st.success("✅ Fato registado e vinculado com sucesso!")
                except Exception as e:
                    st.error(f"❌ ERRO NO BANCO: {e}")
