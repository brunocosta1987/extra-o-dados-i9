import streamlit as st
import pdfplumber
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="Extrator MPRJ", layout="wide")

st.title("🚗 Extrator de Recibos - TaxiCorp MPRJ")

# =============================
# FUNÇÃO DE EXTRAÇÃO
# =============================
def extrair_dados(texto):

    def buscar(padrao):
        match = re.search(padrao, texto, re.DOTALL)
        return match.group(1).strip() if match else None

    dados = {}

    # Identificação
    dados['Recibo'] = buscar(r'Recibo de Atendimento #(\d+)')
    dados['Data Recibo'] = buscar(r'\|\s*(\d{2}/\d{2}/\d{4} \d{2}:\d{2})')

    # Pessoas
    dados['Solicitante'] = buscar(r'Solicitante\s*\n([A-Z\s]+)')
    dados['Passageiro'] = buscar(r'Passageiro\s*\n(.+)')

    # Datas
    dados['Solicitação'] = buscar(r'Solicitação\s*\n([\d/\s:]+)')
    dados['Embarque'] = buscar(r'Embarque\s*\n([\d/\s:]+)')
    dados['Desembarque'] = buscar(r'Desembarque\s*\n([\d/\s:]+)')

    # Rota
    dados['Origem'] = buscar(r'Origem\s+(.*?)\n')
    dados['Destino'] = buscar(r'Destino\s+(.*?)\n')

    # Operacional
    dados['Observações'] = buscar(r'Observações\s*\n(.+)')
    dados['Distância (km)'] = buscar(r'Distância\s*\n(\d+)')
    dados['Duração (min)'] = buscar(r'Duração\s*\n(\d+)')

    # Financeiro
    dados['Valor Corrida'] = buscar(r'Valor da Corrida\s*\nR\$ ([\d,]+)')
    dados['Total Voucher'] = buscar(r'Total do Voucher\s*\nR\$ ([\d,]+)')

    return dados


# =============================
# PROCESSAMENTO DO PDF
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
# UPLOAD
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

    # Tratamento de valores
    df['Valor Corrida'] = df['Valor Corrida'].str.replace(',', '.').astype(float)
    df['Total Voucher'] = df['Total Voucher'].str.replace(',', '.').astype(float)

    st.subheader("📊 Dados Extraídos")
    st.dataframe(df, use_container_width=True)

    # Download Excel
    buffer = BytesIO()
    df.to_excel(buffer, index=False)

    st.download_button(
        label="📥 Baixar Excel",
        data=buffer.getvalue(),
        file_name="relatorio_mprj.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
