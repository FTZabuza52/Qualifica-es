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
# CONEXÃO SUPABASE
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
try:
    resp = supabase.table("dim_pessoas").select("*").execute()
    dic_alvos = {f"{a.get('nome','')} ({a.get('vulgo','')})": a.get('id_pessoa') for a in resp.data}
except: dic_alvos = {}

try:
    resp = supabase.table("fato_eventos").select("*").execute()
    dic_fatos = {f"{a.get('tipo_evento','')} - {a.get('bairro_setor','')}": a.get('id_evento') for a in resp.data}
except: dic_fatos = {}

try:
    resp = supabase.table("dim_veiculos").select("*").execute()
    dic_veiculos = {f"{a.get('placa','S/Placa')} - {a.get('cor','')} {a.get('tipo','')}": a.get('id_veiculo') for a in resp.data}
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
        st.markdown("### Qualificação do Alvo")
        nome = st.text_input("Nome Completo")
        vulgo = st.text_input("Vulgo")
        
        col_mae, col_nasc = st.columns(2)
        with col_mae:
            nome_mae = st.text_input("Nome da Mãe")
        with col_nasc:
            data_nascimento = st.text_input("Data de Nascimento")
            
        cpf = st.text_input("CPF")
        
        st.markdown("### Endereço Fixo (Moradia)")
        endereco = st.text_input("Endereço Residencial")
        coordenadas_alvo = st.text_input("Localização do Endereço (Lat, Lon do Maps)")
        
        st.markdown("### Características e Mídia")
        tatuagens = st.text_area("Tatuagens e Sinais (Descreva detalhes)")
        obs = st.text_area("Observações Gerais")
        
        # UPLOAD MÚLTIPLO LIBERADO AQUI
        fotos_alvo = st.file_uploader("Fotografias do Alvo (Pode selecionar várias)", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
        
        st.markdown("---")
        st.write("🔗 **Vínculos Múltiplos**")
        v_fatos = st.multiselect("Vincular a Fatos/Locais (Ex: Abordagens):", list(dic_fatos.keys()), key="alvo_fatos")
        v_veiculos = st.multiselect("Vincular a Veículos:", list(dic_veiculos.keys()), key="alvo_veiculos")
        
        if st.form_submit_button("Gravar Alvo"):
            # Lógica para subir múltiplas fotos e salvar os links separados por vírgula
            urls_fotos = []
            if fotos_alvo:
                for foto in fotos_alvo:
                    ext = foto.name.split('.')[-1]
                    nome_arq = f"alvos_{uuid.uuid4()}.{ext}"
                    supabase.storage.from_('Fotos').upload(nome_arq, foto.read(), {"content-type": foto.type})
                    urls_fotos.append(supabase.storage.from_('Fotos').get_public_url(nome_arq))
            url_foto_final = ", ".join(urls_fotos)

            lat_alvo, lon_alvo = extrair_coordenadas(coordenadas_alvo)
            dados = {
                "nome": nome, "vulgo": vulgo, "nome_mae": nome_mae, 
                "data_nascimento": data_nascimento, "cpf": cpf, 
                "endereco": endereco, "latitude": lat_alvo, "longitude": lon_alvo, 
                "tatuagens_sinais": tatuagens, "observacoes": obs, "caminho_foto": url_foto_final
            }
            
            try:
                res = supabase.table("dim_pessoas").insert(dados).execute()
                if res.data:
                    id_novo = res.data[0].get('id_pessoa')
                    for f in v_fatos:
                        supabase.table("ponte_vinculos").insert({"id_pessoa": id_novo, "id_evento": dic_fatos[f]}).execute()
                    for v in v_veiculos:
                        supabase.table("ponte_pessoas_veiculos").insert({"id_pessoa": id_novo, "id_veiculo": dic_veiculos[v]}).execute()
                st.success(f"✅ Indivíduo gravado e vinculado com sucesso!")
            except Exception as e: st.error(f"❌ Erro: {e}")

# ----------------- ABA 2: FATOS / EVENTOS -----------------
with aba_local:
    with st.form("form_local", clear_on_submit=True):
        st.markdown("### Registo do Evento / Local")
        
        # ADICIONADO "Visto/Abordado"
        lista_eventos = [
            "Visto/Abordado", "LTD", "MP ATIVO", "Casa bomba", "Indivíduo Armado", 
            "Veículo com queixa de roubo ou furto", "Veículo usado em Crime", 
            "Lideranças/Disciplina", "Ponto de Salves", "Outro"
        ]
        tipo_evento = st.selectbox("Tipo de Evento", lista_eventos)
        
        bairro = st.text_input("Bairro / Setor")
        coordenadas_fato = st.text_input("Coordenadas Exatas (Lat, Lon do Maps)")
        resumo = st.text_area("Detalhes da Patrulha (Resumo do que foi avistado/apreendido)")
        
        # UPLOAD MÚLTIPLO LIBERADO AQUI
        fotos_local = st.file_uploader("Fotografias do Local ou Abordagem (Pode selecionar várias)", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
        
        st.markdown("---")
        st.write("🔗 **Vínculos Múltiplos**")
        v_alvos = st.multiselect("Vincular a Indivíduos (Ex: Quem foi visto junto):", list(dic_alvos.keys()), key="fato_alvos")
        v_veic_fato = st.multiselect("Vincular a Veículos (Ex: Veículos no local):", list(dic_veiculos.keys()), key="fato_veic")
        
        if st.form_submit_button("Gravar Evento"):
            # Lógica para subir múltiplas fotos do evento
            urls_fotos_local = []
            if fotos_local:
                for foto in fotos_local:
                    ext = foto.name.split('.')[-1]
                    nome_arq = f"locais_{uuid.uuid4()}.{ext}"
                    supabase.storage.from_('Fotos').upload(nome_arq, foto.read(), {"content-type": foto.type})
                    urls_fotos_local.append(supabase.storage.from_('Fotos').get_public_url(nome_arq))
            url_foto_local_final = ", ".join(urls_fotos_local)

            lat_fato, lon_fato = extrair_coordenadas(coordenadas_fato)
            dados_fato = {
                "tipo_evento": tipo_evento, "bairro_setor": bairro, 
                "latitude": lat_fato, "longitude": lon_fato, 
                "resumo_obs": resumo, "caminho_foto": url_foto_local_final
            }
            
            try:
                res = supabase.table("fato_eventos").insert(dados_fato).execute()
                if res.data:
                    id_novo = res.data[0].get('id_evento')
                    # Aqui a mágica do vínculo acontece (Múltiplos alvos e múltiplos carros para o mesmo evento)
                    for a in v_alvos:
                        supabase.table("ponte_vinculos").insert({"id_pessoa": dic_alvos[a], "id_evento": id_novo}).execute()
                    for v in v_veic_fato:
                        supabase.table("ponte_fatos_veiculos").insert({"id_evento": id_novo, "id_veiculo": dic_veiculos[v]}).execute()
                st.success("✅ Fato/Evento gravado e vinculado!")
            except Exception as e: st.error(f"❌ Erro: {e}")

# ----------------- ABA 3: VEÍCULOS -----------------
with aba_veiculo:
    with st.form("form_veiculo", clear_on_submit=True):
        st.markdown("### Registo de Veículo")
        
        col_tipo, col_marca = st.columns(2)
        with col_tipo:
            tipo_basico = st.selectbox("Tipo", ["Carro", "Moto", "Caminhonete", "Caminhão", "Outro"])
        with col_marca:
            marca_modelo = st.text_input("Marca/Modelo (Ex: Honda CG 160)")
            
        col_cor, col_placa = st.columns(2)
        with col_cor:
            cor = st.text_input("Cor Predominante")
        with col_placa:
            placa = st.text_input("Placa")
            
        caracteristicas = st.text_area("Características Marcantes (Adesivos, amassados, rodas, insulfilm)")
        
        st.markdown("---")
        st.write("🔗 **Vínculos Múltiplos**")
        v_alvos_veic = st.multiselect("Vincular a Indivíduos (Dono/Condutor):", list(dic_alvos.keys()), key="veic_alvos")
        v_fatos_veic = st.multiselect("Vincular a Fatos (Localizado/Apreendido em):", list(dic_fatos.keys()), key="veic_fatos")
        
        if st.form_submit_button("Gravar Veículo"):
            tipo_final = f"{tipo_basico} - {marca_modelo}" if marca_modelo else tipo_basico
            dados_veic = {"tipo": tipo_final, "cor": cor, "placa": placa, "caracteristicas": caracteristicas}
            
            try:
                res = supabase.table("dim_veiculos").insert(dados_veic).execute()
                if res.data:
                    id_novo = res.data[0].get('id_veiculo')
                    for a in v_alvos_veic:
                        supabase.table("ponte_pessoas_veiculos").insert({"id_pessoa": dic_alvos[a], "id_veiculo": id_novo}).execute()
                    for f in v_fatos_veic:
                        supabase.table("ponte_fatos_veiculos").insert({"id_evento": dic_fatos[f], "id_veiculo": id_novo}).execute()
                st.success("✅ Veículo gravado e vinculado!")
            except Exception as e: st.error(f"❌ Erro: {e}")
