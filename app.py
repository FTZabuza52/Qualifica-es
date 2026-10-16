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
# CONEXÃO E FUNÇÕES BASE
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

# NOVA FUNÇÃO: DESTRUIÇÃO FÍSICA DE MÍDIA NO BUCKET
def apagar_fotos_bucket(string_urls):
    if not string_urls: return
    urls = string_urls.split(',')
    arquivos_alvo = []
    for url in urls:
        url = url.strip()
        if url:
            nome_arquivo = url.split('/')[-1]
            arquivos_alvo.append(nome_arquivo)
    
    if arquivos_alvo:
        try:
            supabase.storage.from_('Fotos').remove(arquivos_alvo)
        except Exception as e:
            st.error(f"Aviso - Falha ao limpar bucket: {e}")

# ==========================================
# RECOLHA DE DADOS (DICIONÁRIOS)
# ==========================================
try:
    resp = supabase.table("dim_pessoas").select("*").execute()
    dic_alvos = {f"{a.get('nome','')} ({a.get('vulgo','')})": a.get('id_pessoa') for a in resp.data}
    lista_alvos_bruta = resp.data
except: 
    dic_alvos = {}
    lista_alvos_bruta = []

try:
    resp = supabase.table("fato_eventos").select("*").execute()
    dic_fatos = {f"{a.get('tipo_evento','')} - {a.get('bairro_setor','')}": a.get('id_evento') for a in resp.data}
    lista_fatos_bruta = resp.data
except: 
    dic_fatos = {}
    lista_fatos_bruta = []

try:
    resp = supabase.table("dim_veiculos").select("*").execute()
    dic_veiculos = {f"{a.get('placa','S/Placa')} - {a.get('cor','')} {a.get('tipo','')}": a.get('id_veiculo') for a in resp.data}
    lista_veiculos_bruta = resp.data
except: 
    dic_veiculos = {}
    lista_veiculos_bruta = []

# ==========================================
# CABEÇALHO
# ==========================================
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    try:
        st.image("logo.jpg", use_container_width=True)
    except:
        pass

st.markdown("<h2 style='text-align: center;'>Sistema de Inteligência FT-20</h2>", unsafe_allow_html=True)
st.divider()

# ==========================================
# INTERFACE PRINCIPAL (4 ABAS AGORA)
# ==========================================
aba_alvo, aba_local, aba_veiculo, aba_gestao = st.tabs(["👤 Indivíduo", "🏠 Fato/Local", "🚗 Veículo", "⚙️ Gestão"])

# ----------------- ABA 1: PESSOAS -----------------
with aba_alvo:
    with st.form("form_alvo", clear_on_submit=True):
        st.markdown("### Qualificação do Alvo")
        nome = st.text_input("Nome Completo")
        vulgo = st.text_input("Vulgo")
        
        col_mae, col_nasc = st.columns(2)
        with col_mae: nome_mae = st.text_input("Nome da Mãe")
        with col_nasc: data_nascimento = st.text_input("Data de Nascimento")
            
        cpf = st.text_input("CPF")
        
        st.markdown("### Endereço e MP")
        status_mandado = st.text_input("Status Mandado (Ex: Ativo - Homicídio)")
        endereco = st.text_input("Endereço Residencial")
        coordenadas_alvo = st.text_input("Localização do Endereço (Lat, Lon do Maps)")
        
        st.markdown("### Características e Mídia")
        tatuagens = st.text_area("Tatuagens e Sinais")
        obs = st.text_area("Observações Gerais")
        
        fotos_alvo = st.file_uploader("Fotografias do Alvo", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
        
        st.markdown("---")
        st.write("🔗 **Vínculos Iniciais**")
        v_fatos = st.multiselect("Vincular a Fatos/Locais:", list(dic_fatos.keys()), key="alvo_fatos")
        v_veiculos = st.multiselect("Vincular a Veículos:", list(dic_veiculos.keys()), key="alvo_veiculos")
        
        if st.form_submit_button("Gravar Alvo"):
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
                "nome": nome, "vulgo": vulgo, "nome_mae": nome_mae, "data_nascimento": data_nascimento, 
                "cpf": cpf, "endereco": endereco, "latitude": lat_alvo, "longitude": lon_alvo, 
                "tatuagens_sinais": tatuagens, "observacoes": obs, "status_mandado": status_mandado,
                "caminho_foto": url_foto_final
            }
            
            try:
                res = supabase.table("dim_pessoas").insert(dados).execute()
                if res.data:
                    id_novo = res.data[0].get('id_pessoa')
                    for f in v_fatos: supabase.table("ponte_vinculos").insert({"id_pessoa": id_novo, "id_evento": dic_fatos[f]}).execute()
                    for v in v_veiculos: supabase.table("ponte_pessoas_veiculos").insert({"id_pessoa": id_novo, "id_veiculo": dic_veiculos[v]}).execute()
                st.success(f"✅ Indivíduo gravado com sucesso!")
            except Exception as e: st.error(f"❌ Erro: {e}")

