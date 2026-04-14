import pandas as pd
from pathlib import Path
from datetime import datetime
import zipfile
import xml.etree.ElementTree as ET

# ==================================================
# CONFIGURAÇÕES DE PASTA
# ==================================================
PASTA_INPUT = Path(r"C:\Users\wiser.user\OneDrive - Wiser\Área de Trabalho\Relatório de Entradas\01.Documentacao\02.Arquivo_Origem")
PASTA_INPUT_INF = Path(r"C:\Users\wiser.user\OneDrive - Wiser\Área de Trabalho\Relatório de Entradas\01.Documentacao\01.Informacoes_Gerais")
PASTA_OUTPUT = Path(r"C:\Users\wiser.user\OneDrive - Wiser\Área de Trabalho\Relatório de Entradas\01.Documentacao")

PASTA_OUTPUT.mkdir(parents=True, exist_ok=True)

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


def normalizar_texto(valor):
    if valor is None:
        return ""
    if pd.isna(valor):
        return ""
    texto = str(valor).replace("\xa0", " ").strip()
    return "" if texto.lower() == "nan" else texto


def coluna_excel_para_indice(ref):
    letras = "".join(ch for ch in ref if ch.isalpha()).upper()
    indice = 0
    for letra in letras:
        indice = indice * 26 + (ord(letra) - ord("A") + 1)
    return indice - 1


def ler_xlsx_sem_openpyxl(caminho):
    ns = {
        "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "p": "http://schemas.openxmlformats.org/package/2006/relationships",
    }

    with zipfile.ZipFile(caminho) as arquivo_zip:
        shared_strings = []
        if "xl/sharedStrings.xml" in arquivo_zip.namelist():
            raiz_shared = ET.fromstring(arquivo_zip.read("xl/sharedStrings.xml"))
            for item in raiz_shared.findall("a:si", ns):
                texto = "".join(no.text or "" for no in item.iterfind(".//a:t", ns))
                shared_strings.append(texto)

        workbook = ET.fromstring(arquivo_zip.read("xl/workbook.xml"))
        rels = ET.fromstring(arquivo_zip.read("xl/_rels/workbook.xml.rels"))
        rel_map = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rels.findall("p:Relationship", ns)
        }

        primeira_aba = workbook.find("a:sheets/a:sheet", ns)
        if primeira_aba is None:
            return pd.DataFrame()

        rel_id = primeira_aba.attrib.get(
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        )
        sheet_path = rel_map.get(rel_id, "")
        if not sheet_path:
            return pd.DataFrame()
        if not sheet_path.startswith("xl/"):
            sheet_path = f"xl/{sheet_path}"

        worksheet = ET.fromstring(arquivo_zip.read(sheet_path))

        linhas = []
        for row in worksheet.findall("a:sheetData/a:row", ns):
            valores = {}
            max_col = -1

            for cell in row.findall("a:c", ns):
                referencia = cell.attrib.get("r", "")
                if not referencia:
                    continue

                indice_coluna = coluna_excel_para_indice(referencia)
                max_col = max(max_col, indice_coluna)

                cell_type = cell.attrib.get("t")
                valor = cell.find("a:v", ns)

                if cell_type == "s" and valor is not None and valor.text is not None:
                    texto = shared_strings[int(valor.text)]
                elif cell_type == "inlineStr":
                    texto = "".join(no.text or "" for no in cell.iterfind(".//a:t", ns))
                elif valor is not None and valor.text is not None:
                    texto = valor.text
                else:
                    texto = ""

                valores[indice_coluna] = texto

            if max_col >= 0:
                linhas.append([valores.get(i, "") for i in range(max_col + 1)])

    if not linhas:
        return pd.DataFrame()

    largura = max(len(linha) for linha in linhas)
    linhas = [linha + [""] * (largura - len(linha)) for linha in linhas]

    cabecalho = [normalizar_texto(col) or f"Coluna_{i + 1}" for i, col in enumerate(linhas[0])]
    dados = linhas[1:]
    df = pd.DataFrame(dados, columns=cabecalho)
    df = df.replace(r"^\s*$", pd.NA, regex=True).dropna(how="all").reset_index(drop=True)
    return df


