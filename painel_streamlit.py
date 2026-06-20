import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import time
from datetime import datetime

try:
    import agente_almoxweb 
    robo_disponivel = True
except ModuleNotFoundError:
    robo_disponivel = False

# ==========================================
# 🎨 CONFIGURAÇÕES DE PÁGINA E CSS
# ==========================================
st.set_page_config(page_title="Portal Logístico WEG", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
        .stApp { background-color: #f4f6f9; }
        h1, h2, h3 { color: #00579D !important; font-family: 'Segoe UI', sans-serif; }
        div.stButton > button:first-child { background-color: #00579D; color: white; border-radius: 4px; border: none; font-weight: bold; width: 100%; }
        div.stButton > button:first-child:hover { background-color: #003A6B; transform: scale(1.02); }
        .kpi-card { background: white; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 0px 4px 10px rgba(0,0,0,0.05); }
        .kpi-valor { font-size: 36px; font-weight: bold; margin-bottom: 5px; }
        .kpi-titulo { font-size: 14px; color: #666; font-weight: bold; text-transform: uppercase; }
        .kpi-azul .kpi-valor { color: #00579D; } .kpi-verde .kpi-valor { color: #2e7d32; }
        .kpi-amarelo .kpi-valor { color: #f57c00; } .kpi-vermelho .kpi-valor { color: #d32f2f; }
        .kpi-vermelho { border-bottom: 4px solid #d32f2f; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 1. CONEXÃO COM O BANCO DE DADOS
# ==========================================
DATABASE_URL = st.secrets["banco_dados"]["url"]
engine = create_engine(DATABASE_URL)

if "db_verificado" not in st.session_state:
    with engine.connect() as conn:
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS expedicao_completa (
                id SERIAL PRIMARY KEY, item TEXT, material TEXT, descricao TEXT, 
                centro_dep TEXT, tipo_estoque TEXT, lote TEXT, tp TEXT, 
                posicao_dep TEXT, estoque REAL, data_em TEXT, data_necess TEXT, 
                nfe TEXT, fornecedor TEXT, status_envio TEXT DEFAULT 'Pendente' 
            )
        '''))
        conn.execute(text("CREATE TABLE IF NOT EXISTS usuarios (usuario TEXT PRIMARY KEY, senha TEXT, perfil TEXT)"))
        conn.commit()

        if conn.execute(text("SELECT COUNT(*) FROM usuarios")).scalar() == 0:
            conn.execute(text("INSERT INTO usuarios (usuario, senha, perfil) VALUES ('roberto', 'weg2026', 'Admin')"))
            conn.execute(text("INSERT INTO usuarios (usuario, senha, perfil) VALUES ('expedicao', 'senha123', 'Operador')"))
            conn.commit()
    st.session_state["db_verificado"] = True

# ==========================================
# 2. LOGIN SEGURO E MEMÓRIA DO CARRINHO
# ==========================================
if "logado" not in st.session_state:
    st.session_state["logado"] = False
    st.session_state["usuario_atual"] = ""
    st.session_state["perfil_atual"] = ""

if "carrinho_expedicao" not in st.session_state:
    st.session_state["carrinho_expedicao"] = []

if not st.session_state["logado"]:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/WEG_logo.svg/1200px-WEG_logo.svg.png", width=150)
        st.markdown("## Portal de Logística SAD 320")
        with st.form("form_login"):
            usuario_input = st.text_input("Usuário").lower().strip()
            senha_input = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar no Sistema"):
                with engine.connect() as conn:
                    resultado = conn.execute(text("SELECT senha, perfil FROM usuarios WHERE usuario = :u"), {"u": usuario_input}).fetchone()
                if resultado and resultado[0] == senha_input:
                    st.session_state["logado"] = True
                    st.session_state["usuario_atual"] = usuario_input
                    st.session_state["perfil_atual"] = resultado[1]
                    st.rerun()
                else:
                    st.error("Credenciais inválidas.")
    st.stop()

# ==========================================
# 3. MENU LATERAL E ROBÔ
# ==========================================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/WEG_logo.svg/1200px-WEG_logo.svg.png", width=100)
st.sidebar.markdown(f"👨‍💻 Logado: **{st.session_state['usuario_atual'].upper()}**")
st.sidebar.markdown(f"🛡️ Nível: **{st.session_state['perfil_atual']}**")

if st.sidebar.button("🚪 Sair do Sistema"):
    st.session_state.clear()
    st.rerun()

st.sidebar.divider()

# FUNÇÃO PARA LIMPAR O ".0" DOS NÚMEROS DO PANDAS
def limpar_numero_sap(valor):
    v = str(valor).strip()
    if v.endswith('.0'): return v[:-2]
    if v == 'nan' or v == 'None': return ''
    return v

if st.session_state["perfil_atual"] == "Admin":
    st.sidebar.markdown("### 🤖 Robô Sincronizador")
    if robo_disponivel:
        if st.sidebar.button("⚡ Sincronizar com SAP"):
            with st.spinner("Extraindo e comparando dados..."):
                dados_novos = agente_almoxweb.extrair_dados_almoxweb()
                if dados_novos:
                    df_robo = pd.DataFrame(dados_novos)
                    df_pb = pd.DataFrame()
                    
                    # Aplica a limpeza do ".0"
                    df_pb['item'] = df_robo.get('Item', '').apply(limpar_numero_sap)
                    df_pb['material'] = df_robo.get('Material', '').apply(limpar_numero_sap)
                    df_pb['descricao'] = df_robo.get('Descricao', df_robo.get('Descrição', ''))
                    df_pb['centro_dep'] = df_robo.get('Centro_Dep', df_robo.get('Centro | Dep.', '')).apply(limpar_numero_sap)
                    df_pb['tipo_estoque'] = df_robo.get('TipoEstoq.', df_robo.get('TipoEstoq', 'Livre'))
                    df_pb['lote'] = df_robo.get('Lote', '').apply(limpar_numero_sap)
                    df_pb['tp'] = df_robo.get('Tp.', df_robo.get('Tp', '')).apply(limpar_numero_sap)
                    df_pb['posicao_dep'] = df_robo.get('Posicao', df_robo.get('Posição Dep.', '')).apply(limpar_numero_sap)
                    df_pb['nfe'] = df_robo.get('NF', df_robo.get('NFE', '')).apply(limpar_numero_sap)
                    
                    df_pb['estoque'] = df_robo.get('Quantidade', df_robo.get('Estoque', 0))
                    df_pb['estoque'] = df_pb['estoque'].astype(str).str.replace(r'[^\d.,]', '', regex=True).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
                    df_pb['estoque'] = pd.to_numeric(df_pb['estoque'], errors='coerce').fillna(0.0)
                    
                    df_pb['data_em'] = df_robo.get('Data_Entrada', df_robo.get('Data EM', ''))
                    df_pb['data_necess'] = df_robo.get('Data_Necess', df_robo.get('Data Necess.', ''))
                    df_pb['fornecedor'] = df_robo.get('Fornecedor', '')

                    # Sincronização Inteligente
                    df_pb['chave_comparacao'] = df_pb['material'] + "|" + df_pb['nfe'] + "|" + df_pb['posicao_dep']
                    
                    query_banco = "SELECT id, status_envio, COALESCE(material, '') || '|' || COALESCE(nfe, '') || '|' || COALESCE(posicao_dep, '') as chave_banco FROM expedicao_completa"
                    df_banco = pd.read_sql_query(query_banco, engine)
                    
                    chaves_no_banco = set(df_banco['chave_banco'])
                    chaves_pendentes_banco = set(df_banco[df_banco['status_envio'] == 'Pendente']['chave_banco'])
                    chaves_do_sap = set(df_pb['chave_comparacao'])

                    df_inserir = df_pb[~df_pb['chave_comparacao'].isin(chaves_no_banco)].copy()
                    df_inserir = df_inserir.drop(columns=['chave_comparacao'])
                    chaves_sumiram = chaves_pendentes_banco - chaves_do_sap

                    if not df_inserir.empty:
                        df_inserir.to_sql(name='expedicao_completa', con=engine, if_exists='append', index=False)
                    
                    if chaves_sumiram:
                        with engine.connect() as conn:
                            for chave in chaves_sumiram:
                                conn.execute(text("UPDATE expedicao_completa SET status_envio = 'Baixado Direto no SAP' WHERE status_envio = 'Pendente' AND COALESCE(material, '') || '|' || COALESCE(nfe, '') || '|' || COALESCE(posicao_dep, '') = :c"), {"c": chave})
                            conn.commit()

                    st.sidebar.success(f"✅ Sincronizado! \n{len(df_inserir)} novos.\n{len(chaves_sumiram)} baixados.")
                    time.sleep(3)
                    st.rerun()

# ==========================================
# 4. MOTOR DE CÁLCULO DE SLA
# ==========================================
def calcular_sla_pandas(df):
    if df.empty: 
        df['SLA'] = []
        return df
    df['data_real'] = pd.to_datetime(df['data_em'], format='mixed', dayfirst=True, errors='coerce')
    hoje = pd.Timestamp(datetime.now().date())
    df['dias_parado'] = (hoje - df['data_real']).dt.days.fillna(0).astype(int)
    
    def classificar_regra(row):
        tipo = str(row['tipo_estoque']).upper()
        if 'Q' in tipo or 'CQ' in tipo: return "🟣 BLOQ. QUALIDADE"
        if row['dias_parado'] > 7: return "🔴 URGENTE (>7d)"
        elif row['dias_parado'] > 3: return "🟡 ATENÇÃO (>3d)"
        else: return "🟢 NO PRAZO"
    df['SLA'] = df.apply(classificar_regra, axis=1)
    
    # Removemos a data real pra não sujar a tabela final
    return df.drop(columns=['data_real', 'dias_parado'])

# ==========================================
# 5. TELA PRINCIPAL E ABAS
# ==========================================
col_topo1, col_topo2 = st.columns([3, 1])
with col_topo1: st.markdown("<h1>📊 Hub Logístico Central</h1>", unsafe_allow_html=True)

query_bruta = "SELECT * FROM expedicao_completa WHERE status_envio = 'Pendente'"
df_bruto = pd.read_sql_query(query_bruta, engine)
df_bruto = calcular_sla_pandas(df_bruto)

# DASHBOARD DE TOPO
if not df_bruto.empty:
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div class='kpi-card kpi-azul'><div class='kpi-titulo'>Total Pendente</div><div class='kpi-valor'>{len(df_bruto)}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='kpi-card kpi-verde'><div class='kpi-titulo'>No Prazo (≤ 3 dias)</div><div class='kpi-valor'>{len(df_bruto[df_bruto['SLA'] == '🟢 NO PRAZO'])}</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='kpi-card kpi-amarelo'><div class='kpi-titulo'>Atenção (> 3 dias)</div><div class='kpi-valor'>{len(df_bruto[df_bruto['SLA'] == '🟡 ATENÇÃO (>3d)'])}</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='kpi-card kpi-vermelho'><div class='kpi-titulo'>Crítico (> 7 dias)</div><div class='kpi-valor'>{len(df_bruto[df_bruto['SLA'] == '🔴 URGENTE (>7d)'])}</div></div>", unsafe_allow_html=True)
    st.write("")

# CRIAÇÃO DAS 4 ABAS ESTRATÉGICAS
aba_expedicao, aba_recebedor, aba_historico, aba_admin = st.tabs([
    "📋 1. EXPEDIÇÃO (Despachar)", 
    "📦 2. RECEBIMENTO (Doca)", 
    "💾 3. HISTÓRICO GERAL", 
    "⚙️ 4. ADMINISTRAÇÃO"
])

# ------------------------------------------
# ABA 1: EXPEDIÇÃO (A TABELA COM CHECKBOX E BUSCA GLOBAL)
# ------------------------------------------
with aba_expedicao:
    
    st.markdown("##### 🔍 Montagem de Carga")
    col_b1, col_b2 = st.columns([3, 1])
    busca_global = col_b1.text_input("🔎 Pesquise rapidamente por NF, Material, Fornecedor ou Posição:", placeholder="Ex: NF-1234, SKF, 1000456...")
    filtro_sla = col_b2.selectbox("Focar Operação:", ["Mostrar Todos", "🔴 URGENTE (>7d)", "🟡 ATENÇÃO (>3d)", "🟣 BLOQ. QUALIDADE"])
    st.divider()

    if df_bruto.empty:
        st.success("Tudo limpo! Nenhum material pendente para despachar.")
    else:
        df_tela = df_bruto.copy()
        
        if filtro_sla != "Mostrar Todos": df_tela = df_tela[df_tela['SLA'] == filtro_sla]

        if busca_global:
            mask = df_tela.astype(str).apply(lambda x: x.str.contains(busca_global, case=False, na=False)).any(axis=1)
            df_tela = df_tela[mask]

        if df_tela.empty:
            st.warning("Nenhum material encontrado com os filtros atuais.")
        else:
            # Organiza a ordem das colunas para ficar bonito
            colunas_visiveis = ['id', 'SLA', 'material', 'descricao', 'estoque', 'posicao_dep', 'nfe', 'fornecedor', 'data_em']
            df_tela = df_tela[colunas_visiveis]
            
            # Insere o Checkbox
            df_tela.insert(0, "Selecionar", df_tela['id'].isin(st.session_state["carrinho_expedicao"]))
            
            # Trava edição nas outras colunas
            df_editado = st.data_editor(
                df_tela, hide_index=True, use_container_width=True, height=400,
                disabled=colunas_visiveis,
                column_config={"SLA": st.column_config.TextColumn("Status SLA", width="medium")}
            )
            
            # Salva na Memória do Carrinho
            for index, row in df_editado.iterrows():
                id_linha = row['id']
                if row['Selecionar'] and id_linha not in st.session_state["carrinho_expedicao"]:
                    st.session_state["carrinho_expedicao"].append(id_linha)
                elif not row['Selecionar'] and id_linha in st.session_state["carrinho_expedicao"]:
                    st.session_state["carrinho_expedicao"].remove(id_linha)

            # Botão de Despacho
            qtd_carrinho = len(st.session_state["carrinho_expedicao"])
            col_btn1, col_btn2 = st.columns([2, 1])
            with col_btn1: st.info(f"🛒 **Carrinho de Despacho:** {qtd_carrinho} itens marcados.")
            with col_btn2:
                if st.button("🚚 Despachar Carga do Carrinho", type="primary", use_container_width=True):
                    if qtd_carrinho == 0: st.error("Carrinho vazio!")
                    else:
                        with engine.connect() as conn:
                            for id_peca in st.session_state["carrinho_expedicao"]:
                                conn.execute(text("UPDATE expedicao_completa SET status_envio = 'Despachado' WHERE id = :id_peca"), {"id_peca": int(id_peca)})
                            conn.commit()
                        st.session_state["carrinho_expedicao"] = []
                        st.success("✅ Carga Despachada para a Doca de Recebimento!")
                        time.sleep(1.5)
                        st.rerun()

# ------------------------------------------
# ABA 2: RECEBIMENTO (A DOCA)
# ------------------------------------------
with aba_recebedor:
    st.markdown("### 📦 Painel do Recebedor (Em Trânsito)")
    st.write("Materiais que a expedição despachou e estão aguardando conferência física na doca.")
    
    query_rec = "SELECT id, material, descricao, estoque, nfe, fornecedor, status_envio FROM expedicao_completa WHERE status_envio = 'Despachado'"
    df_rec = pd.read_sql_query(query_rec, engine)
    
    if df_rec.empty:
        st.success("Nenhuma carga em trânsito no momento.")
    else:
        df_rec.insert(0, "Chegou_Fisico", False)
        
        df_editado_rec = st.data_editor(
            df_rec, hide_index=True, use_container_width=True, height=300,
            disabled=["id", "material", "descricao", "estoque", "nfe", "fornecedor", "status_envio"]
        )
        
        selecionados_rec = df_editado_rec[df_editado_rec["Chegou_Fisico"] == True]
        
        if st.button("✅ Confirmar Recebimento Físico", type="primary"):
            if selecionados_rec.empty:
                st.error("Marque as caixinhas dos materiais que você conferiu!")
            else:
                with engine.connect() as conn:
                    for id_peca in selecionados_rec["id"]:
                        conn.execute(text("UPDATE expedicao_completa SET status_envio = 'Recebido' WHERE id = :id_peca"), {"id_peca": int(id_peca)})
                    conn.commit()
                st.success("Baixa realizada! Material encerrado.")
                time.sleep(1.5)
                st.rerun()

# ------------------------------------------
# ABA 3: HISTÓRICO GERAL
# ------------------------------------------
with aba_historico:
    st.markdown("### 💾 Base de Dados Histórica")
    query_hist = "SELECT id, material, descricao, estoque, nfe, status_envio FROM expedicao_completa WHERE status_envio != 'Pendente' ORDER BY id DESC"
    df_hist = pd.read_sql_query(query_hist, engine)
    
    if df_hist.empty: st.info("Nenhum material movimentado.")
    else: st.dataframe(df_hist, hide_index=True, use_container_width=True)

# ------------------------------------------
# ABA 4: ADMINISTRAÇÃO (SÓ PARA ADMIN)
# ------------------------------------------
with aba_admin:
    if st.session_state["perfil_atual"] != "Admin":
        st.error("⛔ Acesso Restrito aos Administradores do Sistema.")
    else:
        st.markdown("### ⚙️ Painel de Controle de TI")
        st.warning("Área de Risco: Ações aqui afetam o banco de dados oficial.")
        
        if st.button("🔄 Resetar Status de Todos os Materiais (Devolver para Pendente)"):
            with engine.connect() as conn:
                conn.execute(text("UPDATE expedicao_completa SET status_envio = 'Pendente'"))
                conn.commit()
            st.session_state["carrinho_expedicao"] = []
            st.success("Banco resetado com sucesso!")
            time.sleep(1)
            st.rerun()
            
        if st.button("🗑️ Apagar Banco de Dados Inteiro (Zerar Tudo)"):
            with engine.connect() as conn:
                conn.execute(text("DELETE FROM expedicao_completa"))
                conn.commit()
            st.session_state["carrinho_expedicao"] = []
            st.success("Tabela apagada!")
            time.sleep(1)
            st.rerun()
