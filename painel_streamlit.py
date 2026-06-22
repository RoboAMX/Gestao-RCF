import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import datetime

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA (Sempre a primeira linha)
# ==========================================
st.set_page_config(page_title="Gestão à Vista - Almoxarifado", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 2. CSS CUSTOMIZADO (Layout Fixo e Sem Rolagem)
# ==========================================
# Este CSS remove os espaços em branco extras e oculta a barra de rolagem da tela principal
st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 0rem;
            padding-left: 1rem;
            padding-right: 1rem;
            max-height: 100vh;
            overflow-y: hidden; /* Remove a rolagem vertical */
        }
        /* Estilização para os cartões na barra lateral */
        .kpi-card {
            background-color: #f8f9fa;
            border-left: 5px solid;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 10px;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
        }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. ATUALIZAÇÃO AUTOMÁTICA (10 Minutos)
# ==========================================
# 10 minutos = 600.000 milissegundos
# Isso forçará o Streamlit a rodar o script novamente, consultando o banco atualizado.
st_autorefresh(interval=600000, limit=None, key="data_refresh_10min")

# ==========================================
# 4. FUNÇÕES DE CONSULTA AO BANCO DE DADOS
# ==========================================
# Aqui você colocará sua lógica real de SQL/Banco de dados.
# Como o script recarrega a cada 10 min, estas funções puxarão dados frescos.
@st.cache_data(ttl=600) # Cache expira em 10 min
def buscar_dados_banco():
    # SIMULAÇÃO DA CONSULTA AO BANCO DE DADOS
    return {
        "total_recebimento": 305,
        "prazo": 51,
        "atencao": 50,
        "critico": 30,
        "qualidade": 174,
        "cq_atrasados": 117,
        "cq_total": 174,
        "doca_atrasados": 80,
        "doca_total": 131,
        "data_antigo_cq": "03.06.2026",
        "dias_antigo_cq": 19,
        "data_antigo_rec": "15.05.2026",
        "dias_antigo_rec": 38,
        "hora_atualizacao": datetime.datetime.now().strftime("%H:%M:%S")
    }

dados = buscar_dados_banco()

# ==========================================
# 5. BARRA LATERAL (Menu e KPIs)
# ==========================================
with st.sidebar:
    st.title("Hub Inbound")
    
    # Navegação usando selectbox (ou radio) para não conflitar com botões
    st.session_state['menu_selecionado'] = st.selectbox(
        "Navegação:",
        ["0. GESTÃO À VISTA", "1. ENVIAR (Recebimento Físico)", "2. ACONDICIONAR (Almoxarifado)", "3. HISTÓRICO GERAL", "4. MURAL", "5. ADMINISTRAÇÃO"]
    )
    
    st.markdown("---")
    st.subheader("Indicadores")
    
    # Cartões de KPI customizados na lateral
    st.markdown(f"""
        <div class="kpi-card" style="border-color: #007bff;">
            <p style="margin:0; font-size:12px; color:gray;">TOTAL NO RECEBIMENTO</p>
            <h3 style="margin:0; color:#007bff;">{dados['total_recebimento']}</h3>
        </div>
        <div class="kpi-card" style="border-color: #28a745;">
            <p style="margin:0; font-size:12px; color:gray;">PRAZO (≤3D)</p>
            <h3 style="margin:0; color:#28a745;">{dados['prazo']}</h3>
        </div>
        <div class="kpi-card" style="border-color: #ffc107;">
            <p style="margin:0; font-size:12px; color:gray;">ATENÇÃO (>3D)</p>
            <h3 style="margin:0; color:#ffc107;">{dados['atencao']}</h3>
        </div>
        <div class="kpi-card" style="border-color: #dc3545;">
            <p style="margin:0; font-size:12px; color:gray;">CRÍTICO (>7D)</p>
            <h3 style="margin:0; color:#dc3545;">{dados['critico']}</h3>
        </div>
        <div class="kpi-card" style="border-color: #6f42c1;">
            <p style="margin:0; font-size:12px; color:gray;">QUALIDADE (CQ)</p>
            <h3 style="margin:0; color:#6f42c1;">{dados['qualidade']}</h3>
        </div>
        <br>
        <p style="font-size: 10px; color: gray;">Última atualização: {dados['hora_atualizacao']}</p>
    """, unsafe_allow_html=True)

