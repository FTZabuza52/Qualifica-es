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
# CONEXÃO SUPABASE E FUNÇÕES
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
# RECOLHA DE DADOS PARA OS VÍNCULOS
# ==========================================
# Puxa Pessoas
try:
    resp = supabase.table("dim_pessoas").select("*").execute()
    dic_alvos = {f"{a.get('nome','')} ({a.get('vulgo','')})": a.get('id_pessoa') or a.get('id') for a in resp.data}
except: dic_alvos = {}

# Puxa Fatos
try:
    resp = supabase.table("fato_eventos").select("*").execute()
    dic_fatos = {f"{a.get('tipo_evento','')} - {a.get('bairro_setor','')}": a.get('id_evento') or a.get('id') for a in resp.data}
except: dic_fatos = {}

# Puxa Veículos
try:
    resp = supabase.table("dim_veiculos").select("*").execute()
    dic_veiculos = {f"{a.get('placa','S/Placa')} - {a.get('cor','')} {a.get('tipo','')}": a.get('id_veiculo') or a.get('id') for a in resp.data}
except: dic_veiculos = {}

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
# INTERFACE PRINCIPAL (3 ABAS)
# ==========================================
aba_alvo, aba_local, aba_veiculo = st.tabs(["👤 Indivíduo", "🏠 Fato/Local", "🚗 Veículo"])

# ----------------- ABA 1: PESSOAS -----------------
with aba_alvo:
    with st.form("form_alvo", clear_on_submit=True):
        nome = st.text_input("Nome Completo")
        vulgo = st.text_input("Vulgo")
        cpf = st.text_input("CPF")
        faccao = st.selectbox("Facção/Grupo", ["Nenhuma", "CV", "PCC", "Outra"])
        endereco = st.text_input("Endereço Principal")
        coordenadas_alvo = st.text_input("Coordenadas (Cole do Maps, ex: -15.89, -52.25)")
        obs = st.text_area("Observações / Tatuagens")
        foto_alvo = st.file_uploader("Fotografia do Alvo", type=["png", "jpg", "jpeg"])
        
        st.markdown("---")
        st.write("🔗 **Vínculos Múltiplos**")
        v_fatos = st.multiselect("Vincular a Fatos/Locais:", list(dic_fatos.keys()), key="alvo_fatos")
        v_veiculos = st.multiselect("Vincular a Veículos:", list(dic_veiculos.keys()), key="alvo_veiculos")
        
        if st.form_submit_button("Gravar Alvo"):
            url_foto = ""
            if foto_alvo:
                ext = foto_alvo.name.split('.')[-1]
                nome_arq = f"alvos_{uuid.uuid4()}.{ext}"
                supabase.storage.from_('Fotos').upload(nome_arq, foto_alvo.read(), {"content-type": foto_alvo.type})
                url_foto = supabase.storage.from_('Fotos').get_public_url(nome_arq)

            lat_alvo, lon_alvo = extrair_coordenadas(coordenadas_alvo)
            dados = {"nome": nome, "vulgo": vulgo, "cpf": cpf, "faccao_grupo": faccao, "endereco": endereco, "latitude": lat_alvo, "longitude": lon_alvo, "observacoes": obs, "caminho_foto": url_foto}
            
            try:
                res = supabase.table("dim_pessoas").insert(dados).execute()
                if res.data:
                    id_novo = res.data[0].get('id_pessoa') or res.data[0].get('id')
                    for f in v_fatos:
                        supabase.table("ponte_vinculos").insert({"id_pessoa": id_novo, "id_evento": dic_fatos[f]}).execute()
                    for v in v_veiculos:
                        supabase.table("ponte_pessoas_veiculos").insert({"id_pessoa": id_novo, "id_veiculo": dic_veiculos[v]}).execute()
                st.success(f"✅ Indivíduo gravado e vinculado!")
            except Exception as e: st.error(f"❌ Erro: {e}")