def ler_tabular(caminho):
    if caminho.suffix.lower() == ".csv":
        return pd.read_csv(
            caminho,
            engine="python",
            sep=None,
            encoding="utf-8-sig",
            on_bad_lines="skip"
        )

    if caminho.suffix.lower() in {".xlsx", ".xlsm"}:
        try:
            return pd.read_excel(caminho)
        except ImportError:
            return ler_xlsx_sem_openpyxl(caminho)

    print(f"⚠️ Formato não suportado: {caminho.name}")
    return None


def ler_info_geral():
    if not PASTA_INPUT_INF.exists():
        print(f"⚠️ Pasta de informações gerais não encontrada: {PASTA_INPUT_INF}")
        return None

    arquivos = sorted(
        [
            arq for arq in PASTA_INPUT_INF.iterdir()
            if arq.is_file()
            and arq.suffix.lower() in {".xlsx", ".xlsm", ".csv"}
            and not arq.name.startswith("~$")
        ]
    )

    if not arquivos:
        print("⚠️ Nenhum arquivo de informações gerais encontrado.")
        return None

    return ler_tabular(arquivos[0])


def primeiro_valor_preenchido(df, coluna):
    if df is None or df.empty or coluna not in df.columns:
        return ""

    for valor in df[coluna]:
        texto = normalizar_texto(valor)
        if texto:
            return texto
    return ""


def montar_visao_geral(df):
    if df is None or df.empty:
        return None

    registros = []
    for coluna in df.columns:
        if coluna == "Nome Relatório:":
            continue

        valores = []
        vistos = set()
        for valor in df[coluna]:
            texto = normalizar_texto(valor)
            if not texto:
                continue
            chave = texto.casefold()
            if chave in vistos:
                continue
            vistos.add(chave)
            valores.append(texto)

        if valores:
            registros.append({
                "Campo": coluna.rstrip(":"),
                "Informações": "<br>".join(valores),
            })

    return pd.DataFrame(registros) if registros else None


# ==================================================
# INFORMAÇÕES GERAIS / NOME DO PROJETO
# Se quiser definir manualmente, escreva abaixo.
# Se deixar vazio "", usa "Nome Relatório:" do arquivo em PASTA_INPUT_INF.
# ==================================================
info_geral = ler_info_geral()
NOME_PROJETO_MANUAL = ""

nome_relatorio_info = primeiro_valor_preenchido(info_geral, "Nome Relatório:")

if NOME_PROJETO_MANUAL.strip():
    nome_projeto_exibicao = NOME_PROJETO_MANUAL.strip()
elif nome_relatorio_info:
    nome_projeto_exibicao = nome_relatorio_info
else:
    nome_projeto_exibicao = PASTA_INPUT.parent.name

nome_projeto = nome_projeto_exibicao.replace(" ", "_")
visao_geral = montar_visao_geral(info_geral)

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
    cols_existentes = [c for c in cols if c in df.columns]
    if not cols_existentes:
        return df
    return df[cols_existentes]

tables = filtrar(tables, ["ID", "Name", "IsHidden", "Description"])

columns = filtrar(columns, [
    "ID",
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
    "ID",
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
    "ID",
    "Name",
    "QueryDefinition",
    "Mode"
])

roles = filtrar(roles, ["ID", "Name"])
permissions = filtrar(permissions, ["ID", "TableID", "FilterExpression"])
hierarchies = filtrar(hierarchies, ["ID", "TableID", "Name", "Levels"])

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

measures       = limpar_quebras(measures)
partitions     = limpar_quebras(partitions)
permissions    = limpar_quebras(permissions)
hierarchies    = limpar_quebras(hierarchies)
tables         = limpar_quebras(tables)
columns        = limpar_quebras(columns)
relationships  = limpar_quebras(relationships)
roles          = limpar_quebras(roles)
visao_geral    = limpar_quebras(visao_geral)

# ==================================================
# HTML HELPERS
# ==================================================
def html_tabela(df):
    return df.to_html(index=False, escape=False, classes="doc-table")

def safe_len(df):
    return 0 if df is None else len(df)


