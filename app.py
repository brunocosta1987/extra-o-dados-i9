import streamlit as st
import pdfplumber
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="Dashboard MPRJ", layout="wide")

st.title("🚗 Dashboard de Recibos - TaxiCorp MPRJ")

# =============================
# FUNÇÕES AUXILIARES
# =============================
def limpar_texto(texto):
    if texto:
        return re.sub(r'\s+', ' ', texto).strip()
    return None

def buscar_bloco(inicio, fim, texto):
    padrao = rf'{inicio}\s*(.*?)\s*{fim}'
    match = re.search(padrao, texto, re.DOTALL)
    return limpar_texto(match.group(1)) if match else None

def buscar_valor(label, texto):

    # pega um bloco maior depois do label
    padrao = rf'{label}(.*?)(?:Total|Valor|Distância|Duração|$)'
    match = re.search(padrao, texto, re.DOTALL | re.IGNORECASE)

    if match:
        trecho = match.group(1)

        # procura QUALQUER valor monetário dentro do trecho
        valor = re.search(r'R?\$?\s*([\d\.,]+)', trecho)

        if valor:
            return limpar_texto(valor.group(1))

    return "0"


# =============================
# EXTRAÇÃO DE DADOS
# =============================
def extrair_dados(texto):

    dados = {}

    # Identificação
    dados['Recibo'] = limpar_texto(
        re.search(r'Recibo de Atendimento #(\d+)', texto).group(1)
        if re.search(r'Recibo de Atendimento #(\d+)', texto) else None
    )

    dados['Data Recibo'] = limpar_texto(
        re.search(r'\|\s*(\d{2}/\d{2}/\d{4} \d{2}:\d{2})', texto).group(1)
        if re.search(r'\|\s*(\d{2}/\d{2}/\d{4} \d{2}:\d{2})', texto) else None
    )

    # Pessoas
    dados['Solicitante'] = buscar_bloco("Solicitante", "Passageiro", texto)
    dados['Passageiro'] = buscar_bloco("Passageiro", "Qtd.", texto)

    # Datas
    dados['Solicitação'] = buscar_bloco("Solicitação", "Embarque", texto)
    dados['Embarque'] = buscar_bloco("Embarque", "Desembarque", texto)
    dados['Desembarque'] = buscar_bloco("Desembarque", "Origem", texto)

    # Rota
    dados['Origem'] = buscar_bloco("Origem", "Destino", texto)
    dados['Destino'] = buscar_bloco("Destino", "Observações", texto)

    # Operacional
    dados['Observações'] = buscar_bloco("Observações", "Distância", texto)

    dados['Distância (km)'] = limpar_texto(
        re.search(r'Distância\s*(\d+)', texto).group(1)
        if re.search(r'Distância\s*(\d+)', texto) else "0"
    )

    dados['Duração (min)'] = limpar_texto(
        re.search(r'Duração\s*(\d+)', texto).group(1)
        if re.search(r'Duração\s*(\d+)', texto) else "0"
    )

    # Financeiro (CORRIGIDO)
    dados['Valor Corrida'] = buscar_valor("Valor da Corrida", texto)
    dados['Total Voucher'] = buscar_valor("Total do Voucher", texto)
    dados['Pedágio'] = buscar_valor("Pedágio", texto)

    return dados


# =============================
# PROCESSAMENTO
# =============================
def processar_pdf(arquivo):

    registros = []

    with pdfplumber.open(arquivo) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text()

            if texto:
                dados = extrair_dados(texto)
                registros.append(dados)

    return registros


# =============================
# INTERFACE
# =============================
arquivos = st.file_uploader(
    "📎 Envie os PDFs",
    type="pdf",
    accept_multiple_files=True
)

if arquivos:

    todos = []

    for arquivo in arquivos:
        st.write(f"📄 Processando: {arquivo.name}")
        dados = processar_pdf(arquivo)
        todos.extend(dados)

    df = pd.DataFrame(todos)

    # =============================
    # CONVERSÕES
    # =============================
    def converter_valor(coluna):
        return (
            coluna.fillna("0")
            .astype(str)
            .str.replace('.', '', regex=False)
            .str.replace(',', '.', regex=False)
            .astype(float)
        )

    df['Valor Corrida'] = converter_valor(df['Valor Corrida'])
    df['Total Voucher'] = converter_valor(df['Total Voucher'])
    df['Pedágio'] = converter_valor(df['Pedágio'])
    df['Distância (km)'] = pd.to_numeric(df['Distância (km)'], errors='coerce').fillna(0)

    # Datas
    df['Data Recibo'] = pd.to_datetime(df['Data Recibo'], errors='coerce')
    df['Dia'] = df['Data Recibo'].dt.date

    # =============================
    # KPIs
    # =============================
    st.subheader("📊 Indicadores Gerais")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("🚗 KM Total", f"{df['Distância (km)'].sum():,.0f}")
    col2.metric("🛣️ Pedágio", f"R$ {df['Pedágio'].sum():,.2f}")
    col3.metric("💰 Voucher", f"R$ {df['Total Voucher'].sum():,.2f}")
    col4.metric("📄 Qtde Recibos", len(df))

    # =============================
    # GRÁFICOS
    # =============================
    st.subheader("📈 Análises")

    gasto_dia = df.groupby('Dia')['Total Voucher'].sum().reset_index()
    st.line_chart(gasto_dia.set_index('Dia'))

    km_dia = df.groupby('Dia')['Distância (km)'].sum().reset_index()
    st.bar_chart(km_dia.set_index('Dia'))

    st.subheader("👤 Top 10 Passageiros")
    top_passageiros = (
        df.groupby('Passageiro')['Total Voucher']
        .sum()
        .sort_values(ascending=False)
        .head(10)
    )
    st.bar_chart(top_passageiros)

    # =============================
    # FILTROS
    # =============================
    st.subheader("🔍 Filtros")

    passageiros = st.multiselect(
        "Filtrar por Passageiro",
        options=df['Passageiro'].dropna().unique()
    )

    if passageiros:
        df = df[df['Passageiro'].isin(passageiros)]

    # =============================
    # TABELA
    # =============================
    st.subheader("📋 Dados Detalhados")
    st.dataframe(df, use_container_width=True)

    # =============================
    # DOWNLOAD
    # =============================
    buffer = BytesIO()
    df.to_excel(buffer, index=False)

    st.download_button(
        label="📥 Baixar Excel",
        data=buffer.getvalue(),
        file_name="dashboard_mprj.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
