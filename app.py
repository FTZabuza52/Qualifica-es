import streamlit as st
from supabase import create_client, Client
import uuid
from datetime import datetime, date

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
# RECOLHA DE DADOS (DICIONÁRIOS BLINDADOS)
# ==========================================
try:
    resp_p = supabase.table("dim_pessoas").select("*").execute()
    lista_alvos_bruta = resp_p.data if resp_p.data else []
    dic_alvos = {f"{a.get('nome','')} ({a.get('vulgo','')})": a.get('id_pessoa') for a in lista_alvos_bruta}
except Exception as e:
    dic_alvos = {}
    lista_alvos_bruta = []

try:
    resp_links = supabase.table("ponte_vinculos").select("*").execute()
    links_fatos_pessoas = resp_links.data if resp_links.data else []
except:
    links_fatos_pessoas = []

try:
    resp_f = supabase.table("fato_eventos").select("*").execute()
    lista_fatos_bruta = resp_f.data if resp_f.data else []
    fatos_nomes_map = {}
    for link in links_fatos_pessoas:
        id_ev = link.get('id_evento')
        id_pe = link.get('id_pessoa')
        nome_p = next((p.get('nome') for p in lista_alvos_bruta if p.get('id_pessoa') == id_pe), None)
        if nome_p:
            if id_ev not in fatos_nomes_map: fatos_nomes_map[id_ev] = []
            fatos_nomes_map[id_ev].append(nome_p)
    dic_fatos = {}
    for f in lista_fatos_bruta:
        id_f = f.get('id_evento')
        tipo = f.get('tipo_evento', '')
        bairro = f.get('bairro_setor', '')
        nomes_vinculados = fatos_nomes_map.get(id_f, [])
        if nomes_vinculados:
            str_nomes = ", ".join(nomes_vinculados)
            label = f"[{str_nomes}] {tipo} - {bairro}"
        else:
            label = f"[Alvo Solto] {tipo} - {bairro}"
        while label in dic_fatos:
            label = f"{label} (*)"
        dic_fatos[label] = id_f
except Exception as e:
    dic_fatos = {}
    lista_fatos_bruta = []

try:
    resp_v = supabase.table("dim_veiculos").select("*").execute()
    lista_veiculos_bruta = resp_v.data if resp_v.data else []
    dic_veiculos = {f"{a.get('placa','S/Placa')} - {a.get('cor','')} {a.get('tipo','')}": a.get('id_veiculo') for a in lista_veiculos_bruta}
except Exception as e:
    dic_veiculos = {}
    lista_veiculos_bruta = []

# ==========================================
# CABEÇALHO E TABS
# ==========================================
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    try: st.image("logo.jpg", use_container_width=True)
    except: pass