def nav_icon_svg(sec_id):
    icones = {
        "visao-geral": """
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M4 6.5h7v11H4zM13 6.5h7v4h-7zM13 12.5h7v5h-7zM4 19.5h16"/>
            </svg>
        """,
        "tabelas": """
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M4 6.5h16v11H4zM4 10.5h16M8 6.5v11M16 6.5v11"/>
            </svg>
        """,
        "colunas": """
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M5 5.5h4v13H5zM10 5.5h4v13h-4zM15 5.5h4v13h-4z"/>
            </svg>
        """,
        "medidas": """
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M6 18.5V10M12 18.5V6.5M18 18.5v-8M4 18.5h16"/>
            </svg>
        """,
        "relacionamentos": """
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M8.5 8.5h3M12.5 8.5h3M8.5 15.5h7M6.5 10.5a2 2 0 1 1 0-4 2 2 0 0 1 0 4ZM17.5 10.5a2 2 0 1 1 0-4 2 2 0 0 1 0 4ZM6.5 17.5a2 2 0 1 1 0-4 2 2 0 0 1 0 4Z"/>
            </svg>
        """,
        "powerquery": """
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M7 7.5h4l2 3 2-3h2M5 16.5h14M8 7.5l-2 9M16 7.5l2 9"/>
            </svg>
        """,
        "roles": """
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M8 10.5V8.5a4 4 0 1 1 8 0v2M6 10.5h12v8H6z"/>
            </svg>
        """,
        "rls": """
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M8 10.5V8.5a4 4 0 1 1 8 0v2M6 10.5h12v8H6zM10 14.5h4"/>
            </svg>
        """,
        "hierarquias": """
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M12 5.5v4M7 12.5h10M7 12.5v6M12 12.5v6M17 12.5v6"/>
            </svg>
        """,
    }
    return icones.get(sec_id, """
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M5 12.5h14"/>
        </svg>
    """).strip()

def add_secao(sec_id, titulo, descricao, df):
    if df is None or df.empty:
        return f"""
        <section class="section" id="{sec_id}" data-section="{sec_id}">
            <div class="section-header">
                <div class="section-header-text">
                    <h2>{titulo}</h2>
                    <p class="section-subtitle">{descricao}</p>
                </div>
                <span class="badge muted">0 registros</span>
            </div>
            <div class="empty-state">Nenhum dado encontrado para esta seção.</div>
        </section>
        """

    qtd = len(df)
    badge_txt = f"{qtd} registro" if qtd == 1 else f"{qtd} registros"

    return f"""
    <section class="section" id="{sec_id}" data-section="{sec_id}">
        <div class="section-header">
            <div class="section-header-text">
                <h2>{titulo}</h2>
                <p class="section-subtitle">{descricao}</p>
            </div>
            <span class="badge">{badge_txt}</span>
        </div>
        <div class="table-wrap">
            {html_tabela(df)}
        </div>
    </section>
    """

# ==================================================
# DEFINIÇÃO DO MENU / SEÇÕES
# ==================================================
SECOES = [
    {"id": "visao-geral",     "label": "Visão Geral",                  "desc": "Informações gerais do relatório preenchidas no arquivo complementar.", "df": visao_geral},
    {"id": "tabelas",         "label": "Tabelas do Modelo",             "desc": "Lista de tabelas do modelo, com visibilidade e descrição.", "df": tables},
    {"id": "colunas",         "label": "Colunas", "desc": "Colunas, tipos, chaves, nulabilidade e propriedades.",      "df": columns},
    {"id": "medidas",         "label": "Medidas (DAX)",                 "desc": "Medidas DAX com expressão e descrição.",                    "df": measures},
    {"id": "relacionamentos", "label": "Relacionamentos",               "desc": "Relacionamentos entre tabelas e cardinalidade.",           "df": relationships},
    {"id": "powerquery",      "label": "Cód. Avançado e TBV",    "desc": "Consultas / QueryDefinition e modo de carregamento.",      "df": partitions},
    {"id": "roles",           "label": "Segurança (Regras)",             "desc": "Papéis de segurança configurados.",                        "df": roles},
    {"id": "rls",             "label": "Segurança (RLS)",       "desc": "Filtros por tabela usados em RLS.",                        "df": permissions},
    {"id": "hierarquias",     "label": "Hierarquias",                   "desc": "Hierarquias e níveis (levels).",                           "df": hierarchies},
]

