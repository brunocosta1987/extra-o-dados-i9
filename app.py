import streamlit as st
import pdfplumber
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="Extrator MPRJ", layout="wide")

st.title("🚗 Extrator de Recibos - TaxiCorp MPRJ")

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


# =============================
# EXTRAÇÃO MELHORADA
# =============================
def extrair_dados(texto):

    dados = {}

    # ID e Data
    dados['Recibo'] = limpar_texto(
        re.search(r'Recibo de Atendimento #(\d+)', texto).group(1)
        if re.search(r'Recibo de Atendimento #(\d+)', texto) else None
    )

    dados['Data Recibo'] = limpar_texto(
        re.search(r'\|\s*(\d{2}/\d{2}/\d{4} \d{2}:\d{2})', texto).group(1)
        if re.search(r'\|\s*(\d{2}/\d{2}/\d{4} \d{2}:\d{2})', texto) else None
    )

    # Pessoas (agora robusto)
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
        if re.search(r'Distância\s*(\d+)', texto) else None
    )

    dados['Duração (min)'] = limpar_texto(
        re.search(r'Duração\s*(\d+)', texto).group(1)
        if re.search(r'Duração\s*(\d+)', texto) else None
    )

    # Financeiro
    dados['Valor Corrida'] = limpar_texto(
        re.search(r'Valor da Corrida\s*R\$ ([\d,]+)', texto).group(1)
        if re.search(r'Valor da Corrida\s*R\$ ([\d,]+)', texto) else None
    )

    dados['Total Voucher'] = limpar_texto(
        re.search(r'Total do Voucher\s*R\$ ([\d,]+)', texto).group(1)
        if re.search(r'Total do Voucher\s*R\$ ([\d,]+)', texto) else None
    )

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

    # Conversões
    if 'Valor Corrida' in df.columns:
        df['Valor Corrida'] = df['Valor Corrida'].str.replace(',', '.').astype(float)

    if 'Total Voucher' in df.columns:
        df['Total Voucher'] = df['Total Voucher'].str.replace(',', '.').astype(float)

    st.subheader("📊 Dados Extraídos")
    st.dataframe(df, use_container_width=True)

    # Download
    buffer = BytesIO()
    df.to_excel(buffer, index=False)

    st.download_button(
        label="📥 Baixar Excel",
        data=buffer.getvalue(),
        file_name="relatorio_mprj.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
