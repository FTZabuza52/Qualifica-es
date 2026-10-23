import streamlit as st
from supabase import create_client, Client
import uuid
from datetime import datetime, date
import imagehash
from PIL import Image
import io
import numpy as np
import requests
import face_recognition

# ==========================================
# CONFIGURAÇÕES DA PÁGINA
# ==========================================
st.set_page_config(page_title="FT-20 | Informações de Serviço", page_icon="🛡️", layout="wide")

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
# CONEXÃO E FUNÇÕES AUXILIARES
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

def gerar_hash_foto(foto_bytes):
    try:
        imagem = Image.open(io.BytesIO(foto_bytes))
        return str(imagehash.average_hash(imagem))
    except:
        return None

def checar_mandado_ativo(id_pessoa):
    try:
        links = supabase.table("ponte_vinculos").select("id_evento").eq("id_pessoa", id_pessoa).execute()
        for link in (links.data or []):
            fato = supabase.table("fato_eventos").select("tipo_evento, resumo_obs").eq("id_evento", link['id_evento']).execute()
            if fato.data and fato.data[0]['tipo_evento'] == "MP ATIVO":
                return fato.data[0].get('resumo_obs') or "ATIVO"
    except: pass
    return False

# ==========================================
# RECOLHA DE DADOS EM BANCO
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
            label = f"[{', '.join(nomes_vinculados)}] {tipo} - {bairro}"
        else:
            label = f"[Alvo Solto] {tipo} - {bairro}"
        while label in dic_fatos: label = f"{label} (*)"
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
# CABEÇALHO E NAVEGAÇÃO
# ==========================================
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    try: st.image("logo.jpg", use_container_width=True)
    except: pass
st.markdown("<h2 style='text-align: center;'>Sistema de Inteligência FT-20</h2>", unsafe_allow_html=True)
st.divider()

aba_alvo, aba_local, aba_veiculo, aba_gestao, aba_busca_visual = st.tabs([
    "👤 Indivíduo", "🏠 Fato/Local", "🚗 Veículo", "⚙️ Gestão", "📸 Reconhecimento Facial / Visual"
])