menu_itens = "\n".join(
    [f"""
    <button class="nav-item" data-target="{s['id']}" title="{s['label']}">
        <span class="nav-label">
            <span class="nav-icon">{nav_icon_svg(s['id'])}</span>
            <span>{s['label']}</span>
        </span>
        <span class="nav-count">{safe_len(s['df'])}</span>
    </button>
    """ for s in SECOES]
)

secoes_html = "\n".join(
    [add_secao(s["id"], s["label"], s["desc"], s["df"]) for s in SECOES]
)

# ==================================================
# HTML FINAL
# ==================================================
html = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Documentação Power BI - {nome_projeto_exibicao}</title>

<style>
:root {{
  --background: #F8FAFC;
  --foreground: #1E293B;
  --card: #FFFFFF;
  --card-foreground: #1E293B;
  --popover: #FFFFFF;
  --popover-foreground: #1E293B;
  --primary: #3B82F6;
  --primary-foreground: #FFFFFF;
  --secondary: #F1F5F9;
  --secondary-foreground: #1E293B;
  --muted: #F1F5F9;
  --muted-foreground: #64748B;
  --accent: #F1F5F9;
  --accent-foreground: #1E293B;
  --border: #E2E8F0;
  --input: #E2E8F0;
  --ring: #3B82F6;
  --radius: 0.5rem;
  --sidebar: #1E293B;
  --sidebar-foreground: #94A3B8;
  --sidebar-primary: #3B82F6;
  --sidebar-primary-foreground: #FFFFFF;
  --sidebar-accent: rgba(255, 255, 255, 0.05);
  --sidebar-accent-foreground: #F8FAFC;
  --sidebar-border: rgba(255, 255, 255, 0.1);
  --sidebar-ring: #3B82F6;
  --shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.06);
  --shadow-md: 0 10px 30px rgba(15, 23, 42, 0.08);
  --header-height: 64px;
  --sidebar-width: 300px;
  --radius: 10px;
}}

* {{
  box-sizing: border-box;
}}

body[data-theme="dark"] {{
  --background: #0F172A;
  --foreground: #E2E8F0;
  --card: #111827;
  --card-foreground: #E2E8F0;
  --popover: #111827;
  --popover-foreground: #E2E8F0;
  --secondary: #1E293B;
  --secondary-foreground: #E2E8F0;
  --muted: #1E293B;
  --muted-foreground: #94A3B8;
  --accent: #1E293B;
  --accent-foreground: #E2E8F0;
  --border: #334155;
  --input: #334155;
  --sidebar: #0F172A;
  --sidebar-foreground: #94A3B8;
  --sidebar-accent: rgba(148, 163, 184, 0.08);
  --sidebar-accent-foreground: #E2E8F0;
  --sidebar-border: rgba(148, 163, 184, 0.18);
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.32);
  --shadow-md: 0 10px 30px rgba(0, 0, 0, 0.28);
}}

html, body {{
  margin: 0;
  padding: 0;
  min-height: 100%;
  background: var(--background);
}}

body {{
  font-family: Inter, "Segoe UI", Roboto, Arial, sans-serif;
  color: var(--foreground);
  overflow-x: hidden;
}}

a {{
  color: var(--primary);
}}

.layout {{
  min-height: 100vh;
  background: var(--background);
}}

.topbar {{
  position: fixed;
  top: 0;
  left: var(--sidebar-width);
  right: 0;
  height: var(--header-height);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 0 20px;
  background: rgba(255, 255, 255, 0.96);
  border-bottom: 1px solid var(--border);
  box-shadow: var(--shadow-sm);
  backdrop-filter: blur(10px);
  z-index: 30;
}}

body[data-theme="dark"] .topbar {{
  background: rgba(15, 23, 42, 0.92);
}}

.topbar-meta {{
  display: flex;
  flex-direction: column;
  min-width: 0;
}}

.topbar-meta h1 {{
  margin: 0;
  font-size: 20px;
  line-height: 1.1;
  color: var(--foreground);
}}

.topbar-meta p {{
  margin: 4px 0 0;
  color: var(--muted-foreground);
  font-size: 12px;
}}

.topbar-actions {{
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}}