# ----------------- ABA 2: LOCAIS / FATOS -----------------
with aba_local:
    with st.form("form_local", clear_on_submit=True):
        tipo_evento = st.selectbox("Tipo de Registo", ["Denúncia Biqueira", "Local de Reunião", "Apreensão", "Outro"])
        bairro = st.text_input("Bairro / Rua / Referência")
        coordenadas_fato = st.text_input("Coordenadas (Cole do Maps)")
        resumo = st.text_area("Resumo da Denúncia / Observações")
        foto_local = st.file_uploader("Fotografia do Local", type=["png", "jpg", "jpeg"])
        
        st.markdown("---")
        st.write("🔗 **Vínculos Múltiplos**")
        v_alvos = st.multiselect("Vincular a Indivíduos:", list(dic_alvos.keys()), key="fato_alvos")
        v_veic_fato = st.multiselect("Vincular a Veículos:", list(dic_veiculos.keys()), key="fato_veic")
        
        if st.form_submit_button("Gravar Fato"):
            url_foto_local = ""
            if foto_local:
                ext = foto_local.name.split('.')[-1]
                nome_arq = f"locais_{uuid.uuid4()}.{ext}"
                supabase.storage.from_('Fotos').upload(nome_arq, foto_local.read(), {"content-type": foto_local.type})
                url_foto_local = supabase.storage.from_('Fotos').get_public_url(nome_arq)

            lat_fato, lon_fato = extrair_coordenadas(coordenadas_fato)
            dados_fato = {"tipo_evento": tipo_evento, "bairro_setor": bairro, "latitude": lat_fato, "longitude": lon_fato, "resumo_obs": resumo, "caminho_foto": url_foto_local}
            
            try:
                res = supabase.table("fato_eventos").insert(dados_fato).execute()
                if res.data:
                    id_novo = res.data[0].get('id_evento') or res.data[0].get('id')
                    for a in v_alvos:
                        supabase.table("ponte_vinculos").insert({"id_pessoa": dic_alvos[a], "id_evento": id_novo}).execute()
                    for v in v_veic_fato:
                        supabase.table("ponte_fatos_veiculos").insert({"id_evento": id_novo, "id_veiculo": dic_veiculos[v]}).execute()
                st.success("✅ Fato gravado e vinculado!")
            except Exception as e: st.error(f"❌ Erro: {e}")

# ----------------- ABA 3: VEÍCULOS -----------------
with aba_veiculo:
    with st.form("form_veiculo", clear_on_submit=True):
        tipo = st.selectbox("Tipo de Veículo", ["Carro", "Moto", "Caminhonete", "Caminhão", "Outro"])
        cor = st.text_input("Cor Predominante")
        placa = st.text_input("Placa (Letras e Números)")
        caracteristicas = st.text_area("Características Específicas (Adesivos, Amolgadelas, Rebaixado, etc.)")
        
        st.markdown("---")
        st.write("🔗 **Vínculos Múltiplos**")
        v_alvos_veic = st.multiselect("Vincular a Indivíduos (Proprietário/Condutor):", list(dic_alvos.keys()), key="veic_alvos")
        v_fatos_veic = st.multiselect("Vincular a Fatos (Localizado/Apreendido em):", list(dic_fatos.keys()), key="veic_fatos")
        
        if st.form_submit_button("Gravar Veículo"):
            dados_veic = {"tipo": tipo, "cor": cor, "placa": placa, "caracteristicas": caracteristicas}
            try:
                res = supabase.table("dim_veiculos").insert(dados_veic).execute()
                if res.data:
                    id_novo = res.data[0].get('id_veiculo') or res.data[0].get('id')
                    for a in v_alvos_veic:
                        supabase.table("ponte_pessoas_veiculos").insert({"id_pessoa": dic_alvos[a], "id_veiculo": id_novo}).execute()
                    for f in v_fatos_veic:
                        supabase.table("ponte_fatos_veiculos").insert({"id_evento": dic_fatos[f], "id_veiculo": id_novo}).execute()
                st.success("✅ Veículo gravado e vinculado!")
            except Exception as e: st.error(f"❌ Erro: {e}")