# ----------------- ABA 1: PESSOAS -----------------
with aba_alvo:
    st.markdown("### 🔍 Verificação Prévia")
    busca_pessoa = st.text_input("Digite o Nome, Vulgo ou CPF antes de cadastrar para evitar duplicidade:", key="busca_pes_nova")
    
    if busca_pessoa and len(busca_pessoa) >= 3:
        termo = busca_pessoa.lower()
        similares = [p for p in lista_alvos_bruta if termo in str(p.get('nome', '')).lower() or termo in str(p.get('vulgo', '')).lower() or termo in str(p.get('cpf', '')).lower()]
        if similares:
            st.warning(f"⚠️ **Atenção! Encontrámos {len(similares)} registo(s) semelhante(s):**")
            for p in similares:
                st.markdown(f"• **{p.get('nome')}** (Vulgo: _{p.get('vulgo', 'N/D')}_) | CPF: `{p.get('cpf', 'N/D')}`")
        else:
            st.success("✔️ Nenhum alvo encontrado. Pode prosseguir com o cadastro.")
    
    st.markdown("---")
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
            urls_fotos, hashes_fotos = [], []
            if fotos_alvo:
                for foto in fotos_alvo:
                    conteudo = foto.read()
                    h = gerar_hash_foto(conteudo)
                    if h: hashes_fotos.append(h)
                    ext = foto.name.split('.')[-1]
                    nome_arq = f"alvos_{uuid.uuid4()}.{ext}"
                    supabase.storage.from_('Fotos').upload(nome_arq, conteudo, {"content-type": foto.type})
                    urls_fotos.append(supabase.storage.from_('Fotos').get_public_url(nome_arq))
                    
            url_foto_final = ", ".join(urls_fotos)
            hash_final = ", ".join(hashes_fotos) if hashes_fotos else None
            lat_alvo, lon_alvo = extrair_coordenadas(coordenadas_alvo)
            
            dados = {
                "nome": nome, "vulgo": vulgo, "nome_mae": nome_mae, "data_nascimento": data_nascimento, 
                "cpf": cpf, "endereco": endereco, "latitude": lat_alvo, "longitude": lon_alvo, 
                "tatuagens_sinais": tatuagens, "observacoes": obs, "caminho_foto": url_foto_final,
                "foto_hash": hash_final
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
        with col_tipo_fato: tipo_evento = st.selectbox("Tipo de Evento", lista_eventos)
        with col_data_fato: data_evento = st.date_input("Data do Evento")
            
        bairro = st.text_input("Bairro / Setor")
        coordenadas_fato = st.text_input("Coordenadas Exatas (Lat, Lon)")
        resumo = st.text_area("Detalhes da Patrulha")
        fotos_local = st.file_uploader("Fotografias do Local", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
        st.markdown("---")
        v_alvos = st.multiselect("Vincular a Indivíduos:", list(dic_alvos.keys()), key="fato_alvos")
        v_veic_fato = st.multiselect("Vincular a Veículos:", list(dic_veiculos.keys()), key="fato_veic")
        
        if st.form_submit_button("Gravar Evento"):
            urls_fotos_local, hashes_fotos_local = [], []
            if fotos_local:
                for foto in fotos_local:
                    conteudo = foto.read()
                    h = gerar_hash_foto(conteudo)
                    if h: hashes_fotos_local.append(h)
                    ext = foto.name.split('.')[-1]
                    nome_arq = f"locais_{uuid.uuid4()}.{ext}"
                    supabase.storage.from_('Fotos').upload(nome_arq, conteudo, {"content-type": foto.type})
                    urls_fotos_local.append(supabase.storage.from_('Fotos').get_public_url(nome_arq))
                    
            url_foto_local_final = ", ".join(urls_fotos_local)
            hash_local_final = ", ".join(hashes_fotos_local) if hashes_fotos_local else None
            lat_fato, lon_fato = extrair_coordenadas(coordenadas_fato)
            
            dados_fato = {
                "tipo_evento": tipo_evento, "data_hora": data_evento.isoformat(), 
                "bairro_setor": bairro, "latitude": lat_fato, "longitude": lon_fato, 
                "resumo_obs": resumo, "caminho_foto": url_foto_local_final, "foto_hash": hash_local_final
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
            dados_veic = {"tipo": tipo_final, "cor": cor, "placa": placa.upper(), "caracteristicas": caracteristicas}
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
        if opcoes_alvos:
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
                        up_coords = st.text_input("Localização (Lat, Lon)", value=f"{lat_a}, {lon_a}" if lat_a and lon_a else "")
                        up_tattoo = st.text_area("Tatuagens", value=dados_alvo.get('tatuagens_sinais') or "")
                        up_obs = st.text_area("Observações Gerais / Passagens", value=dados_alvo.get('observacoes') or "")
                        
                        foto_atual = dados_alvo.get('caminho_foto')
                        hash_atual = dados_alvo.get('foto_hash')
                        modo_foto = st.radio("Ação com Fotos:", ["Manter Atual", "Adicionar Novas Imagens", "Substituir / Atualizar Foto (Apaga a anterior)"], horizontal=True)
                        novas_fotos_up = st.file_uploader("Novas Imagens:", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

                        if st.form_submit_button("🔄 Salvar Alterações"):
                            try:
                                lat_nova, lon_nova = extrair_coordenadas(up_coords)
                                url_foto_final = foto_atual
                                hash_foto_final = hash_atual

                                if novas_fotos_up:
                                    urls_novas, hashes_novos = [], []
                                    for foto in novas_fotos_up:
                                        conteudo = foto.read()
                                        h = gerar_hash_foto(conteudo)
                                        if h: hashes_novos.append(h)
                                        ext = foto.name.split('.')[-1]
                                        nome_arq = f"alvos_{uuid.uuid4()}.{ext}"
                                        supabase.storage.from_('Fotos').upload(nome_arq, conteudo, {"content-type": foto.type})
                                        urls_novas.append(supabase.storage.from_('Fotos').get_public_url(nome_arq))
                                    
                                    str_novas = ", ".join(urls_novas)
                                    str_hashes_novos = ", ".join(hashes_novos)

                                    if modo_foto == "Substituir / Atualizar Foto (Apaga a anterior)":
                                        apagar_fotos_bucket(foto_atual)
                                        url_foto_final = str_novas
                                        hash_foto_final = str_hashes_novos
                                    elif modo_foto == "Adicionar Novas Imagens":
                                        url_foto_final = f"{foto_atual}, {str_novas}" if foto_atual else str_novas
                                        hash_foto_final = f"{hash_atual}, {str_hashes_novos}" if hash_atual else str_hashes_novos

                                supabase.table("dim_pessoas").update({
                                    "nome": up_nome, "vulgo": up_vulgo, "nome_mae": up_mae, "data_nascimento": up_nasc,
                                    "cpf": up_cpf, "endereco": up_endereco, "latitude": lat_nova, "longitude": lon_nova,
                                    "tatuagens_sinais": up_tattoo, "observacoes": up_obs, "caminho_foto": url_foto_final,
                                    "foto_hash": hash_foto_final
                                }).eq("id_pessoa", id_p).execute()
                                st.success("✅ Dados atualizados!")
                                st.rerun()
                            except Exception as e: st.error(f"Erro: {e}")
                    
                    if st.button("🗑️ EXCLUIR ALVO DEFINITIVAMENTE", type="primary"):
                        apagar_fotos_bucket(dados_alvo.get('caminho_foto'))
                        supabase.table("ponte_vinculos").delete().eq("id_pessoa", id_p).execute()
                        supabase.table("ponte_pessoas_veiculos").delete().eq("id_pessoa", id_p).execute()
                        supabase.table("dim_pessoas").delete().eq("id_pessoa", id_p).execute()
                        st.success("💀 Alvo erradicado.")
                        st.rerun()

    elif tabela_alvo == "🏠 Fatos":
        opcoes_fatos = list(dic_fatos.keys())
        if opcoes_fatos:
            fato_selecionado = st.selectbox("Selecione o evento para gerenciar:", [""] + opcoes_fatos)
            if fato_selecionado != "":
                id_f = dic_fatos[fato_selecionado]
                dados_fato = next((item for item in lista_fatos_bruta if item["id_evento"] == id_f), None)
                if dados_fato:
                    with st.form("form_upd_fato"):
                        st.markdown(f"**Editando Fato Registrado**")
                        up_tipo = st.text_input("Tipo Evento", value=dados_fato.get('tipo_evento') or "")
                        up_bairro = st.text_input("Bairro", value=dados_fato.get('bairro_setor') or "")
                        lat_f, lon_f = dados_fato.get('latitude') or "", dados_fato.get('longitude') or ""
                        up_coords_fato = st.text_input("Coordenadas (Lat, Lon)", value=f"{lat_f}, {lon_f}" if lat_f and lon_f else "")
                        up_resumo = st.text_area("Resumo", value=dados_fato.get('resumo_obs') or "")
                        
                        if st.form_submit_button("🔄 Salvar Alterações"):
                            lat_f_nova, lon_f_nova = extrair_coordenadas(up_coords_fato)
                            supabase.table("fato_eventos").update({
                                "tipo_evento": up_tipo, "bairro_setor": up_bairro, 
                                "latitude": lat_f_nova, "longitude": lon_f_nova, "resumo_obs": up_resumo
                            }).eq("id_evento", id_f).execute()
                            st.success("✅ Fato atualizado!")
                            st.rerun()
                    
                    if st.button("🗑️ EXCLUIR EVENTO DEFINITIVAMENTE", type="primary"):
                        apagar_fotos_bucket(dados_fato.get('caminho_foto'))
                        supabase.table("ponte_vinculos").delete().eq("id_evento", id_f).execute()
                        supabase.table("ponte_fatos_veiculos").delete().eq("id_evento", id_f).execute()
                        supabase.table("fato_eventos").delete().eq("id_evento", id_f).execute()
                        st.success("💀 Evento erradicado.")
                        st.rerun()

    elif tabela_alvo == "🚗 Veículos":
        opcoes_veiculos = list(dic_veiculos.keys())
        if opcoes_veiculos:
            veic_selecionado = st.selectbox("Selecione o veículo:", [""] + opcoes_veiculos)
            if veic_selecionado != "":
                id_v = dic_veiculos[veic_selecionado]
                dados_veic = next((item for item in lista_veiculos_bruta if item["id_veiculo"] == id_v), None)
                if dados_veic:
                    with st.form("form_upd_veic"):
                        up_tipo_v = st.text_input("Tipo/Modelo", value=dados_veic.get('tipo') or "")
                        up_cor_v = st.text_input("Cor", value=dados_veic.get('cor') or "")
                        up_placa_v = st.text_input("Placa", value=dados_veic.get('placa') or "")
                        up_carac_v = st.text_area("Características", value=dados_veic.get('caracteristicas') or "")
                        
                        if st.form_submit_button("🔄 Salvar Alterações"):
                            supabase.table("dim_veiculos").update({
                                "tipo": up_tipo_v, "cor": up_cor_v, "placa": up_placa_v.upper(), "caracteristicas": up_carac_v
                            }).eq("id_veiculo", id_v).execute()
                            st.success("✅ Veículo atualizado!")
                            st.rerun()

                    if st.button("🗑️ EXCLUIR VEÍCULO DEFINITIVAMENTE", type="primary"):
                        supabase.table("ponte_pessoas_veiculos").delete().eq("id_veiculo", id_v).execute()
                        supabase.table("ponte_fatos_veiculos").delete().eq("id_veiculo", id_v).execute()
                        supabase.table("dim_veiculos").delete().eq("id_veiculo", id_v).execute()
                        st.success("💀 Veículo erradicado.")
                        st.rerun()

# ==========================================
# 👁️ FUNÇÃO AUXILIAR ORB PARA LOCAIS/FATOS
# ==========================================
def calcular_matches_orb_local(bytes_img1, bytes_img2, max_features=1000, limiar_distancia=45):
    try:
        nparr1 = np.frombuffer(bytes_img1, np.uint8)
        nparr2 = np.frombuffer(bytes_img2, np.uint8)
        img1 = cv2.imdecode(nparr1, cv2.IMREAD_GRAYSCALE)
        img2 = cv2.imdecode(nparr2, cv2.IMREAD_GRAYSCALE)

        if img1 is None or img2 is None: return 0

        h1, w1 = img1.shape[:2]
        if max(h1, w1) > 600:
            escala = 600.0 / max(h1, w1)
            img1 = cv2.resize(img1, (int(w1 * escala), int(h1 * escala)))

        h2, w2 = img2.shape[:2]
        if max(h2, w2) > 600:
            escala = 600.0 / max(h2, w2)
            img2 = cv2.resize(img2, (int(w2 * escala), int(h2 * escala)))

        orb = cv2.ORB_create(nfeatures=max_features)
        kp1, des1 = orb.detectAndCompute(img1, None)
        kp2, des2 = orb.detectAndCompute(img2, None)

        if des1 is None or des2 is None or len(des1) == 0 or len(des2) == 0:
            return 0

        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)
        pontos_bons = [m for m in matches if m.distance <= limiar_distancia]
        return len(pontos_bons)
    except:
        return 0

# ----------------- ABA 5: RECONHECIMENTO FACIAL E BUSCA DE FATOS/LOCAIS -----------------
with aba_busca_visual:
    st.markdown("### 📸 Inteligência Visual Híbrida (Indivíduos & Fatos/Locais)")
    st.caption("O motor biométrico cruza feições faciais de pessoas, enquanto o motor geométrico (ORB) reconhece fachadas, quiosques, veículos e locais de interesse.")

    tipo_captura = st.radio("Origem da Imagem:", ["📁 Carregar Arquivo (Galeria/WhatsApp)", "📷 Tirar Foto Agora (Câmera)"], horizontal=True)
    
    arquivo_analise = None
    if tipo_captura == "📁 Carregar Arquivo (Galeria/WhatsApp)":
        arquivo_analise = st.file_uploader("Selecione a imagem para cruzamento:", type=["jpg", "jpeg", "png"], key="upload_facial_fato")
    else:
        arquivo_analise = st.camera_input("Enquadre o indivíduo ou o local de interesse:")

    if arquivo_analise is not None:
        col_img1, col_img2 = st.columns([1, 2])
        with col_img1:
            st.image(arquivo_analise, caption="Foto para Varredura", use_container_width=True)
            
        with col_img2:
            st.info("ℹ️ A varredura analisará biometria facial e padrões geométricos de pontos físicos.")
            botao_varrer = st.button("🚀 Iniciar Varredura de Inteligência", type="primary", use_container_width=True)

        if botao_varrer:
            with st.spinner("🔍 Analisando biometria e estrutura de locais na base de dados..."):
                try:
                    bytes_entrada = arquivo_analise.getvalue()
                    
                    # 1. PROCESSAMENTO FACIAL (INDIVÍDUOS)
                    img_entrada = face_recognition.load_image_file(io.BytesIO(bytes_entrada))
                    encodings_entrada = face_recognition.face_encodings(img_entrada)

                    alvo_pessoa_match = None
                    menor_dist_facial = 1.0
                    url_match_foto = ""

                    if len(encodings_entrada) > 0:
                        encoding_alvo = encodings_entrada[0]
                        alvos_com_foto = [p for p in lista_alvos_bruta if p.get('caminho_foto')]
                        
                        prog_facial = st.progress(0, text="Processando biometria facial de alvos...")
                        total_alvos = len(alvos_com_foto) if alvos_com_foto else 1

                        for idx, p in enumerate(alvos_com_foto):
                            urls = [u.strip() for u in p['caminho_foto'].split(',') if u.strip()]
                            for url in urls:
                                try:
                                    resp = requests.get(url, timeout=4)
                                    if resp.status_code == 200:
                                        img_banco = face_recognition.load_image_file(io.BytesIO(resp.content))
                                        enc_banco = face_recognition.face_encodings(img_banco)
                                        if enc_banco:
                                            dist = face_recognition.face_distance([enc_banco[0]], encoding_alvo)[0]
                                            if dist < menor_dist_facial:
                                                menor_dist_facial = dist
                                                alvo_pessoa_match = p
                                                url_match_foto = url
                                except: pass
                            prog_facial.progress((idx + 1) / total_alvos)
                        prog_facial.empty()

                    # 2. PROCESSAMENTO GEOMÉTRICO ORB (FATOS / LOCAIS / PONTOS)
                    fato_local_match = None
                    max_matches_orb = 0
                    url_match_fato = ""

                    fatos_com_foto = [f for f in lista_fatos_bruta if f.get('caminho_foto')]
                    if fatos_com_foto:
                        prog_local = st.progress(0, text="Varrendo padrões estruturais de Fatos/Locais...")
                        total_fatos = len(fatos_com_foto)
                        for idx, f in enumerate(fatos_com_foto):
                            urls_f = [u.strip() for u in f['caminho_foto'].split(',') if u.strip()]
                            for u_f in urls_f:
                                try:
                                    resp_f = requests.get(u_f, timeout=4)
                                    if resp_f.status_code == 200:
                                        qtd_pts = calcular_matches_orb_local(bytes_entrada, resp_f.content)
                                        if qtd_pts > max_matches_orb:
                                            max_matches_orb = qtd_pts
                                            fato_local_match = f
                                            url_match_fato = u_f
                                except: pass
                            prog_local.progress((idx + 1) / total_fatos)
                        prog_local.empty()

                    # ========================================================
                    # EXIBIÇÃO DE RESULTADOS: CASO 1 - INDIVÍDUO IDENTIFICADO
                    # ========================================================
                    if alvo_pessoa_match and menor_dist_facial <= 0.60:
                        precisao = round((1 - menor_dist_facial) * 100, 1)
                        st.success(f"🎯 **INDIVÍDUO IDENTIFICADO COM SUCESSO! ({precisao}% de Precisão Biométrica)**")

                        mp_obs = checar_mandado_ativo(alvo_pessoa_match['id_pessoa'])
                        if mp_obs:
                            st.error(f"🚨 **ALERTA CRÍTICO: MANDADO DE PRISÃO ATIVO!**\n\nDetalhes: _{mp_obs}_")

                        st.markdown("---")
                        st.markdown("### 📋 Ficha de Qualificação Integral")
                        c_card_foto, c_card_dados = st.columns([1, 2])
                        with c_card_foto:
                            st.image(url_match_foto, caption=f"Registro: {alvo_pessoa_match.get('nome')}", use_container_width=True)

                        with c_card_dados:
                            st.markdown(f"**Nome:** `{alvo_pessoa_match.get('nome')}`")
                            st.markdown(f"**Vulgo:** `{alvo_pessoa_match.get('vulgo') or 'N/D'}`")
                            st.markdown(f"**CPF:** `{alvo_pessoa_match.get('cpf') or 'N/D'}`")
                            st.markdown(f"**Data de Nascimento:** `{alvo_pessoa_match.get('data_nascimento') or 'N/D'}`")
                            st.markdown(f"**Nome da Mãe:** `{alvo_pessoa_match.get('nome_mae') or 'N/D'}`")
                            st.markdown(f"**Endereço:** `{alvo_pessoa_match.get('endereco') or 'N/D'}`")
                            
                            lat_m, lon_m = alvo_pessoa_match.get('latitude'), alvo_pessoa_match.get('longitude')
                            if lat_m and lon_m:
                                st.markdown(f"📍 [Ver Residência no Google Maps](https://maps.google.com/?q={lat_m},{lon_m})")

                            if alvo_pessoa_match.get('tatuagens_sinais'):
                                st.markdown(f"**Tatuagens / Sinais:** _{alvo_pessoa_match.get('tatuagens_sinais')}_")
                            if alvo_pessoa_match.get('observacoes'):
                                st.markdown(f"**Passagens / Obs:** _{alvo_pessoa_match.get('observacoes')}_")

                        # VEÍCULOS VINCULADOS AO INDIVÍDUO
                        st.markdown("#### 🚗 Veículos Vinculados ao Indivíduo")
                        try:
                            l_veics = supabase.table("ponte_pessoas_veiculos").select("id_veiculo").eq("id_pessoa", alvo_pessoa_match['id_pessoa']).execute()
                            ids_v = [l['id_veiculo'] for l in (l_veics.data or [])]
                            if ids_v:
                                for vid in ids_v:
                                    vd = supabase.table("dim_veiculos").select("*").eq("id_veiculo", vid).execute().data[0]
                                    st.markdown(f"• **{vd.get('placa')}** | {vd.get('cor')} {vd.get('tipo')} - _{vd.get('caracteristicas') or 'Sem detalhes'}_")
                            else:
                                st.caption("Nenhum veículo vinculado a este indivíduo.")
                        except: pass

                        # VÍNCULOS TOTAIS DA ABA FATOS / LOCAIS
                        st.markdown("#### 🏠 Relação Completa de Fatos & Locais Vinculados")
                        try:
                            l_fatos = supabase.table("ponte_vinculos").select("id_evento").eq("id_pessoa", alvo_pessoa_match['id_pessoa']).execute()
                            ids_ev = [l['id_evento'] for l in (l_fatos.data or [])]
                            if ids_ev:
                                for id_e in ids_ev:
                                    fd = supabase.table("fato_eventos").select("*").eq("id_evento", id_e).execute().data[0]
                                    dt = fd.get('data_hora')[:10] if fd.get('data_hora') else 'Data N/D'
                                    tipo_ev = fd.get('tipo_evento', '')
                                    
                                    # Ícone tático por gravidade
                                    icone = "🚨" if tipo_ev == "MP ATIVO" else ("💣" if tipo_ev == "Casa bomba" else ("🔫" if tipo_ev == "Indivíduo Armado" else "📍"))
                                    
                                    with st.expander(f"{icone} {tipo_ev} ({dt}) - Bairro: {fd.get('bairro_setor')}", expanded=True):
                                        col_f1, col_f2 = st.columns([1, 2])
                                        with col_f1:
                                            if fd.get('caminho_foto'):
                                                foto_fato_url = fd.get('caminho_foto').split(',')[0].strip()
                                                st.image(foto_fato_url, caption=f"Foto do Local/Fato", use_container_width=True)
                                            else:
                                                st.caption("Sem foto anexada a este fato.")
                                        
                                        with col_f2:
                                            st.markdown(f"**Tipo de Registro:** `{tipo_ev}`")
                                            st.markdown(f"**Data da Ocorrência:** `{dt}`")
                                            st.markdown(f"**Bairro / Setor:** `{fd.get('bairro_setor') or 'N/D'}`")
                                            if fd.get('resumo_obs'):
                                                st.markdown(f"**Relato da Guarnição:**\n\n_{fd.get('resumo_obs')}_")
                                            
                                            lat_ev, lon_ev = fd.get('latitude'), fd.get('longitude')
                                            if lat_ev and lon_ev:
                                                st.markdown(f"🗺️ [Abrir Coordenadas do Fato no Maps](https://maps.google.com/?q={lat_ev},{lon_ev})")
                                            
                                            # Comparsas e Veículos vinculados a este mesmo fato
                                            l_outros = supabase.table("ponte_vinculos").select("id_pessoa").eq("id_evento", id_e).execute()
                                            ids_outros = [o['id_pessoa'] for o in (l_outros.data or []) if o['id_pessoa'] != alvo_pessoa_match['id_pessoa']]
                                            if ids_outros:
                                                nomes_comp = []
                                                for opid in ids_outros:
                                                    op_data = supabase.table("dim_pessoas").select("nome, vulgo").eq("id_pessoa", opid).execute()
                                                    if op_data.data:
                                                        nomes_comp.append(f"{op_data.data[0]['nome']} (Vulgo: {op_data.data[0].get('vulgo','N/D')})")
                                                st.markdown(f"👥 **Comparsas/Outros Alvos Ligados:** {', '.join(nomes_comp)}")
                            else:
                                st.caption("Nenhum fato ou local registrado para este alvo.")
                        except Exception as e:
                            st.caption(f"Erro ao listar fatos vinculados: {e}")

                    # ========================================================
                    # EXIBIÇÃO DE RESULTADOS: CASO 2 - LOCAL/FATO IDENTIFICADO
                    # ========================================================
                    elif fato_local_match and max_matches_orb >= 20:
                        st.success(f"🏠 **LOCAL/FATO RECONHECIDO (ORB)! ({max_matches_orb} pontos geométricos coincidentes)**")
                        
                        st.markdown("---")
                        st.markdown("### 📍 Detalhes do Fato / Ponto de Interesse")
                        c_loc_foto, c_loc_dados = st.columns([1, 2])
                        with c_loc_foto:
                            st.image(url_match_fato, caption=f"Registro do Local", use_container_width=True)
                            
                        with c_loc_dados:
                            tipo_f = fato_local_match.get('tipo_evento', '')
                            dt_f = fato_local_match.get('data_hora')[:10] if fato_local_match.get('data_hora') else 'Data N/D'
                            st.markdown(f"**Tipo de Evento:** `{tipo_f}`")
                            st.markdown(f"**Data:** `{dt_f}` | **Setor:** `{fato_local_match.get('bairro_setor')}`")
                            
                            if fato_local_match.get('resumo_obs'):
                                st.markdown(f"**Histórico/Observações:**\n\n_{fato_local_match.get('resumo_obs')}_")
                                
                            lat_fl, lon_fl = fato_local_match.get('latitude'), fato_local_match.get('longitude')
                            if lat_fl and lon_fl:
                                st.markdown(f"🗺️ [Abrir Ponto Exato no Google Maps](https://maps.google.com/?q={lat_fl},{lon_fl})")

                        # INDIVÍDUOS FREQUENTADORES / VINCULADOS A ESTE LOCAL
                        st.markdown("#### 👥 Indivíduos Vinculados a este Local")
                        try:
                            l_p_fato = supabase.table("ponte_vinculos").select("id_pessoa").eq("id_evento", fato_local_match['id_evento']).execute()
                            ids_pf = [lp['id_pessoa'] for lp in (l_p_fato.data or [])]
                            if ids_pf:
                                for pid in ids_pf:
                                    pd = supabase.table("dim_pessoas").select("*").eq("id_pessoa", pid).execute().data[0]
                                    mp = checar_mandado_ativo(pid)
                                    alerta_mp = "🚨 **MP ATIVO** " if mp else ""
                                    st.markdown(f"• {alerta_mp}**{pd.get('nome')}** (Vulgo: _{pd.get('vulgo') or 'N/D'}_) | CPF: `{pd.get('cpf') or 'N/D'}`")
                            else:
                                st.caption("Nenhum indivíduo vinculado diretamente a este fato.")
                        except: pass

                        # VEÍCULOS VINCULADOS AO LOCAL
                        st.markdown("#### 🚗 Veículos Vinculados a este Local")
                        try:
                            l_v_fato = supabase.table("ponte_fatos_veiculos").select("id_veiculo").eq("id_evento", fato_local_match['id_evento']).execute()
                            ids_vf = [lv['id_veiculo'] for lv in (l_v_fato.data or [])]
                            if ids_vf:
                                for vid in ids_vf:
                                    vd = supabase.table("dim_veiculos").select("*").eq("id_veiculo", vid).execute().data[0]
                                    st.markdown(f"• **{vd.get('placa')}** | {vd.get('cor')} {vd.get('tipo')} - _{vd.get('caracteristicas') or 'Sem obs'}_")
                            else:
                                st.caption("Nenhum veículo vinculado a este fato.")
                        except: pass

                    else:
                        st.warning(f"❌ Nenhuma compatibilidade facial confirmada (Menor distância: {round(menor_dist_facial, 2)}) e nenhum ponto físico coincidente (Máx ORB: {max_matches_orb}).")

                except Exception as e:
                    st.error(f"Erro durante a varredura visual: {e}")