.sidebar {{
  position: fixed;
  top: 0;
  left: 0;
  width: var(--sidebar-width);
  height: 100vh;
  padding: 18px 14px 14px;
  background: var(--sidebar);
  border-right: 1px solid var(--sidebar-border);
  overflow-y: auto;
  overflow-x: hidden;
  z-index: 40;
}}

.brand {{
  display: block;
  padding: 14px 12px;
  border: 1px solid var(--sidebar-border);
  border-radius: var(--radius);
  background: rgba(255,255,255,0.02);
  box-shadow: none;
}}

.brand h2 {{
  margin: 0;
  color: #F8FAFC;
  font-size: 15px;
  line-height: 1.2;
  font-weight: 600;
}}

.sidebar-divider {{
  height: 1px;
  margin: 14px 0 12px;
  background: var(--sidebar-border);
}}

.ctrl-btn {{
  min-width: 118px;
  height: 36px;
  padding: 0 14px;
  border: 1px solid var(--border);
  background: var(--card);
  color: var(--foreground);
  border-radius: var(--radius);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  transition: transform .06s ease, background .2s ease, border-color .2s ease, box-shadow .2s ease;
  box-shadow: var(--shadow-sm);
}}

.ctrl-btn:hover {{
  background: #F8FAFC;
  border-color: #CBD5E1;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.08);
}}

.ctrl-btn:active {{
  transform: translateY(1px);
}}

.ctrl-btn.primary {{
  background: var(--primary);
  color: var(--primary-foreground);
  border-color: var(--primary);
}}

.ctrl-btn.primary:hover {{
  background: #2563EB;
  border-color: #2563EB;
}}

.nav {{
  display: flex;
  flex-direction: column;
  gap: 8px;
}}

.nav-item {{
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  text-align: left;
  padding: 10px 12px;
  border-radius: var(--radius);
  border: 1px solid transparent;
  background: var(--sidebar-accent);
  color: var(--sidebar-accent-foreground);
  cursor: pointer;
  transition: background .2s ease, border-color .2s ease, transform .06s ease;
}}

.nav-item:hover {{
  background: rgba(255,255,255,0.08);
  border-color: var(--sidebar-border);
}}

.nav-item.active {{
  background: rgba(59,130,246,0.20);
  border-color: rgba(59,130,246,0.55);
}}

.nav-label {{
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-size: 12.5px;
  line-height: 1.35;
  font-weight: 600;
  max-width: calc(100% - 70px);
}}

.nav-icon {{
  width: 18px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 18px;
  color: #93C5FD;
}}

.nav-icon svg {{
  width: 18px;
  height: 18px;
  stroke: currentColor;
  stroke-width: 1.7;
  stroke-linecap: round;
  stroke-linejoin: round;
  fill: none;
}}

.nav-count {{
  font-size: 12px;
  color: #E2E8F0;
  padding: 3px 9px;
  border-radius: 999px;
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.10);
  font-weight: 700;
}}

.main {{
  margin-left: var(--sidebar-width);
  padding: calc(var(--header-height) + 16px) 20px 20px;
  min-height: 100vh;
  overflow-y: auto;
  overflow-x: hidden;
  background: var(--background);
}}

.header {{
  display: none;
}}

.section {{
  display: none;
  margin-top: 14px;
  padding: 16px;
  background: var(--card);
  color: var(--card-foreground);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-md);
  page-break-before: always;
}}

.section.visible {{
  display: block;
}}

.section-header {{
  position: relative;
  margin-bottom: 16px;
  padding-right: 140px;
}}

.section-header-text h2 {{
  margin: 0;
  font-size: 18px;
  color: var(--foreground);
}}

.section-subtitle {{
  margin: 8px 0 0;
  color: var(--muted-foreground);
  font-size: 13px;
  line-height: 1.5;
}}

.badge {{
  position: absolute;
  top: 0;
  right: 0;
  font-size: 12px;
  padding: 6px 10px;
  border-radius: 999px;
  background: #DBEAFE;
  border: 1px solid #BFDBFE;
  color: #1D4ED8;
  white-space: nowrap;
  font-weight: 700;
}}

.badge.muted {{
  background: #F1F5F9;
  border-color: var(--border);
  color: var(--muted-foreground);
}}

