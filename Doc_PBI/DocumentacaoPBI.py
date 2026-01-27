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

roles = filtrar(roles, ["ID","Name"])
permissions = filtrar(permissions, ["ID","TableID", "FilterExpression"])
hierarchies = filtrar(hierarchies, ["ID","TableID", "Name", "Levels"])

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

# ==================================================
# HTML HELPERS
# ==================================================
def html_tabela(df):
    return df.to_html(index=False, escape=False, classes="doc-table")

def safe_len(df):
    return 0 if df is None else len(df)

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
    {"id": "tabelas",         "label": "📁 Tabelas do Modelo",          "desc": "Lista de tabelas do modelo, com visibilidade e descrição.", "df": tables},
    {"id": "colunas",         "label": "📐 Dicionário de Dados (Colunas)","desc": "Colunas, tipos, chaves, nulabilidade e propriedades.",       "df": columns},
    {"id": "medidas",         "label": "📊 Medidas (DAX)",              "desc": "Medidas DAX com expressão e descrição.",                     "df": measures},
    {"id": "relacionamentos", "label": "🔗 Relacionamentos",            "desc": "Relacionamentos entre tabelas e cardinalidade.",            "df": relationships},
    {"id": "powerquery",      "label": "🧠 Cód. Avançado e T. Virtual", "desc": "Consultas / QueryDefinition e modo de carregamento.",        "df": partitions},
    {"id": "roles",           "label": "🔐 Segurança (Roles)",          "desc": "Papéis de segurança configurados.",                         "df": roles},
    {"id": "rls",             "label": "🔐 Segurança (Filtros RLS)",    "desc": "Filtros por tabela usados em RLS.",                          "df": permissions},
    {"id": "hierarquias",     "label": "🧱 Hierarquias",                "desc": "Hierarquias e níveis (levels).",                             "df": hierarchies},
]

menu_itens = "\n".join(
    [f"""
    <button class="nav-item" data-target="{s['id']}" title="{s['label']}">
        <span class="nav-label">{s['label']}</span>
        <span class="nav-count">{safe_len(s['df'])}</span>
    </button>
    """ for s in SECOES]
)

secoes_html = "\n".join(
    [add_secao(s["id"], s["label"], s["desc"], s["df"]) for s in SECOES]
)

# ==================================================
# HTML FINAL (LAYOUT CORRIGIDO)
# ==================================================
html = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Documentação Power BI - {nome_projeto}</title>

<style>
:root {{
  --bg: #0b1220;
  --panel: #0f1b33;
  --panel2: #0d1730;
  --text: #e9eefb;
  --muted: #b9c3dd;
  --line: rgba(255,255,255,0.10);
  --chip: rgba(255,255,255,0.08);
  --accent: #6ea8fe;
  --accent2: #7ee787;
  --shadow: 0 10px 30px rgba(0,0,0,.25);
}}

* {{ box-sizing: border-box; }}

/* TRAVA: NUNCA TER ROLAGEM HORIZONTAL NA PÁGINA */
html, body {{
  margin: 0;
  padding: 0;
  height: 100%;
  overflow-x: hidden;
}}

body {{
  font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, "Noto Sans", "Liberation Sans", sans-serif;
  background: linear-gradient(120deg, #070c18, #0b1220 40%, #0b1220);
  color: var(--text);
}}

a {{ color: var(--accent); }}

/* LAYOUT SEM GRID E SEM FLEX ESTRUTURAL */
.layout {{
  width: 100%;
  height: 100vh;
}}

/* SIDEBAR FIXA */
.sidebar {{
  position: fixed;
  top: 0;
  left: 0;
  width: 320px;
  height: 100vh;
  padding: 20px 18px;
  background: linear-gradient(180deg, var(--panel), var(--panel2));
  border-right: 1px solid var(--line);
  overflow-y: auto;
  overflow-x: hidden;
}}

.brand {{
  display: block;
  padding: 12px 12px 16px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: rgba(255,255,255,0.03);
  box-shadow: var(--shadow);
}}

.brand h1 {{
  margin: 0 0 6px 0;
  font-size: 16px;
  letter-spacing: .2px;
}}

.brand .meta {{
  margin: 0;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.3;
}}

.controls {{
  margin-top: 14px;
}}

.ctrl-btn {{
  width: 49%;
  border: 1px solid var(--line);
  background: rgba(255,255,255,0.04);
  color: var(--text);
  padding: 10px 10px;
  border-radius: 12px;
  cursor: pointer;
  font-size: 12px;
  transition: transform .06s ease, background .2s ease;
}}

.ctrl-btn:hover {{ background: rgba(255,255,255,0.07); }}
.ctrl-btn:active {{ transform: translateY(1px); }}

.nav {{
  margin-top: 16px;
}}

.nav-item {{
  width: 100%;
  text-align: left;
  padding: 10px 12px;
  margin-bottom: 8px;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: rgba(255,255,255,0.03);
  color: var(--text);
  cursor: pointer;
  transition: background .2s ease, border-color .2s ease;
}}

.nav-item:hover {{
  background: rgba(255,255,255,0.06);
  border-color: rgba(255,255,255,0.18);
}}

.nav-item.active {{
  background: rgba(110,168,254,0.15);
  border-color: rgba(110,168,254,0.45);
}}

.nav-label {{
  display: inline-block;
  font-size: 13px;
  line-height: 1.2;
}}

.nav-count {{
  float: right;
  font-size: 12px;
  color: var(--muted);
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--chip);
  border: 1px solid var(--line);
}}

