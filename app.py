"""MOOC: El proceso del análisis fenomenológico — versión Streamlit.

Lee las notas ya preparadas para la web (carpeta `contenido/`, anonimizadas y con «Sección»)
y las muestra con navegación lateral, recuadros, respuestas plegables y esquemas ampliables.
"""
import re
from pathlib import Path

import streamlit as st

BASE = Path(__file__).parent / "contenido"
MOOC = BASE / "40 Cursos" / "Maestría en educación. - Seminario trabajo de grado" / "MOOC - Análisis fenomenológico"
ADJ = BASE / "60 Adjuntos"

st.set_page_config(
    page_title="MOOC · Análisis fenomenológico",
    page_icon="📘",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {max-width: 980px; padding-top: 2rem;}
    h1 {font-size: 2rem !important;}
    h2 {font-size: 1.45rem !important; margin-top: 1.2rem;}
    h3 {font-size: 1.15rem !important;}
    [data-testid="stSidebarNavLink"] span, [data-testid="stSidebarNav"] a span {
        white-space: normal !important; overflow: visible !important; text-overflow: clip !important;}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------- lectura de notas
def leer(path: Path):
    texto = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", texto, re.S)
    titulo, cuerpo = path.stem, texto
    if m:
        t = re.search(r'^title:\s*"?(.*?)"?\s*$', m.group(1), re.M)
        titulo, cuerpo = (t.group(1) if t else path.stem), m.group(2)
    return titulo, cuerpo


def clave(nombre: str) -> str:
    """Clave estable a partir del nombre de archivo (sin extensión)."""
    if nombre == "index":
        return "inicio"
    if nombre.startswith("202610290100"):
        return "introduccion"
    if nombre.startswith("Rúbrica"):
        return "rubrica-y-plantillas"
    m = re.match(r"\d{12} Sección (\d)", nombre)
    if m:
        return f"seccion-{m.group(1)}"
    return re.sub(r"[^a-z0-9]+", "-", nombre.lower()).strip("-")


NOTAS = {}  # clave -> (nombre de archivo, título, cuerpo)
for p in [BASE / "index.md"] + sorted(MOOC.glob("*.md")):
    t, c = leer(p)
    NOTAS[clave(p.stem)] = (p.stem, t, c)
POR_NOMBRE = {v[0]: k for k, v in NOTAS.items()}
ORDEN = ["inicio", "introduccion"] + [f"seccion-{i}" for i in range(1, 9)] + ["rubrica-y-plantillas"]
ORDEN = [k for k in ORDEN if k in NOTAS]


# ---------------------------------------------------------------- conversión de Obsidian
WIKI = re.compile(r"\[\[([^\]|#\\]+)(#[^\]|\\]*)?(?:\\?\|([^\]]+))?\]\]")
ZOOM = re.compile(r'<a class="zoom-abrir".*?class="zoom-capa">.*?</span>', re.S)
IMG = re.compile(r'<img src="/60-adjuntos/([^"]+)" alt="([^"]*)"[^>]*>')


def texto_enlaces(s: str) -> str:
    """Los enlaces internos se muestran en negrita; la navegación está en el menú y los botones."""
    def rep(m):
        alias = m.group(3) or re.sub(r"^\d{12}\s+", "", m.group(1)).strip()
        return f"**{alias}**"
    return WIKI.sub(rep, s)


def mostrar_imagen(bloque: str):
    m = IMG.search(bloque)
    if not m:
        return
    archivo, alt = m.group(1), m.group(2)
    candidatos = [p for p in ADJ.iterdir() if p.name.lower().replace(" ", "-") == archivo.lower()]
    if candidatos:
        st.image(str(candidatos[0]), caption=alt + " · usa ⛶ (arriba a la derecha de la imagen) para verla a pantalla completa",
                 width="stretch")


CALLOUT = re.compile(r"^> \[!(\w+)\]([-+]?)\s*(.*)$")
ESTILO = {"info": st.info, "note": st.info, "tip": st.success, "warning": st.warning,
          "caution": st.warning, "danger": st.error, "question": st.info, "example": st.info}


def render(cuerpo: str):
    # Quitar navegación «← … · … →» (se reemplaza por botones)
    cuerpo = re.sub(r"^←.*$\n?", "", cuerpo, flags=re.M)
    lineas = cuerpo.split("\n")
    buffer = []

    def volcar():
        if buffer:
            md = "\n".join(buffer).strip()
            if md:
                partes = ZOOM.split(md)
                imgs = ZOOM.findall(md)
                for i, parte in enumerate(partes):
                    if parte.strip():
                        st.markdown(texto_enlaces(parte))
                    if i < len(imgs):
                        mostrar_imagen(imgs[i])
            buffer.clear()

    i = 0
    while i < len(lineas):
        m = CALLOUT.match(lineas[i])
        if m:
            volcar()
            tipo, plegado, titulo = m.group(1).lower(), m.group(2), m.group(3).strip()
            contenido = []
            i += 1
            while i < len(lineas) and lineas[i].startswith(">"):
                contenido.append(re.sub(r"^> ?", "", lineas[i]))
                i += 1
            texto = texto_enlaces("\n".join(contenido).strip())
            if plegado == "-":
                with st.expander(titulo or "Ver"):
                    st.markdown(texto)
            else:
                cuerpo_callout = (f"**{titulo}**\n\n" if titulo and contenido else "") + (texto or titulo)
                ESTILO.get(tipo, st.info)(texto_enlaces(cuerpo_callout) if not contenido else cuerpo_callout)
            continue
        buffer.append(lineas[i])
        i += 1
    volcar()


# ---------------------------------------------------------------- páginas
def pagina(k):
    nombre, titulo, cuerpo = NOTAS[k]
    st.title(titulo)
    if k == "inicio":
        primer_parrafo = next(b for b in cuerpo.strip().split("\n\n") if b.strip())
        st.markdown(texto_enlaces(primer_parrafo))
        c1, c2 = st.columns(2)
        c1.page_link(PAGINAS["introduccion"], label="Empezar el curso →", icon="🧭", width="stretch")
        c2.page_link(PAGINAS["rubrica-y-plantillas"], label="Rúbrica y plantillas del proyecto final", icon="📝", width="stretch")
        st.subheader("Secciones")
        for j in range(1, 9):
            kk = f"seccion-{j}"
            st.page_link(PAGINAS[kk], label=NOTAS[kk][1], icon="📄")
        st.caption("Maestría en Educación UPTC · Elver Chaparro Cardozo")
        return
    render(cuerpo)
    # Botones anterior / siguiente
    idx = ORDEN.index(k)
    st.divider()
    c1, c2 = st.columns(2)
    if idx > 0:
        c1.page_link(PAGINAS[ORDEN[idx - 1]], label="← " + NOTAS[ORDEN[idx - 1]][1], width="stretch")
    if idx < len(ORDEN) - 1:
        c2.page_link(PAGINAS[ORDEN[idx + 1]], label=NOTAS[ORDEN[idx + 1]][1] + " →", width="stretch")
    st.caption("Maestría en Educación UPTC · Elver Chaparro Cardozo")


def hacer(k):
    def f():
        pagina(k)
    f.__name__ = "p_" + k.replace("-", "_")
    return f


NAV = {"inicio": "Inicio", "introduccion": "Introducción", "rubrica-y-plantillas": "Rúbrica y plantillas",
       "seccion-1": "1 · Qué busca el análisis", "seccion-2": "2 · Pregunta y presuposiciones",
       "seccion-3": "3 · Material experiencial", "seccion-4": "4 · Lectura holística y selectiva",
       "seccion-5": "5 · Unidades y aspectos vividos", "seccion-6": "6 · Temas esenciales",
       "seccion-7": "7 · Los cuatro existenciales", "seccion-8": "8 · Escritura y validación"}
ICONOS = {"inicio": "🏠", "introduccion": "🧭", "rubrica-y-plantillas": "📝"}
PAGINAS = {
    k: st.Page(hacer(k), title=NAV.get(k, NOTAS[k][1]),
               icon=ICONOS.get(k, "📄"), url_path=k, default=(k == "inicio"))
    for k in ORDEN
}

with st.sidebar:
    st.markdown("### Análisis fenomenológico · MOOC")
    st.caption("Maestría en Educación UPTC · Elver Chaparro Cardozo")

nav = st.navigation(
    {
        "Curso": [PAGINAS[k] for k in ["inicio", "introduccion"] if k in PAGINAS],
        "Secciones": [PAGINAS[k] for k in ORDEN if k.startswith("seccion-")],
        "Proyecto final": [PAGINAS[k] for k in ["rubrica-y-plantillas"] if k in PAGINAS],
    }
)
nav.run()
