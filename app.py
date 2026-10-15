import streamlit as st

# Configurações iniciais da aba do navegador
st.set_page_config(page_title="Tático Intel", page_icon="🛡️", layout="centered")

# ==========================================
# BARREIRA DE SEGURANÇA (AUTENTICAÇÃO)
# ==========================================
def check_password():
    """Retorna True se o utilizador inserir a senha correta."""
    
    def password_entered():
        # st.secrets é o "cofre" da nuvem onde guardaremos a senha real
        if st.session_state["password"] == st.secrets["SENHA_ACESSO"]:
            st.session_state["password_correct"] = True
            # Apaga a senha digitada da memória para evitar roubo de sessão
            del st.session_state["password"] 
        else:
            st.session_state["password_correct"] = False

    # Se já estiver autenticado na sessão, passa direto
    if st.session_state.get("password_correct", False):
        return True

    # Tela de Login
    st.markdown("### 🔒 Acesso Restrito")
    st.text_input(
        "Insira a Senha de Acesso Táti", 
        type="password", 
        on_change=password_entered, 
        key="password"
    )
    
    if "password_correct" in st.session_state:
        st.error("❌ Senha incorreta. Acesso negado.")
    return False

# Se a senha não estiver correta, o comando st.stop() bloqueia tudo o que estiver abaixo.
if not check_password():
    st.stop()

# ==========================================
# ÁREA RESTRITA (O SEU PAINEL DE INTELIGÊNCIA)
# ==========================================
st.title("🛡️ Sistema de Inteligência Tática")
st.write("✅ Acesso autorizado. Bem-vindo, Sargento.")
st.info("A ligação com o banco de dados Supabase e o formulário de cadastro de alvos serão inseridos aqui no próximo passo.")