.empty-state {{
  padding: 16px;
  color: var(--muted-foreground);
  font-size: 14px;
  border: 1px dashed #CBD5E1;
  border-radius: var(--radius);
  background: #F8FAFC;
}}

body[data-theme="dark"] .empty-state {{
  background: #0F172A;
  border-color: #334155;
}}

.table-wrap {{
  max-width: 100%;
  overflow-x: auto;
  overflow-y: hidden;
  border-radius: var(--radius);
  border: 1px solid var(--border);
  background: var(--card);
}}

table.doc-table {{
  width: max-content;
  min-width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 13px;
}}

table.doc-table thead th {{
  position: sticky;
  top: 0;
  background: #F8FAFC;
  border-bottom: 1px solid var(--border);
  color: var(--foreground);
  text-align: left;
  padding: 14px 12px;
  white-space: nowrap;
  font-weight: 700;
  z-index: 2;
}}

table.doc-table thead th:first-child {{
  border-top-left-radius: var(--radius);
}}

table.doc-table thead th:last-child {{
  border-top-right-radius: var(--radius);
}}

body[data-theme="dark"] table.doc-table thead th {{
  background: #172033;
}}

table.doc-table td {{
  border-top: 1px solid #EEF2F7;
  padding: 12px;
  vertical-align: top;
  color: var(--foreground);
  word-break: break-word;
  line-height: 1.45;
}}

table.doc-table tbody tr:nth-child(even) td {{
  background: #FBFDFF;
}}

table.doc-table tbody tr:hover td {{
  background: #F1F5F9;
}}

body[data-theme="dark"] table.doc-table tbody tr:nth-child(even) td {{
  background: #0F1A2E;
}}

body[data-theme="dark"] table.doc-table tbody tr:hover td {{
  background: #1E293B;
}}

@media print {{
  html, body {{
    margin: 0 !important;
    padding: 0 !important;
    background: white !important;
    color: #000 !important;
  }}

  .layout {{
    width: 100% !important;
    height: auto !important;
    display: block !important;
    overflow: visible !important;
  }}

  .sidebar,
  .topbar-actions {{
    display: none !important;
  }}

  .topbar {{
    position: static !important;
    left: 0 !important;
    height: auto !important;
    padding: 0 0 12px !important;
    background: white !important;
    border-bottom: 1px solid #ccc !important;
    box-shadow: none !important;
  }}

  .main {{
    margin-left: 0 !important;
    height: auto !important;
    max-height: none !important;
    overflow: visible !important;
    padding: 0 !important;
  }}

  .header {{
    margin-bottom: 12px !important;
  }}

  .section {{
    display: block !important;
    margin-top: 12px !important;
    break-inside: auto !important;
    page-break-before: always !important;
    box-shadow: none !important;
    background: white !important;
    border: 1px solid #ccc !important;
  }}

  .table-wrap {{
    overflow: visible !important;
    max-width: 100% !important;
    border: 1px solid #ccc !important;
    background: white !important;
  }}

  table.doc-table {{
    width: 100% !important;
    min-width: 100% !important;
    border-collapse: collapse !important;
    font-size: 10px;
  }}

  table.doc-table thead th {{
    position: static !important;
    background: #eee !important;
    color: #000 !important;
    border: 1px solid #ccc !important;
  }}

  table.doc-table td,
  table.doc-table th {{
    color: #000 !important;
    border: 1px solid #ccc !important;
  }}

  .badge {{
    color: #000 !important;
    border: 1px solid #999 !important;
    background: #f3f3f3 !important;
  }}
}}

@media (max-width: 1100px) {{
  .topbar {{
    left: 0;
  }}

  .sidebar {{
    position: relative;
    width: 100%;
    height: auto;
    min-height: auto;
    border-right: 0;
    border-bottom: 1px solid var(--sidebar-border);
  }}

  .main {{
    margin-left: 0;
    padding-top: calc(var(--header-height) + 20px);
  }}
}}

@media (max-width: 760px) {{
  .topbar {{
    position: relative;
    height: auto;
    padding: 18px;
    flex-direction: column;
    align-items: flex-start;
  }}

  .topbar-actions {{
    width: 100%;
  }}

  .ctrl-btn {{
    flex: 1 1 150px;
  }}

  .main {{
    margin-left: 0;
    padding: 18px;
  }}

  .section-header {{
    padding-right: 0;
  }}

  .badge {{
    position: static;
    display: inline-flex;
    margin-top: 12px;
  }}

}}
</style>
</head>