/* CONTEÚDO: SCROLL VERTICAL SOMENTE AQUI */
.main {{
  margin-left: 320px;
  height: 100vh;
  padding: 26px 26px 60px;
  overflow-y: auto;
  overflow-x: hidden;
}}

.header h2 {{
  margin: 0;
  font-size: 20px;
}}

.header p {{
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 13px;
}}

.section {{
  display: none;
  margin-top: 14px;
  padding: 16px 16px 12px;
  background: rgba(255,255,255,0.03);
  border: 1px solid var(--line);
  border-radius: 16px;
  box-shadow: var(--shadow);
}}

.section.visible {{
  display: block;
}}

.section-header {{
  position: relative;
  margin-bottom: 10px;
  padding-right: 120px;
}}

.section-header-text h2 {{
  margin: 0;
  font-size: 16px;
}}

.section-subtitle {{
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 12px;
}}

.badge {{
  position: absolute;
  top: 0;
  right: 0;
  font-size: 12px;
  padding: 5px 10px;
  border-radius: 999px;
  background: rgba(126,231,135,0.12);
  border: 1px solid rgba(126,231,135,0.35);
  color: var(--text);
  white-space: nowrap;
}}

.badge.muted {{
  background: rgba(255,255,255,0.06);
  border-color: var(--line);
  color: var(--muted);
}}

.empty-state {{
  padding: 14px;
  color: var(--muted);
  font-size: 13px;
  border: 1px dashed var(--line);
  border-radius: 12px;
  background: rgba(255,255,255,0.02);
}}

.footer-note {{
  margin-top: 18px;
  color: var(--muted);
  font-size: 12px;
}}

/* TABELAS: SCROLL HORIZONTAL APENAS NO CONTAINER */
.table-wrap {{
  max-width: 100%;
  overflow-x: auto;
  overflow-y: hidden;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: rgba(0,0,0,0.12);
}}

table.doc-table {{
  width: max-content;  /* pode ser maior que o container */
  min-width: 100%;     /* mas se couber, ocupa 100% */
  border-collapse: collapse;
  font-size: 12px;
}}

table.doc-table thead th {{
  position: sticky;
  top: 0;
  background: rgba(255,255,255,0.06);
  backdrop-filter: blur(6px);
  border-bottom: 1px solid var(--line);
  color: var(--text);
  text-align: left;
  padding: 10px 10px;
  white-space: nowrap;
}}

table.doc-table td {{
  border-top: 1px solid var(--line);
  padding: 8px 10px;
  vertical-align: top;
  color: var(--text);
  word-break: break-word;
}}

table.doc-table tr:hover td {{
  background: rgba(255,255,255,0.03);
}}

@media (max-width: 980px) {{
  .sidebar {{
    position: relative;
    width: 100%;
    height: auto;
  }}
  .main {{
    margin-left: 0;
    height: auto;
  }}
}}
</style>
</head>

<body>
  <div class="layout">
    <aside class="sidebar">
      <div class="brand">
        <h1>📘 Documentação Power BI</h1>
        <p class="meta"><strong>Projeto:</strong> {nome_projeto}</p>
        <p class="meta"><strong>Exportado em:</strong> {data_hora_html}</p>

        <div class="controls">
          <button class="ctrl-btn" id="btnShowAll">Mostrar tudo</button>
          <button class="ctrl-btn" id="btnTop">Topo</button>
        </div>
      </div>

      <div class="nav" id="nav">
        {menu_itens}
      </div>
    </aside>

    <main class="main" id="mainScroll">
      <div class="header">
        <div>
          <h2>Seções</h2>
          <p>Clique no menu à esquerda para filtrar e ver somente a seção desejada.</p>
        </div>
      </div>

      <div id="content">
        {secoes_html}
      </div>

      <div class="footer-note">
        Gerado automaticamente via Python • {data_hora_html}
      </div>
    </main>
  </div>

<script>
(function() {{
  const mainScroll = document.getElementById('mainScroll');
  const nav = document.getElementById('nav');
  const sections = Array.from(document.querySelectorAll('.section'));
  const navButtons = Array.from(document.querySelectorAll('.nav-item'));

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

  const first = navButtons[0];
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
with open(PASTA_OUTPUT / nome_arquivo, "w", encoding="utf-8") as f:
    f.write(html)

print("✅ DOCUMENTAÇÃO GERADA COM SUCESSO!")
print(f"📂 Pasta: {PASTA_OUTPUT}")
print(f"📄 Arquivo: {nome_arquivo}")