st.markdown("<h2 style='text-align: center;'>Sistema de Inteligência FT-20</h2>", unsafe_allow_html=True)
st.divider()

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
        st.markdown("### Endereço Fixo (Moradia)")
        endereco = st.text_input("Endereço Residencial")
        coordenadas_alvo = st.text_input("Localização do Endereço (Lat, Lon do Maps)")
        st.markdown("### Características e Mídia")
        tatuagens = st.text_area("Tatuagens e Sinais")
        obs = st.text_area("Observações Gerais / Passagens")
        fotos_alvo = st.file_uploader("Fotografias do Alvo", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
        st.markdown("---")
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
                "tatuagens_sinais": tatuagens, "observacoes": obs, "caminho_foto": url_foto_final
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
        lista_eventos = ["Abordagem", "Visto/Abordado", "LTD", "MP ATIVO", "Casa bomba", "Indivíduo Armado", "Veículo com queixa de roubo", "Veículo usado em Crime", "Lideranças/Disciplina", "Ponto de Salves", "Outro"]
        
        col_tipo_fato, col_data_fato = st.columns(2)
        with col_tipo_fato:
            tipo_evento = st.selectbox("Tipo de Evento", lista_eventos)
        with col_data_fato:
            # ADICIONADO: Campo de Data (padrão é hoje)
            data_evento = st.date_input("Data do Evento")
            
        bairro = st.text_input("Bairro / Setor")
        coordenadas_fato = st.text_input("Coordenadas Exatas (Lat, Lon)")
        resumo = st.text_area("Detalhes da Patrulha")
        fotos_local = st.file_uploader("Fotografias do Local", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
        st.markdown("---")
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
            
            # ADICIONADO: Enviando a data selecionada para o banco
            dados_fato = {
                "tipo_evento": tipo_evento, 
                "data_hora": data_evento.isoformat(), 
                "bairro_setor": bairro, 
                "latitude": lat_fato, 
                "longitude": lon_fato, 
                "resumo_obs": resumo, 
                "caminho_foto": url_foto_local_final
            }
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
    tabela_alvo = st.radio("Selecione o banco de dados:", ["👤 Pessoas", "🏠 Fatos", "🚗 Veículos"], horizontal=True)

    if tabela_alvo == "👤 Pessoas":
        opcoes_alvos = list(dic_alvos.keys())
        if len(opcoes_alvos) == 0:
            st.warning("Nenhum indivíduo cadastrado.")
        else:
            alvo_selecionado = st.selectbox("Selecione o alvo para gerenciar:", [""] + opcoes_alvos)
            if alvo_selecionado != "":
                id_p = dic_alvos[alvo_selecionado]
                dados_alvo = next((item for item in lista_alvos_bruta if item["id_pessoa"] == id_p), None)
                if dados_alvo:
                    with st.form("form_upd_pessoa"):
                        st.markdown(f"**Editando Ficha Completa: {dados_alvo.get('nome')}**")
                        up_nome = st.text_input("Nome", value=dados_alvo.get('nome') or "")
                        up_vulgo = st.text_input("Vulgo", value=dados_alvo.get('vulgo') or "")
                        col_mae, col_nasc = st.columns(2)
                        with col_mae: up_mae = st.text_input("Nome da Mãe", value=dados_alvo.get('nome_mae') or "")
                        with col_nasc: up_nasc = st.text_input("Data de Nascimento", value=dados_alvo.get('data_nascimento') or "")
                        up_cpf = st.text_input("CPF", value=dados_alvo.get('cpf') or "")
                        up_endereco = st.text_input("Endereço Residencial", value=dados_alvo.get('endereco') or "")
                        lat_a, lon_a = dados_alvo.get('latitude') or "", dados_alvo.get('longitude') or ""
                        up_coords = st.text_input("Localização do Endereço (Lat, Lon)", value=f"{lat_a}, {lon_a}" if lat_a and lon_a else "")
                        up_tattoo = st.text_area("Tatuagens", value=dados_alvo.get('tatuagens_sinais') or "")
                        up_obs = st.text_area("Observações Gerais / Passagens", value=dados_alvo.get('observacoes') or "")
                        if st.form_submit_button("🔄 Salvar Alterações"):
                            try:
                                lat_nova, lon_nova = extrair_coordenadas(up_coords)
                                supabase.table("dim_pessoas").update({
                                    "nome": up_nome, "vulgo": up_vulgo, "nome_mae": up_mae, "data_nascimento": up_nasc,
                                    "cpf": up_cpf, "endereco": up_endereco, "latitude": lat_nova, "longitude": lon_nova,
                                    "tatuagens_sinais": up_tattoo, "observacoes": up_obs
                                }).eq("id_pessoa", id_p).execute()
                                st.success("✅ Dados de qualificação atualizados!")
                                st.rerun()
                            except Exception as e: st.error(f"Erro: {e}")
                    st.markdown("---")
                  if st.button("🗑️ EXCLUIR ALVO DEFINITIVAMENTE", type="primary"):
                        apagar_fotos_bucket(dados_alvo.get('caminho_foto'))
                        # Desamarra a teia primeiro
                        supabase.table("ponte_vinculos").delete().eq("id_pessoa", id_p).execute()
                        supabase.table("ponte_pessoas_veiculos").delete().eq("id_pessoa", id_p).execute()
                        # Exclui o alvo
                        supabase.table("dim_pessoas").delete().eq("id_pessoa", id_p).execute()
                        st.success("💀 Alvo e mídias erradicados da base.")
                        st.rerun()

    elif tabela_alvo == "🏠 Fatos":
        opcoes_fatos = list(dic_fatos.keys())
        if len(opcoes_fatos) == 0:
            st.warning("Nenhum evento cadastrado.")
        else:
            fato_selecionado = st.selectbox("Selecione o evento para gerenciar:", [""] + opcoes_fatos)
            if fato_selecionado != "":
                id_f = dic_fatos[fato_selecionado]
                dados_fato = next((item for item in lista_fatos_bruta if item["id_evento"] == id_f), None)
                if dados_fato:
                    with st.form("form_upd_fato"):
                        st.markdown(f"**Editando o Fato Selecionado**")
                        
                        try:
                            links = supabase.table("ponte_vinculos").select("id_pessoa").eq("id_evento", id_f).execute()
                            ids_p = [l['id_pessoa'] for l in (links.data or [])]
                            nomes_vinc = []
                            for pid in ids_p:
                                p_data = supabase.table("dim_pessoas").select("nome, vulgo").eq("id_pessoa", pid).execute()
                                if p_data.data: nomes_vinc.append(f"{p_data.data[0]['nome']} ({p_data.data[0]['vulgo']})")
                            
                            if nomes_vinc: st.info(f"🔗 **Alvos ligados a este registro:** {', '.join(nomes_vinc)}")
                            else: st.warning("🔗 Nenhum alvo vinculado a este registro.")
                        except: pass
                        
                        col_up_t, col_up_d = st.columns(2)
                        with col_up_t:
                            up_tipo = text_input_obj = st.text_input("Tipo Evento", value=dados_fato.get('tipo_evento') or "")
                            
                        # Tratamento para exibir a data atual na edição
                        data_str = dados_fato.get('data_hora')
                        try:
                            if data_str:
                                data_obj = datetime.strptime(data_str[:10], "%Y-%m-%d").date()
                            else:
                                data_obj = datetime.today().date()
                        except:
                            data_obj = datetime.today().date()
                            
                        with col_up_d:
                            up_data = st.date_input("Data do Evento", value=data_obj)
                            
                        up_bairro = st.text_input("Bairro", value=dados_fato.get('bairro_setor') or "")
                        up_resumo = st.text_area("Resumo", value=dados_fato.get('resumo_obs') or "")
                        
                        if st.form_submit_button("🔄 Salvar Alterações"):
                            try:
                                supabase.table("fato_eventos").update({
                                    "tipo_evento": up_tipo, 
                                    "data_hora": up_data.isoformat(),
                                    "bairro_setor": up_bairro, 
                                    "resumo_obs": up_resumo
                                }).eq("id_evento", id_f).execute()
                                st.success("✅ Dados atualizados!")
                                st.rerun()
                            except Exception as e: st.error(f"Erro: {e}")
                    st.markdown("---")
                   if st.button("🗑️ EXCLUIR EVENTO DEFINITIVAMENTE", type="primary"):
                        apagar_fotos_bucket(dados_fato.get('caminho_foto'))
                        # Desamarra a teia primeiro
                        supabase.table("ponte_vinculos").delete().eq("id_evento", id_f).execute()
                        supabase.table("ponte_fatos_veiculos").delete().eq("id_evento", id_f).execute()
                        # Exclui o evento
                        supabase.table("fato_eventos").delete().eq("id_evento", id_f).execute()
                        st.success("💀 Evento e mídias erradicados da base.")
                        st.rerun()
    elif tabela_alvo == "🚗 Veículos":
        opcoes_veiculos = list(dic_veiculos.keys())
        if len(opcoes_veiculos) == 0:
            st.warning("Nenhum veículo cadastrado.")
        else:
            veic_selecionado = st.selectbox("Selecione o veículo para gerenciar:", [""] + opcoes_veiculos)
            if veic_selecionado != "":
                id_v = dic_veiculos[veic_selecionado]
                dados_veic = next((item for item in lista_veiculos_bruta if item["id_veiculo"] == id_v), None)
                if dados_veic:
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
                        # Desamarra a teia primeiro
                        supabase.table("ponte_pessoas_veiculos").delete().eq("id_veiculo", id_v).execute()
                        supabase.table("ponte_fatos_veiculos").delete().eq("id_veiculo", id_v).execute()
                        # Exclui o veículo
                        supabase.table("dim_veiculos").delete().eq("id_veiculo", id_v).execute()
                        st.success("💀 Veículo erradicado da base.")
                        st.rerun()
