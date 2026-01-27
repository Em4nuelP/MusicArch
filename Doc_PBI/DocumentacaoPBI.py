
import pandas as pd
from pathlib import Path
from datetime import datetime

# ==================================================
# CONFIGURAÇÕES DE PASTA
# ==================================================
PASTA_INPUT = Path(r"C:\Users\wiser.user\OneDrive - Wiser\Área de Trabalho\teste docu\DocDet")
PASTA_OUTPUT = Path(r"C:\Users\wiser.user\OneDrive - Wiser\Área de Trabalho\teste docu\DocSint")

PASTA_OUTPUT.mkdir(parents=True, exist_ok=True)

# ==================================================
# NOME DO PROJETO (BASEADO NA PASTA PAI)
# ==================================================
nome_projeto = PASTA_INPUT.parent.name.replace(" ", "_")

# ==================================================
# DATA / HORA DA EXPORTAÇÃO
# ==================================================
agora = datetime.now()
data_hora_html = agora.strftime("%d/%m/%Y %H:%M:%S")
data_hora_arquivo = agora.strftime("%Y-%m-%d_%H-%M-%S")

# ==================================================
# FUNÇÃO DE LEITURA ROBUSTA
# ==================================================
def ler_csv(nome):
    caminho = PASTA_INPUT / nome
    if not caminho.exists():
        print(f"⚠️ Arquivo não encontrado: {nome}")
        return None

    return pd.read_csv(
        caminho,
        engine="python",
        sep=None,
        encoding="utf-8-sig",
        on_bad_lines="skip"
    )

# ==================================================
# CARREGAMENTO DOS ARQUIVOS
# ==================================================
tables         = ler_csv("Tabela.csv")
columns        = ler_csv("Coluna.csv")
measures       = ler_csv("Medida.csv")
relationships  = ler_csv("Relacionamento.csv")
partitions     = ler_csv("M.csv")
roles          = ler_csv("Rls Regra.csv")
permissions    = ler_csv("Rls Filtro.csv")
hierarchies    = ler_csv("Hierarquia.csv")

# ==================================================
# LIMPEZA / SELEÇÃO DE COLUNAS ÚTEIS
# ==================================================
def filtrar(df, cols):
    if df is None:
        return None
    return df[[c for c in cols if c in df.columns]]

tables = filtrar(tables, ["Name", "IsHidden", "Description"])

columns = filtrar(columns, [
    "TableID",
    "ExplicitName",
    "SourceColumn",
    "ExplicitDataType",
    "InferredDataType",
    "IsHidden",
    "IsKey",
    "IsNullable"
])

measures = filtrar(measures, [
    "TableID",
    "Name",
    "MeasureName",
    "Expression",
    "Description"
])

relationships = filtrar(relationships, [
    "FromTable",
    "FromColumn",
    "ToTable",
    "ToColumn",
    "Cardinality"
])

partitions = filtrar(partitions, [
    "Name",
    "QueryDefinition",
    "Mode"
])

roles = filtrar(roles, ["Name"])
permissions = filtrar(permissions, ["TableID", "FilterExpression"])
hierarchies = filtrar(hierarchies, ["TableID", "Name", "Levels"])

# ==================================================
# CONVERTE \n EM <br> (QUEBRA DE LINHA NO HTML)
# ==================================================
def limpar_quebras(df):
    if df is None:
        return None

    df = df.copy()
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(r"\r\n|\r|\n", "<br>", regex=True)
                .str.replace(r"[ \t]{2,}", " ", regex=True)
                .str.strip()
            )
    return df

measures    = limpar_quebras(measures)
partitions  = limpar_quebras(partitions)
permissions = limpar_quebras(permissions)
hierarchies = limpar_quebras(hierarchies)

# ==================================================
# HTML
# ==================================================
def html_tabela(df):
    return df.to_html(index=False, escape=False)

html = f"""
<html>
<head>
<meta charset="utf-8">
<title>Documentação Power BI - {nome_projeto}</title>
<style>
body {{ font-family: Arial; margin: 40px; }}
h1, h2 {{ color: #2c3e50; }}
table {{ border-collapse: collapse; width: 100%; margin-bottom: 40px; }}
th, td {{ border: 1px solid #ccc; padding: 6px; font-size: 12px; vertical-align: top; }}
th {{ background-color: #f4f6f6; }}
</style>
</head>
<body>

<h1>📘 Documentação Power BI</h1>
<p><strong>Projeto:</strong> {nome_projeto}</p>
<p><strong>Exportado em:</strong> {data_hora_html}</p>
"""

def add_secao(titulo, df):
    global html
    if df is not None and not df.empty:
        html += f"<h2>{titulo}</h2>"
        html += html_tabela(df)

add_secao("📁 Tabelas do Modelo", tables)
add_secao("📐 Dicionário de Dados (Colunas)", columns)
add_secao("📊 Medidas (DAX)", measures)
add_secao("🔗 Relacionamentos", relationships)
add_secao("🧠 Código Avançado (Power Query)", partitions)
add_secao("🔐 Segurança (Roles)", roles)
add_secao("🔐 Segurança (Filtros RLS)", permissions)
add_secao("🧱 Hierarquias", hierarchies)

html += "</body></html>"

# ==================================================
# VERSIONAMENTO AUTOMÁTICO
# ==================================================
def proxima_versao(pasta, prefixo):
    arquivos = list(pasta.glob(f"{prefixo}_v*.html"))
    if not arquivos:
        return 1

    versoes = []
    for a in arquivos:
        try:
            v = int(a.stem.split("_v")[-1].split("_")[0])
            versoes.append(v)
        except ValueError:
            pass

    return max(versoes) + 1 if versoes else 1

prefixo_arquivo = f"{nome_projeto}_Documentacao_PowerBI"
versao = proxima_versao(PASTA_OUTPUT, prefixo_arquivo)

nome_arquivo = f"{prefixo_arquivo}_v{versao}_{data_hora_arquivo}.html"

# ==================================================
# SALVAR ARQUIVO
# ==================================================
with open(PASTA_OUTPUT / nome_arquivo, "w", encoding="utf-8") as f:
    f.write(html)

print("✅ DOCUMENTAÇÃO GERADA COM SUCESSO!")
print(f"📂 Pasta: {PASTA_OUTPUT}")
print(f"📄 Arquivo: {nome_arquivo}")