# ==========================================
# 6. FUNÇÃO GERADORA DE MANÔMETRO DIGITAL
# ==========================================
def criar_manometro_digital(valor, maximo, titulo, cor_ponteiro):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = valor,
        title = {'text': titulo, 'font': {'size': 18, 'color': '#333'}},
        number = {'font': {'size': 40, 'color': cor_ponteiro}}, # Número no centro
        gauge = {
            'axis': {'range': [0, maximo], 'tickwidth': 1, 'tickcolor': "darkgray"},
            'bar': {'color': "rgba(0,0,0,0)"}, # Esconde a barra tradicional
            'bgcolor': "#f0f2f6", # Fundo do manômetro
            'borderwidth': 2,
            'bordercolor': "#d1d5db",
            'steps': [
                {'range': [0, maximo*0.33], 'color': "#28a745"}, # Verde
                {'range': [maximo*0.33, maximo*0.66], 'color': "#ffc107"}, # Amarelo
                {'range': [maximo*0.66, maximo], 'color': "#dc3545"} # Vermelho
            ],
            'threshold': { # O PONTEIRO DIGITAL
                'line': {'color': cor_ponteiro, 'width': 6},
                'thickness': 0.8,
                'value': valor
            }
        }
    ))
    fig.update_layout(height=220, margin=dict(l=10, r=10, t=40, b=10))
    return fig

# ==========================================
# 7. TELA PRINCIPAL - GESTÃO À VISTA
# ==========================================
if st.session_state['menu_selecionado'] == "0. GESTÃO À VISTA":
    
    # Linha 1: Gráficos e Relógio
    col1, col2, col3 = st.columns([1.5, 1, 1.5])
    
    with col1:
        st.markdown("<h4 style='text-align: center; color: #0056b3;'>Laboratório Qualidade</h4>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(criar_manometro_digital(dados['cq_atrasados'], 150, "Atrasados", "#dc3545"), use_container_width=True)
        with c2:
            st.plotly_chart(criar_manometro_digital(dados['cq_total'], 200, "Total (CQ)", "#007bff"), use_container_width=True)

    with col2:
        st.markdown("<h4 style='text-align: center; color: #0056b3;'>Relógio de Permanência</h4>", unsafe_allow_html=True)
        st.markdown(f"""
            <div style="text-align: center; margin-top: 20px;">
                <p style="margin:0; font-weight: bold; color: gray;">Material mais Antigo na Qualidade</p>
                <p style="margin:0; font-size: 14px;">Esquecido há {dados['dias_antigo_cq']} dias</p>
                <h4 style="margin:0; color: #6f42c1;">{dados['data_antigo_cq']}</h4>
                <br>
                <p style="margin:0; font-weight: bold; color: gray;">Material mais Antigo no Recebimento</p>
                <p style="margin:0; font-size: 14px;">Esquecido há {dados['dias_antigo_rec']} dias</p>
                <h4 style="margin:0; color: #0056b3;">{dados['data_antigo_rec']}</h4>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("<h4 style='text-align: center; color: #0056b3;'>Doca (Recebimento)</h4>", unsafe_allow_html=True)
        c3, c4 = st.columns(2)
        with c3:
            st.plotly_chart(criar_manometro_digital(dados['doca_atrasados'], 100, "Atrasados", "#dc3545"), use_container_width=True)
        with c4:
            st.plotly_chart(criar_manometro_digital(dados['doca_total'], 200, "Total Livre", "#007bff"), use_container_width=True)

    st.markdown("---")
    
    # Linha 2: Tabelas de Top 10
    col_tabela1, col_tabela2 = st.columns(2)
    
    # DADOS FALSOS PARA AS TABELAS (Substitua pelos seus DataFrames do banco)
    df_lab = pd.DataFrame({
        "dias_parado": [19, 19, 19, 19, 19],
        "material": ["19368049", "15001791", "19364264", "19363885", "16370913"],
        "descricao": ["SKID UNIDADE HIDRAULICA", "JUNTA VEDACAO", "VALVULA REG PRESSAO", "VALVULA REG PRESSAO", "SUPORTE GUIA"],
        "nfe": ["00008266-1", "000047058-1", "000003823-1", "000003823-1", "000004581-1"]
    })
    
    df_doca = pd.DataFrame({
        "dias_parado": [38, 20, 19, 19, 18],
        "material": ["14979153", "14781094", "14720735", "14932313", "14725065"],
        "descricao": ["MOLA COMPRESSAO", "TUBO ASTM A335", "VALVULA DISCO", "ANEL CORPO MANCAL", "VALVULA GAV"],
        "nfe": ["000026872-1", "000099349-3", "000328534-2", "USINAGEM", "000049058-1"]
    })

    with col_tabela1:
        st.markdown("<h5 style='color: #dc3545;'>🔴 Top 10 Itens Esquecidos (Laboratório Qualidade)</h5>", unsafe_allow_html=True)
        st.dataframe(df_lab, use_container_width=True, hide_index=True, height=180)
        
    with col_tabela2:
        st.markdown("<h5 style='color: #ffc107;'>🟡 Top 10 Itens Esquecidos (Recebimento Livre)</h5>", unsafe_allow_html=True)
        st.dataframe(df_doca, use_container_width=True, hide_index=True, height=180)

else:
    # Se o usuário selecionar outra opção no menu lateral, o conteúdo renderiza aqui
    st.write(f"Você está na tela: {st.session_state['menu_selecionado']}")
    st.write("Para voltar ao painel fixo, selecione '0. GESTÃO À VISTA' no menu lateral.")