<body>
  <!-- RGVzZW52b2x2aWRvIHBvciBFbWFudWVsIFBlZHJvc2E= -->
  <div class="layout">
    <aside class="sidebar">
      <div class="brand">
        <h2>Power BI Documentation</h2>
      </div>

      <div class="sidebar-divider"></div>

      <div class="nav" id="nav">
        {menu_itens}
      </div>
    </aside>

    <header class="topbar">
      <div class="topbar-meta">
        <h1>{nome_projeto_exibicao}</h1>
        <p>Data de criação da documentação: {data_hora_html}</p>
      </div>

      <div class="topbar-actions">
        <button class="ctrl-btn" id="btnTheme">Modo Escuro</button>
        <button class="ctrl-btn" id="btnShowAll">Mostrar Tudo</button>
        <button class="ctrl-btn" id="btnTop">Topo</button>
        <button class="ctrl-btn primary" id="btnPdf">Exportar</button>
      </div>
    </header>

    <main class="main" id="mainScroll">
      <div id="content">
        {secoes_html}
      </div>
    </main>
  </div>

<script>
(function() {{
  const mainScroll = document.getElementById('mainScroll');
  const nav = document.getElementById('nav');
  const sections = Array.from(document.querySelectorAll('.section'));
  const navButtons = Array.from(document.querySelectorAll('.nav-item'));
  const themeButton = document.getElementById('btnTheme');

  function applyTheme(theme) {{
    document.body.setAttribute('data-theme', theme);
    themeButton.textContent = theme === 'dark' ? 'Modo Claro' : 'Modo Escuro';
    try {{
      localStorage.setItem('doc-theme', theme);
    }} catch (e) {{}}
  }}

  function showOnly(sectionId) {{
    sections.forEach(s => {{
      s.classList.toggle('visible', s.getAttribute('data-section') === sectionId);
    }});

    navButtons.forEach(b => {{
      b.classList.toggle('active', b.getAttribute('data-target') === sectionId);
    }});

    const el = document.getElementById(sectionId);
    if (el) {{
      mainScroll.scrollTo({{ top: el.offsetTop - 8, behavior: 'smooth' }});
    }}
  }}

  function showAll() {{
    sections.forEach(s => s.classList.add('visible'));
    navButtons.forEach(b => b.classList.remove('active'));
    mainScroll.scrollTo({{ top: 0, behavior: 'smooth' }});
  }}

  nav.addEventListener('click', (e) => {{
    const btn = e.target.closest('.nav-item');
    if (!btn) return;

    const target = btn.getAttribute('data-target');
    if (!target) return;

    showOnly(target);
  }});

  document.getElementById('btnShowAll').addEventListener('click', showAll);

  document.getElementById('btnTop').addEventListener('click', () => {{
    mainScroll.scrollTo({{ top: 0, behavior: 'smooth' }});
  }});

  themeButton.addEventListener('click', () => {{
    const current = document.body.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
    applyTheme(current === 'dark' ? 'light' : 'dark');
  }});

  document.getElementById('btnPdf').addEventListener('click', () => {{
    showAll();

    setTimeout(() => {{
      window.print();
    }}, 350);
  }});

  const first = navButtons[0];
  let savedTheme = 'light';
  try {{
    savedTheme = localStorage.getItem('doc-theme') || 'light';
  }} catch (e) {{}}
  applyTheme(savedTheme);

  if (first) {{
    showOnly(first.getAttribute('data-target'));
  }} else {{
    showAll();
  }}
}})();
</script>
</body>
</html>
"""

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
caminho_html = PASTA_OUTPUT / nome_arquivo

with open(caminho_html, "w", encoding="utf-8") as f:
    f.write(html)

print("DOCUMENTACAO GERADA COM SUCESSO!")
print(f"Pasta: {PASTA_OUTPUT}")
print(f"Arquivo HTML: {nome_arquivo}")
print("Para exportar: abra o HTML e clique no botao 'Exportar'.")
