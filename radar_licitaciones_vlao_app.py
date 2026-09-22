import ast
from datetime import datetime, timedelta
import io
import urllib.parse
import unicodedata
import re
import pandas as pd
import requests
import streamlit as st

# ==============================================================================
# CONFIGURACIÓN DE PÁGINA Y ESTILOS - BID WIN VLAO
# ============================================================================= proposal
st.set_page_config(
    page_title="BID WIN VLAO - Oportunidades SECOP II 2026",
    layout="wide",
    page_icon="🎯"
)

st.markdown("""
    <style>
    .brand-title {
        font-size: 2.6rem;
        font-weight: 900;
        color: #1E3A8A;
        margin-bottom: 0px;
        letter-spacing: -0.5px;
    }
    .brand-slogan {
        font-size: 1.2rem;
        font-weight: 600;
        color: #2563EB;
        margin-bottom: 4px;
    }
    .brand-line {
        font-size: 0.98rem;
        color: #475569;
        margin-bottom: 22px;
    }
    .stMetric {
        background-color: #F8FAFC;
        padding: 14px;
        border-radius: 10px;
        border-left: 5px solid #1E3A8A;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    .opportunity-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-left: 6px solid #2563EB;
        padding: 18px;
        border-radius: 10px;
        margin-bottom: 16px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .card-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #0F172A;
    }
    .card-badge {
        background-color: #EFF6FF;
        color: #1D4ED8;
        padding: 6px 12px;
        border-radius: 14px;
        font-size: 0.92rem;
        font-weight: 700;
    }
    .phase-badge {
        background-color: #F1F5F9;
        color: #334155;
        padding: 3px 8px;
        border-radius: 6px;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

# Encabezado Oficial
st.markdown('<div class="brand-title">🎯 BID WIN VLAO</div>', unsafe_allow_html=True)
st.markdown('<div class="brand-slogan">"Te acerca a tu próximo negocio con el Estado"</div>', unsafe_allow_html=True)
st.markdown('<div class="brand-line"><b>Línea de Negocio: VLAO INGENIERÍA S.A.S.</b> (Mantenimiento, Obras Civiles, Cubiertas, Instalaciones Eléctricas, Iluminación, Ferretería, Plomería e Interventoría)</div>', unsafe_allow_html=True)
st.divider()

# ==============================================================================
# DICCIONARIOS Y LISTAS DE SELECCIÓN PARAMETRIZABLES
# ==============================================================================
SECTORES_UNSPSC = {
    "🌐 Todos los Sectores de la Economía (Sin Filtro Previo)": "TODOS",
    "💼 Portafolio Combinado VLAO INGENIERÍA (3116, 7210, 3912, 8110, etc.)": "VLAO_COMBINADO",
    "🛠️ 3116 / 3010 - Ferretería, Herrajes y Materiales de Construcción": "3116|3010",
    "🏗️ 7210 / 7212 / 7214 / 7215 - Obras Civiles, Edificaciones y Mantenimiento": "7210|7212|7214|7215",
    "⚡ 3912 / 3911 / 2612 - Equipos Eléctricos, Iluminación y Redes": "3912|3911|2612",
    "📐 8110 / 8010 - Ingeniería, Consultoría e Interventoría": "8110|8010",
    "🎨 3121 / 3015 - Pinturas, Acabados e Impermeabilización": "3121|3015",
    "🚰 4014 / 4017 / 3018 - Tuberías, Plomería y Sanitarios": "4014|4017|3018",
    "🔧 2711 / 2510 - Herramientas de Mano y Maquinaria": "2711|2510"
}

SECTORES_VLAO_SEGMENTOS = ['72', '39', '31', '30', '40', '81', '80', '27', '25']

DEPARTAMENTOS_COLOMBIA = [
    "Amazonas", "Antioquia", "Arauca", "Atlántico", "Bogotá D.C.", "Bolívar",
    "Boyacá", "Caldas", "Caquetá", "Casanare", "Cauca", "Cesar", "Chocó", "Córdoba",
    "Cundinamarca", "Guainía", "Guaviare", "Huila", "La Guajira", "Magdalena", "Meta",
    "Nariño", "Norte de Santander", "Putumayo", "Quindío", "Risaralda", "San Andrés",
    "Santander", "Sucre", "Tolima", "Valle del Cauca", "Vaupés", "Vichada"
]

MUNICIPIOS_PRINCIPALES = [
    "Bogotá D.C.", "Medellín", "Cali", "Barranquilla", "Cartagena", "Bucaramanga",
    "Cúcuta", "Pereira", "Santa Marta", "Ibagué", "Pasto", "Manizales", "Neiva",
    "Villavicencio", "Armenia", "Popayán", "Valledupar", "Montería", "Sincelejo",
    "Tunja", "Florencia", "Yopal", "Quibdó", "Arauca", "Mocoa", "San José del Guaviare",
    "Puerto Carreño", "Mitú", "Inírida", "Leticia", "San Andrés", "Soacha", "Bello",
    "Envigado", "Soledad", "Floridablanca", "Girón", "Piedecuesta", "Palmira", "Buenaventura",
    "Tuluá", "Cartago", "Sogamoso", "Duitama", "Chía", "Zipaquirá", "Facatativá", "Fusagasugá",
    "Girardot", "Espinal", "Pitalito", "Garzón", "Aguachica", "Ocaña", "Tumaco", "Ipiales"
]

MODALIDADES_LISTA = [
    "Todas las Modalidades",
    "Mínima Cuantía",
    "Selección Abreviada",
    "Licitación Pública",
    "Concurso de Méritos",
    "Contratación Directa",
    "Régimen Especial"
]

TIPOS_CONTRATO_LISTA = [
    "Todos los Tipos",
    "Obra Pública",
    "Suministro",
    "Interventoría / Consultoría",
    "Compraventa",
    "Prestación de Servicios"
]

ESTADOS_RESUMEN_LISTA = [
    "Todos los Estados",
    "Borrador",
    "Publicado",
    "Presentación de Ofertas",
    "Convocatoria",
    "Evaluación",
    "Adjudicado"
]

FASES_LISTA = [
    "Todas las Fases",
    "Planeación",
    "Selección",
    "Presentación de ofertas",
    "Borrador"
]

VENTANAS_LISTA = [
    "Últimos 30 días",
    "Últimos 60 días",
    "Últimos 90 días",
    "Todo el Año 2026"
]

# ==============================================================================
# FUNCIONES AUXILIARES: NORMALIZACIÓN, FORMATOS Y LÓGICA DE FILTRADO
# ==============================================================================
def normalizar_texto(texto):
    if not texto or pd.isna(texto):
        return ""
    texto_str = str(texto)
    nfkd = unicodedata.normalize('NFD', texto_str)
    sin_tildes = "".join([c for c in nfkd if unicodedata.category(c) != 'Mn'])
    return sin_tildes.lower().strip()

def clean_alpha(texto):
    norm = normalizar_texto(texto)
    return re.sub(r'[^a-z0-9]', '', norm)

def get_soda_location_conditions(field_name, sel_list):
    """Genera cláusulas SoQL tolerantes a tildes y variaciones para la SODA API."""
    conds = []
    for val in sel_list:
        if not val or val == 'TODOS':
            continue
        v_raw = str(val).lower().strip()
        nfkd = unicodedata.normalize('NFD', str(val))
        v_no_tilde = ''.join([c for c in nfkd if unicodedata.category(c) != 'Mn']).lower().strip()
        
        v_stem = re.sub(r'[^a-z0-9]', '', v_no_tilde)
        if len(v_stem) > 5:
            v_stem = v_stem[:5]
            
        sub_or = []
        if v_raw:
            sub_or.append(f"lower({field_name}) like '%{v_raw}%'")
        if v_no_tilde and v_no_tilde != v_raw:
            sub_or.append(f"lower({field_name}) like '%{v_no_tilde}%'")
        if v_stem and len(v_stem) >= 4 and v_stem not in [v_raw, v_no_tilde]:
            sub_or.append(f"lower({field_name}) like '%{v_stem}%'")
            
        if sub_or:
            conds.append(f"({' OR '.join(sub_or)})")
    return conds

def match_location(val_from_dataset, list_selected):
    if not list_selected:
        return True
    val_clean = clean_alpha(val_from_dataset)
    if not val_clean:
        return False
    for sel in list_selected:
        sel_clean = clean_alpha(sel)
        if not sel_clean:
            continue
        if "bogota" in sel_clean and "bogota" in val_clean:
            return True
        if sel_clean in val_clean or val_clean in sel_clean:
            return True
    return False

def match_modalidad(val_mod, sel_mod):
    if sel_mod == "Todas las Modalidades" or not sel_mod:
        return True
    val_n = normalizar_texto(val_mod)
    sel_n = normalizar_texto(sel_mod)
    if "minima" in sel_n:
        return "minima" in val_n or "mínima" in val_n
    if "abreviada" in sel_n:
        return "abreviad" in val_n
    if "licitacion" in sel_n:
        return "licitac" in val_n
    if "concurso" in sel_n:
        return "concurso" in val_n
    if "directa" in sel_n:
        return "directa" in val_n
    if "regimen" in sel_n:
        return "regimen" in val_n or "régimen" in val_n
    return True

def match_tipo_contrato(val_tipo, sel_tipo):
    if sel_tipo == "Todos los Tipos" or not sel_tipo:
        return True
    val_n = normalizar_texto(val_tipo)
    sel_n = normalizar_texto(sel_tipo)
    if "obra" in sel_n:
        return "obra" in val_n
    if "suministro" in sel_n:
        return "suministr" in val_n
    if "interventoria" in sel_n or "consultoria" in sel_n:
        return "interventor" in val_n or "consultor" in val_n or "estudio" in val_n
    if "compraventa" in sel_n:
        return "compra" in val_n or "venta" in val_n
    if "prestacion" in sel_n or "servicios" in sel_n:
        return "servicio" in val_n or "prestac" in val_n
    return True

def match_estado(val_est, sel_est):
    if sel_est == "Todos los Estados" or not sel_est:
        return True
    val_n = normalizar_texto(val_est)
    sel_n = normalizar_texto(sel_est)
    if "oferta" in sel_n or "convocatoria" in sel_n:
        return "oferta" in val_n or "convocatoria" in val_n or "presentac" in val_n or "publicad" in val_n
    if "borrador" in sel_n:
        return "borrador" in val_n
    if "publicado" in sel_n:
        return "publicad" in val_n or "convocatoria" in val_n or "oferta" in val_n
    if "evaluacion" in sel_n:
        return "evalua" in val_n
    if "adjudicado" in sel_n:
        return "adjudic" in val_n
    return True

def match_fase(val_fase, sel_fase):
    if sel_fase == "Todas las Fases" or not sel_fase:
        return True
    val_n = normalizar_texto(val_fase)
    sel_n = normalizar_texto(sel_fase)
    if "planeac" in sel_n:
        return "planeac" in val_n
    if "selecc" in sel_n:
        return "selecc" in val_n
    if "oferta" in sel_n or "presentac" in sel_n:
        return "oferta" in val_n or "presentac" in val_n
    if "borrador" in sel_n:
        return "borrador" in val_n
    return True

def formato_pesos_cop(valor):
    try:
        val = float(valor)
        if pd.isna(val) or val == 0:
            return "$ 0 COP"
        return f"$ {val:,.0f} COP".replace(",", ".")
    except Exception:
        return "$ 0 COP"

def limpiar_url_secop(val):
    if pd.isna(val) or not val:
        return ""
    if isinstance(val, dict):
        return str(val.get('url', '')).strip()
    val_str = str(val).strip()
    if val_str.startswith("{") and ("'url':" in val_str or '"url":' in val_str):
        try:
            d = ast.literal_eval(val_str)
            if isinstance(d, dict):
                return str(d.get('url', '')).strip()
        except Exception:
            pass
    if val_str.startswith("http://") or val_str.startswith("https://"):
        return val_str
    return ""

def parsear_fecha_secop(val):
    if pd.isna(val) or not val:
        return pd.NaT, "Por definir"
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ['none', 'nan', 'null', 'nat']:
        return pd.NaT, "Por definir"
    try:
        dt = pd.to_datetime(val_str, errors='coerce')
        if pd.notna(dt):
            if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
                dt = dt.tz_localize(None)
            elif hasattr(dt, 'tz') and dt.tz is not None:
                dt = dt.tz_localize(None)
            return dt, dt.strftime('%Y-%m-%d')
    except Exception:
        pass
    return pd.NaT, val_str[:10] if len(val_str) >= 10 else val_str

def get_index_safe(lst, item):
    try:
        return lst.index(item)
    except Exception:
        return 0

# ==============================================================================
# CONEXIÓN Y DESCARGA A SODA API (DATOS.GOV.CO - STRICT 2026 - SERVER-SIDE QUERY)
# ==============================================================================
@st.cache_data(ttl=300)
def descargar_secop_2026(
    dias_ventana=365,
    sector_codigo="TODOS",
    modalidad_sel="Todas las Modalidades",
    dptos_sel=None,
    ciudades_sel=None,
    tipo_contrato_sel="Todos los Tipos",
    limite=5000
):
    base_url = "https://www.datos.gov.co/resource/p6dx-8zbt.json"
    
    fecha_inicio_2026 = "2026-01-01T00:00:00"
    if dias_ventana != 365:
        f_calculada = (datetime.now() - timedelta(days=dias_ventana)).strftime("%Y-%m-%dT00:00:00")
        if f_calculada > fecha_inicio_2026:
            fecha_inicio_2026 = f_calculada

    select_cols = (
        "referencia_del_proceso,entidad,departamento_entidad,ciudad_entidad,"
        "codigo_principal_de_categoria,nombre_del_procedimiento,descripci_n_del_procedimiento,"
        "precio_base,modalidad_de_contratacion,tipo_de_contrato,estado_resumen,fase,"
        "fecha_de_publicacion_del,fecha_de_ultima_publicaci,fecha_de_recepcion_de,urlproceso"
    )

    condiciones = [f"fecha_de_publicacion_del >= '{fecha_inicio_2026}'"]

    # 1. Filtro Departamento & Ciudad en Servidor con tolerancia a tildes
    loc_conds = []
    if dptos_sel:
        loc_conds.extend(get_soda_location_conditions("departamento_entidad", dptos_sel))
    if ciudades_sel:
        loc_conds.extend(get_soda_location_conditions("ciudad_entidad", ciudades_sel))
    if loc_conds:
        condiciones.append(f"({' OR '.join(loc_conds)})")

    # 2. UNSPSC Filter
    if sector_codigo == "VLAO_COMBINADO":
        sub_c = [f"codigo_principal_de_categoria like '%{s}%'" for s in SECTORES_VLAO_SEGMENTOS]
        condiciones.append(f"({' OR '.join(sub_c)})")
    elif sector_codigo != "TODOS":
        cods = sector_codigo.split('|')
        sub_c = [f"codigo_principal_de_categoria like '%{c}%'" for c in cods]
        condiciones.append(f"({' OR '.join(sub_c)})")

    # 3. Modalidad Filter
    if "Mínima" in modalidad_sel:
        condiciones.append("(lower(modalidad_de_contratacion) like '%minima%' or lower(modalidad_de_contratacion) like '%mínima%')")
    elif "Abreviada" in modalidad_sel:
        condiciones.append("lower(modalidad_de_contratacion) like '%abreviad%'")
    elif "Licitación" in modalidad_sel:
        condiciones.append("lower(modalidad_de_contratacion) like '%licitac%'")
    elif "Concurso" in modalidad_sel:
        condiciones.append("lower(modalidad_de_contratacion) like '%concurso%'")
    elif "Directa" in modalidad_sel:
        condiciones.append("lower(modalidad_de_contratacion) like '%directa%'")

    # 4. Tipo Contrato Filter
    if tipo_contrato_sel != "Todos los Tipos":
        q_t = normalizar_texto(tipo_contrato_sel.split(' ')[0])
        if q_t:
            condiciones.append(f"lower(tipo_de_contrato) like '%{q_t[:4]}%'")

    params = {
        "$select": select_cols,
        "$where": " AND ".join(condiciones),
        "$order": "fecha_de_publicacion_del DESC",
        "$limit": str(limite)
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        resp = requests.get(url, headers=headers, timeout=35)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        # Fallback de seguridad abierto si SoQL es demasiado complejo
        conds_fb = [f"fecha_de_publicacion_del >= '{fecha_inicio_2026}'"]
        params_fb = {
            "$select": select_cols,
            "$where": " AND ".join(conds_fb),
            "$order": "fecha_de_publicacion_del DESC",
            "$limit": str(limite)
        }
        url_fb = f"{base_url}?{urllib.parse.urlencode(params_fb)}"
        resp = requests.get(url_fb, headers=headers, timeout=35)
        resp.raise_for_status()
        data = resp.json()

    df = pd.DataFrame(data)

    if not df.empty:
        if 'urlproceso' in df.columns:
            df['urlproceso'] = df['urlproceso'].apply(limpiar_url_secop)
        else:
            df['urlproceso'] = ""

        if 'precio_base' in df.columns:
            df['precio_num'] = pd.to_numeric(df['precio_base'], errors='coerce').fillna(0)
            df['precio_formateado'] = df['precio_num'].apply(formato_pesos_cop)
        else:
            df['precio_num'] = 0
            df['precio_formateado'] = "$ 0 COP"

        if 'fecha_de_publicacion_del' in df.columns:
            res_pub = [parsear_fecha_secop(v) for v in df['fecha_de_publicacion_del']]
            df['fecha_pub_dt'] = [r[0] for r in res_pub]
            df['fecha_pub_clean'] = [r[1] for r in res_pub]
        else:
            df['fecha_pub_dt'] = pd.NaT
            df['fecha_pub_clean'] = "Por definir"

        if 'fecha_de_ultima_publicaci' in df.columns:
            res_ult = [parsear_fecha_secop(v) for v in df['fecha_de_ultima_publicaci']]
            df['fecha_ult_pub_clean'] = [r[1] for r in res_ult]
        else:
            df['fecha_ult_pub_clean'] = df['fecha_pub_clean']

        if 'fecha_de_recepcion_de' in df.columns:
            res_cie = [parsear_fecha_secop(v) for v in df['fecha_de_recepcion_de']]
            df['fecha_cierre_dt'] = [r[0] for r in res_cie]
            df['fecha_cierre_clean'] = [r[1] if r[1] != "Por definir" else "Por definir en pliegos" for r in res_cie]
        else:
            df['fecha_cierre_dt'] = pd.NaT
            df['fecha_cierre_clean'] = "Por definir en pliegos"

    return df

# ==============================================================================
# EXPORTACIÓN SEGURA A EXCEL (OPENPYXL)
# ==============================================================================
def exportar_df_a_excel(df_filtrado):
    df_export = df_filtrado.copy()
    columnas_visibles = {
        'referencia_del_proceso': 'Referencia SECOP II',
        'entidad': 'Entidad Compradora',
        'departamento_entidad': 'Departamento',
        'ciudad_entidad': 'Ciudad / Municipio',
        'codigo_principal_de_categoria': 'Código UNSPSC / Categoría',
        'nombre_del_procedimiento': 'Título convocatoria',
        'descripci_n_del_procedimiento': 'Objeto detallado del contrato',
        'precio_formateado': 'Presupuesto Base ($ COP)',
        'modalidad_de_contratacion': 'Modalidad',
        'tipo_de_contrato': 'Tipo de Contrato',
        'estado_resumen': 'Estado',
        'fase': 'Fase',
        'fecha_pub_clean': 'Fecha Publicación',
        'fecha_ult_pub_clean': 'Fecha Última Publicación',
        'fecha_cierre_clean': 'Fecha Cierre Ofertas',
        'urlproceso': 'Link SECOP II'
    }
    cols = [c for c in columnas_visibles.keys() if c in df_export.columns]
    df_export = df_export[cols].rename(columns={c: columnas_visibles[c] for c in cols})

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Oportunidades_BID_WIN_VLAO')
    return buffer.getvalue()

# ==============================================================================
# ⚙️ CONSOLA DE FILTROS DE ENTRADA (MANTENIMIENTO DE ESTADO EN SESSION_STATE)
# ==============================================================================
st.markdown("### ⚙️ Selecciona y aplica los filtros para encontrar la oportunidad a tu medida")
st.caption("Configura los parámetros clave de ubicación, modalidad y sector para realizar la consulta en SECOP II.")

# Cargar session state previo para que los controles no se borren
cfg_saved = st.session_state.get("filtros_guardados", {})

with st.form(key="form_filtros_entrada"):
    # Fila 1: Ubicación Geográfica (Departamento + Municipio Selección)
    c1, c2 = st.columns(2)
    
    with c1:
        dptos_sel = st.multiselect(
            "📍 Ubicación Geográfica (Departamento):",
            options=DEPARTAMENTOS_COLOMBIA,
            default=cfg_saved.get("dptos_sel", []),
            help="Selecciona uno o varios departamentos."
        )
    with c2:
        ciudades_sel = st.multiselect(
            "🏙️ Ciudad / Municipio (Selección Desplegable):",
            options=MUNICIPIOS_PRINCIPALES,
            default=cfg_saved.get("ciudades_sel", []),
            help="Selecciona una o varias ciudades/municipios principales."
        )

    # Fila 2: Definición Jurídica y Contractual
    c3, c4, c5 = st.columns(3)
    with c3:
        idx_mod = get_index_safe(MODALIDADES_LISTA, cfg_saved.get("modalidad_sel", "Todas las Modalidades"))
        modalidad_sel = st.selectbox(
            "📜 Modalidad de Contratación:",
            options=MODALIDADES_LISTA,
            index=idx_mod
        )
    with c4:
        idx_tipo = get_index_safe(TIPOS_CONTRATO_LISTA, cfg_saved.get("tipo_contrato_sel", "Todos los Tipos"))
        tipo_contrato_sel = st.selectbox(
            "📑 Tipo de Contrato:",
            options=TIPOS_CONTRATO_LISTA,
            index=idx_tipo
        )
    with c5:
        sectores_keys = list(SECTORES_UNSPSC.keys())
        idx_sec = get_index_safe(sectores_keys, cfg_saved.get("sector_sel", sectores_keys[0]))
        sector_sel = st.selectbox(
            "🏢 Sector / Categoría UNSPSC:",
            options=sectores_keys,
            index=idx_sec
        )

    # Fila 3: Estado, Fase & Ventana de Tiempos
    c6, c7, c8 = st.columns(3)
    with c6:
        idx_est = get_index_safe(ESTADOS_RESUMEN_LISTA, cfg_saved.get("estado_sel", "Todos los Estados"))
        estado_sel = st.selectbox(
            "📌 Estado del Proceso (estado_resumen):",
            options=ESTADOS_RESUMEN_LISTA,
            index=idx_est
        )
    with c7:
        idx_fase = get_index_safe(FASES_LISTA, cfg_saved.get("fase_sel", "Todas las Fases"))
        fase_sel = st.selectbox(
            "📋 Etapa / Fase SECOP II (fase):",
            options=FASES_LISTA,
            index=idx_fase
        )
    with c8:
        idx_vent = get_index_safe(VENTANAS_LISTA, cfg_saved.get("ventana_tiempo", "Todo el Año 2026"))
        ventana_tiempo = st.selectbox(
            "📅 Ventana de Tiempos (Strict 2026):",
            options=VENTANAS_LISTA,
            index=idx_vent
        )

    # Fila 4: Criterios Adicionales & Anti-OPS
    c9, c10 = st.columns([2, 1])
    with c9:
        palabra_clave = st.text_input(
            "🔎 Búsqueda Libre por Palabra Clave (en título u objeto):",
            value=cfg_saved.get("palabra_clave", ""),
            placeholder="Ej: cubierta, ferretería, mantenimiento, redes, impermeabilización..."
        )
    with c10:
        st.write("")
        st.write("")
        filtro_anti_ops = st.checkbox(
            "🛡️ Filtro Anti-OPS (Excluir Contratación Directa PN)",
            value=cfg_saved.get("filtro_anti_ops", False),
            help="Excluye servicios profesionales individuales de apoyo a la gestión cuando esté marcada."
        )

    st.markdown("---")
    btn_buscar = st.form_submit_button(
        label="🚀 BUSCAR OPORTUNIDADES DE NEGOCIO EN SECOP II",
        use_container_width=True,
        type="primary"
    )

# Persistencia de Filtros en Session State al enviar formulario
if btn_buscar:
    st.session_state["ejecutado_busqueda"] = True
    st.session_state["filtros_guardados"] = {
        "dptos_sel": dptos_sel,
        "ciudades_sel": ciudades_sel,
        "modalidad_sel": modalidad_sel,
        "tipo_contrato_sel": tipo_contrato_sel,
        "sector_sel": sector_sel,
        "estado_sel": estado_sel,
        "fase_sel": fase_sel,
        "ventana_tiempo": ventana_tiempo,
        "palabra_clave": palabra_clave,
        "filtro_anti_ops": filtro_anti_ops
    }

# ==============================================================================
# 📋 OPORTUNIDADES PARA TU SELECCIÓN (MATRIZ DE RESULTADOS)
# ==============================================================================
if st.session_state.get("ejecutado_busqueda"):
    cfg = st.session_state.get("filtros_guardados", {})

    m_dias = 365
    v_t = cfg.get("ventana_tiempo", "Todo el Año 2026")
    if "30" in v_t:
        m_dias = 30
    elif "60" in v_t:
        m_dias = 60
    elif "90" in v_t:
        m_dias = 90

    s_sel = cfg.get("sector_sel", "🌐 Todos los Sectores de la Economía (Sin Filtro Previo)")
    cod_sector = SECTORES_UNSPSC.get(s_sel, "TODOS")
    m_sel = cfg.get("modalidad_sel", "Todas las Modalidades")
    sel_dptos = cfg.get("dptos_sel", [])
    sel_ciudades = cfg.get("ciudades_sel", [])
    sel_tipo = cfg.get("tipo_contrato_sel", "Todos los Tipos")

    with st.spinner("🚀 Cargando oportunidades de SECOP II (2026)..."):
        try:
            df_raw = descargar_secop_2026(
                dias_ventana=m_dias,
                sector_codigo=cod_sector,
                modalidad_sel=m_sel,
                dptos_sel=sel_dptos,
                ciudades_sel=sel_ciudades,
                tipo_contrato_sel=sel_tipo,
                limite=5000
            )
        except Exception as e:
            st.error(f"Error de conexión con Datos Abiertos: {e}")
            df_raw = pd.DataFrame()

    if not df_raw.empty:
        df = df_raw.copy()

        # ----------------------------------------------------------------------
        # APLICACIÓN DE FILTROS RIGUROSOS Y ROBUSTOS EN PANDAS
        # ----------------------------------------------------------------------
        
        # 1. Departamento
        if sel_dptos and 'departamento_entidad' in df.columns:
            df = df[df['departamento_entidad'].apply(lambda val: match_location(val, sel_dptos))]

        # 2. Ciudad / Municipio
        if sel_ciudades and 'ciudad_entidad' in df.columns:
            df = df[df['ciudad_entidad'].apply(lambda val: match_location(val, sel_ciudades))]

        # 3. Tipo de Contrato
        if sel_tipo != "Todos los Tipos" and 'tipo_de_contrato' in df.columns:
            df = df[df['tipo_de_contrato'].apply(lambda val: match_tipo_contrato(val, sel_tipo))]

        # 4. Estado Resumen
        sel_est = cfg.get("estado_sel", "Todos los Estados")
        if sel_est != "Todos los Estados" and 'estado_resumen' in df.columns:
            df = df[df['estado_resumen'].apply(lambda val: match_estado(val, sel_est))]

        # 5. Fase
        sel_fase = cfg.get("fase_sel", "Todas las Fases")
        if sel_fase != "Todas las Fases" and 'fase' in df.columns:
            df = df[df['fase'].apply(lambda val: match_fase(val, sel_fase))]

        # 6. Modalidad (Filtro en Pandas complementario)
        if m_sel != "Todas las Modalidades" and 'modalidad_de_contratacion' in df.columns:
            df = df[df['modalidad_de_contratacion'].apply(lambda val: match_modalidad(val, m_sel))]

        # 7. Filtro Anti-OPS
        if cfg.get("filtro_anti_ops") and 'modalidad_de_contratacion' in df.columns and 'nombre_del_procedimiento' in df.columns:
            palabras_ops = ['prestacion de servicios', 'honorarios', 'apoyo a la gestion', 'persona natural', 'ops']
            def es_ops(row):
                mod = str(row.get('modalidad_de_contratacion', '')).lower()
                nom = normalizar_texto(row.get('nombre_del_procedimiento', ''))
                if 'directa' in mod:
                    if any(p in nom for p in palabras_ops):
                        return True
                return False
            df = df[~df.apply(es_ops, axis=1)]

        # 8. Palabra Clave Libre
        kw_p = cfg.get("palabra_clave", "").strip()
        if kw_p:
            kw_norm = normalizar_texto(kw_p)
            df = df[
                df['nombre_del_procedimiento'].apply(normalizar_texto).str.contains(kw_norm) |
                df['descripci_n_del_procedimiento'].apply(normalizar_texto).str.contains(kw_norm)
            ]

        # ----------------------------------------------------------------------
        # ENCABEZADO DE SECCIÓN Y FILTRO LOCAL DE ENTIDAD COMPRADORA
        # ----------------------------------------------------------------------
        st.markdown("---")
        st.markdown("### 📋 Oportunidades para tu selección")
        
        st.markdown("#### 🔍 Filtro Específico por Entidad Compradora en Resultados")
        c_ent1, c_ent2 = st.columns([2.5, 1])
        with c_ent1:
            entidad_query_fase2 = st.text_input(
                "🏢 Buscar / Filtrar por Cliente Estatal (Entidad Compradora):",
                value="",
                placeholder="Ej: SENA, ICBF, Registraduría, Ejército, Alcaldía de Neiva, Gobernación, Hospital...",
                key="input_entidad_fase2"
            )
        with c_ent2:
            st.write("") # Spacer
            st.caption("Filtra instantáneamente la entidad dentro de las oportunidades seleccionadas.")

        if entidad_query_fase2.strip() and 'entidad' in df.columns:
            q_e2 = normalizar_texto(entidad_query_fase2)
            df = df[df['entidad'].apply(normalizar_texto).str.contains(q_e2)]

        # ----------------------------------------------------------------------
        # A. MÉTRICAS RÁPIDAS SUPERIORES
        # ----------------------------------------------------------------------
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric(
                label="🎯 Total Licitaciones Encontradas",
                value=f"{len(df):,} procesos"
            )
        with m2:
            bolsa_tot = df['precio_num'].sum() if 'precio_num' in df.columns else 0
            st.metric(
                label="💰 Bolsa Presupuestada Acumulada",
                value=formato_pesos_cop(bolsa_tot)
            )
        with m3:
            if 'departamento_entidad' in df.columns and not df.empty:
                dpto_lider = df['departamento_entidad'].mode()[0] if not df['departamento_entidad'].mode().empty else "N/I"
                cant_lider = (df['departamento_entidad'] == dpto_lider).sum()
                st.metric(
                    label="📍 Ubicación Líder en Publicaciones",
                    value=f"{dpto_lider}",
                    delta=f"{cant_lider} licitaciones"
                )
            else:
                st.metric(label="📍 Ubicación Líder", value="Por determinar")

        st.divider()

        # ----------------------------------------------------------------------
        # VISUALIZACIÓN EN TARJETAS ESTRELLA (TOP OPORTUNIDADES)
        # ----------------------------------------------------------------------
        if not df.empty:
            st.markdown("#### ⭐ Oportunidades Destacadas (Resumen Visual)")
            df_cards = df.sort_values(by=['precio_num'], ascending=False).head(5)
            
            for idx, row in df_cards.iterrows():
                with st.container():
                    st.markdown(f"""
                    <div class="opportunity-card">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span class="card-title">🏢 {row.get('entidad', 'Entidad Estatal')}</span>
                            <span class="card-badge">💰 {row.get('precio_formateado', '$ 0 COP')}</span>
                        </div>
                        <div style="margin-top:10px; font-size:1.02rem; color:#1E293B;">
                            <b>Objeto:</b> {row.get('nombre_del_procedimiento', 'Sin especificación')}
                        </div>
                        <div style="margin-top:8px; font-size:0.88rem; color:#475569;">
                            📍 <b>Ubicación:</b> {row.get('ciudad_entidad', 'N/I')}, {row.get('departamento_entidad', 'N/I')} | 
                            📜 <b>Modalidad:</b> {row.get('modalidad_de_contratacion', 'N/I')} | 
                            <span class="phase-badge">📌 {row.get('fase', 'N/I')}</span> | 
                            ⏱️ <b>Cierre Ofertas:</b> {row.get('fecha_cierre_clean', 'Por definir')}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    link_p = row.get('urlproceso', '')
                    if link_p:
                        st.markdown(f"🔗 [**Ver Pliegos en SECOP II 🔗**]({link_p})")
                    st.divider()

        # ----------------------------------------------------------------------
        # B. TABLA DE RESULTADOS (st.dataframe)
        # ----------------------------------------------------------------------
        st.markdown(f"#### 📋 Matriz Operativa de Oportunidades ({len(df)} Registros)")
        
        columnas_matriz = {
            'referencia_del_proceso': 'Referencia SECOP II',
            'entidad': 'Entidad Compradora',
            'ciudad_entidad': 'Ciudad / Municipio',
            'codigo_principal_de_categoria': 'Código UNSPSC / Categoría',
            'nombre_del_procedimiento': 'Título convocatoria',
            'descripci_n_del_procedimiento': 'Objeto detallado del contrato',
            'precio_formateado': 'Presupuesto Base ($ COP)',
            'fecha_pub_clean': 'Fecha Publicación',
            'fecha_ult_pub_clean': 'Fecha Última Publicación',
            'fecha_cierre_clean': 'Fecha Cierre Ofertas',
            'urlproceso': 'Link SECOP II'
        }

        cols_presentes = [c for c in columnas_matriz.keys() if c in df.columns]
        df_matriz = df[cols_presentes].rename(columns={c: columnas_matriz[c] for c in cols_presentes})

        st.dataframe(
            df_matriz,
            use_container_width=True,
            column_config={
                "Link SECOP II": st.column_config.LinkColumn(
                    "Link SECOP II",
                    help="Abrir la licitación directamente en la plataforma de Colombia Compra Eficiente",
                    display_text="Ver Pliegos en SECOP II 🔗"
                )
            }
        )

        # Botón de exportación a Excel
        st.markdown("---")
        excel_bytes = exportar_df_a_excel(df)
        st.download_button(
            label="📥 Exportar Matriz Completa a Excel (.xlsx)",
            data=excel_bytes,
            file_name=f"bid_win_vlao_matriz_2026_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    else:
        st.warning("⚠️ No se encontraron oportunidades que coincidan con la combinación de filtros ingresada. Intenta ampliar los criterios o seleccionar 'Todas las Modalidades'.")