# ----------------- ABA 2: FATOS / EVENTOS -----------------
with aba_local:
    with st.form("form_local", clear_on_submit=True):
        st.markdown("### Registo do Evento")
        lista_eventos = ["Visto/Abordado", "LTD", "MP ATIVO", "Casa bomba", "Indivíduo Armado", "Veículo com queixa de roubo", "Veículo usado em Crime", "Lideranças/Disciplina", "Ponto de Salves", "Outro"]
        tipo_evento = st.selectbox("Tipo de Evento", lista_eventos)
        
        bairro = st.text_input("Bairro / Setor")
        coordenadas_fato = st.text_input("Coordenadas Exatas (Lat, Lon)")
        resumo = st.text_area("Detalhes da Patrulha")
        fotos_local = st.file_uploader("Fotografias do Local", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
        
        st.markdown("---")
        st.write("🔗 **Vínculos Iniciais**")
        v_alvos = st.multiselect("Vincular a Indivíduos:", list(dic_alvos.keys()), key="fato_alvos")
        v_veic_fato = st.multiselect("Vincular a Veículos:", list(dic_veiculos.keys()), key="fato_veic")
        
        if st.form_submit_button("Gravar Evento"):
            urls_fotos_local = []
            if fotos_local:
                for foto in fotos_local:
                    ext = foto.name.split('.')[-1]
                    nome_arq = f"locais_{uuid.uuid4()}.{ext}"
                    supabase.storage.from_('Fotos').upload(nome_arq, foto.read(), {"content-type": foto.type})
                    urls_fotos_local.append(supabase.storage.from_('Fotos').get_public_url(nome_arq))
            url_foto_local_final = ", ".join(urls_fotos_local)

            lat_fato, lon_fato = extrair_coordenadas(coordenadas_fato)
            dados_fato = {"tipo_evento": tipo_evento, "bairro_setor": bairro, "latitude": lat_fato, "longitude": lon_fato, "resumo_obs": resumo, "caminho_foto": url_foto_local_final}
            
            try:
                res = supabase.table("fato_eventos").insert(dados_fato).execute()
                if res.data:
                    id_novo = res.data[0].get('id_evento')
                    for a in v_alvos: supabase.table("ponte_vinculos").insert({"id_pessoa": dic_alvos[a], "id_evento": id_novo}).execute()
                    for v in v_veic_fato: supabase.table("ponte_fatos_veiculos").insert({"id_evento": id_novo, "id_veiculo": dic_veiculos[v]}).execute()
                st.success("✅ Evento gravado com sucesso!")
            except Exception as e: st.error(f"❌ Erro: {e}")

# ----------------- ABA 3: VEÍCULOS -----------------
with aba_veiculo:
    with st.form("form_veiculo", clear_on_submit=True):
        st.markdown("### Registo de Veículo")
        col_tipo, col_marca = st.columns(2)
        with col_tipo: tipo_basico = st.selectbox("Tipo", ["Carro", "Moto", "Caminhonete", "Caminhão", "Outro"])
        with col_marca: marca_modelo = st.text_input("Marca/Modelo")
            
        col_cor, col_placa = st.columns(2)
        with col_cor: cor = st.text_input("Cor Predominante")
        with col_placa: placa = st.text_input("Placa")
            
        caracteristicas = st.text_area("Características Marcantes")
        
        st.markdown("---")
        v_alvos_veic = st.multiselect("Vincular a Indivíduos:", list(dic_alvos.keys()), key="veic_alvos")
        v_fatos_veic = st.multiselect("Vincular a Fatos:", list(dic_fatos.keys()), key="veic_fatos")
        
        if st.form_submit_button("Gravar Veículo"):
            tipo_final = f"{tipo_basico} - {marca_modelo}" if marca_modelo else tipo_basico
            dados_veic = {"tipo": tipo_final, "cor": cor, "placa": placa, "caracteristicas": caracteristicas}
            
            try:
                res = supabase.table("dim_veiculos").insert(dados_veic).execute()
                if res.data:
                    id_novo = res.data[0].get('id_veiculo')
                    for a in v_alvos_veic: supabase.table("ponte_pessoas_veiculos").insert({"id_pessoa": dic_alvos[a], "id_veiculo": id_novo}).execute()
                    for f in v_fatos_veic: supabase.table("ponte_fatos_veiculos").insert({"id_evento": dic_fatos[f], "id_veiculo": id_novo}).execute()
                st.success("✅ Veículo gravado com sucesso!")
            except Exception as e: st.error(f"❌ Erro: {e}")

# ----------------- ABA 4: GESTÃO E AUDITORIA -----------------
with aba_gestao:
    st.markdown("### ⚙️ Painel de Controle de Dados")
    st.info("Aqui você altera informações existentes ou apaga registros. Apagar um registro destrói automaticamente as fotos no servidor.")
    
    tabela_alvo = st.radio("Selecione o banco de dados:", ["👤 Pessoas", "🏠 Fatos", "🚗 Veículos"], horizontal=True)

    # LÓGICA DE GESTÃO PARA PESSOAS
    if tabela_alvo == "👤 Pessoas":
        if not dic_alvos:
            st.warning("Nenhum indivíduo cadastrado.")
        else:
            alvo_selecionado = st.selectbox("Selecione o alvo para gerenciar:", [""] + list(dic_alvos.keys()))
            if alvo_selecionado:
                id_p = dic_alvos[alvo_selecionado]
                # Puxa o dicionário completo do alvo selecionado
                dados_alvo = next(item for item in lista_alvos_bruta if item["id_pessoa"] == id_p)
                
                with st.form("form_upd_pessoa"):
                    st.markdown(f"**Editando: {dados_alvo.get('nome')}**")
                    up_nome = st.text_input("Nome", value=dados_alvo.get('nome') or "")
                    up_vulgo = st.text_input("Vulgo", value=dados_alvo.get('vulgo') or "")
                    up_cpf = st.text_input("CPF", value=dados_alvo.get('cpf') or "")
                    up_status = st.text_input("Status Mandado", value=dados_alvo.get('status_mandado') or "")
                    up_tattoo = st.text_area("Tatuagens", value=dados_alvo.get('tatuagens_sinais') or "")
                    
                    if st.form_submit_button("🔄 Salvar Alterações"):
                        try:
                            supabase.table("dim_pessoas").update({
                                "nome": up_nome, "vulgo": up_vulgo, "cpf": up_cpf, 
                                "status_mandado": up_status, "tatuagens_sinais": up_tattoo
                            }).eq("id_pessoa", id_p).execute()
                            st.success("✅ Dados atualizados!")
                            st.rerun()
                        except Exception as e: st.error(f"Erro: {e}")

                st.markdown("---")
                if st.button("🗑️ EXCLUIR ALVO DEFINITIVAMENTE", type="primary"):
                    apagar_fotos_bucket(dados_alvo.get('caminho_foto'))
                    supabase.table("dim_pessoas").delete().eq("id_pessoa", id_p).execute()
                    st.success("💀 Alvo e mídias erradicados da base.")
                    st.rerun()

    # LÓGICA DE GESTÃO PARA FATOS
    elif tabela_alvo == "🏠 Fatos":
        if not dic_fatos:
            st.warning("Nenhum evento cadastrado.")
        else:
            fato_selecionado = st.selectbox("Selecione o evento para gerenciar:", [""] + list(dic_fatos.keys()))
            if fato_selecionado:
                id_f = dic_fatos[fato_selecionado]
                dados_fato = next(item for item in lista_fatos_bruta if item["id_evento"] == id_f)
                
                with st.form("form_upd_fato"):
                    st.markdown(f"**Editando Evento ID: {id_f}**")
                    up_tipo = st.text_input("Tipo Evento", value=dados_fato.get('tipo_evento') or "")
                    up_bairro = st.text_input("Bairro", value=dados_fato.get('bairro_setor') or "")
                    up_resumo = st.text_area("Resumo", value=dados_fato.get('resumo_obs') or "")
                    
                    if st.form_submit_button("🔄 Salvar Alterações"):
                        try:
                            supabase.table("fato_eventos").update({
                                "tipo_evento": up_tipo, "bairro_setor": up_bairro, "resumo_obs": up_resumo
                            }).eq("id_evento", id_f).execute()
                            st.success("✅ Dados atualizados!")
                            st.rerun()
                        except Exception as e: st.error(f"Erro: {e}")

                st.markdown("---")
                if st.button("🗑️ EXCLUIR EVENTO DEFINITIVAMENTE", type="primary"):
                    apagar_fotos_bucket(dados_fato.get('caminho_foto'))
                    supabase.table("fato_eventos").delete().eq("id_evento", id_f).execute()
                    st.success("💀 Evento e mídias erradicados da base.")
                    st.rerun()

    # LÓGICA DE GESTÃO PARA VEÍCULOS
    elif tabela_alvo == "🚗 Veículos":
        if not dic_veiculos:
            st.warning("Nenhum veículo cadastrado.")
        else:
            veic_selecionado = st.selectbox("Selecione o veículo para gerenciar:", [""] + list(dic_veiculos.keys()))
            if veic_selecionado:
                id_v = dic_veiculos[veic_selecionado]
                dados_veic = next(item for item in lista_veiculos_bruta if item["id_veiculo"] == id_v)
                
                with st.form("form_upd_veic"):
                    st.markdown(f"**Editando Veículo: {dados_veic.get('placa')}**")
                    up_tipo_v = st.text_input("Tipo/Modelo", value=dados_veic.get('tipo') or "")
                    up_cor_v = st.text_input("Cor", value=dados_veic.get('cor') or "")
                    up_placa_v = st.text_input("Placa", value=dados_veic.get('placa') or "")
                    up_carac_v = st.text_area("Características", value=dados_veic.get('caracteristicas') or "")
                    
                    if st.form_submit_button("🔄 Salvar Alterações"):
                        try:
                            supabase.table("dim_veiculos").update({
                                "tipo": up_tipo_v, "cor": up_cor_v, "placa": up_placa_v, "caracteristicas": up_carac_v
                            }).eq("id_veiculo", id_v).execute()
                            st.success("✅ Dados atualizados!")
                            st.rerun()
                        except Exception as e: st.error(f"Erro: {e}")

                st.markdown("---")
                if st.button("🗑️ EXCLUIR VEÍCULO DEFINITIVAMENTE", type="primary"):
                    supabase.table("dim_veiculos").delete().eq("id_veiculo", id_v).execute()
                    st.success("💀 Veículo erradicado da base.")
                    st.rerun()
