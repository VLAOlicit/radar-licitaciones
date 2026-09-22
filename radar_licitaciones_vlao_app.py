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
# ==============================================================================
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

DEPARTAMENTO_MUNICIPIOS_MAP = {
    "Bogotá D.C.": ["Bogotá D.C."],
    "Antioquia": ["Medellín", "Bello", "Envigado", "Itagüí", "Rionegro", "Apartadó", "Turbo", "Caucasia", "Sabanalarga", "Caldas", "La Estrella", "Copacabana", "Marinilla"],
    "Atlántico": ["Barranquilla", "Soledad", "Malambo", "Sabanalarga", "Baranoa", "Puerto Colombia"],
    "Bolívar": ["Cartagena", "Magangué", "Turbaco", "Arjona", "Carmen de Bolívar"],
    "Boyacá": ["Tunja", "Sogamoso", "Duitama", "Chiquinquirá", "Puerto Boyacá", "Paipa"],
    "Caldas": ["Manizales", "La Dorada", "Riosucio", "Villamaría", "Chinchiná"],
    "Caquetá": ["Florencia", "San Vicente del Caguán"],
    "Casanare": ["Yopal", "Aguazul", "Villanueva", "Paz de Ariporo"],
    "Cauca": ["Popayán", "Santander de Quilichao", "Puerto Tejada"],
    "Cesar": ["Valledupar", "Aguachica", "Agustín Codazzi", "Bosconia"],
    "Chocó": ["Quibdó", "Istmina"],
    "Córdoba": ["Montería", "Cereté", "Sahagún", "Lorica", "Montelíbano"],
    "Cundinamarca": ["Soacha", "Chía", "Zipaquirá", "Facatativá", "Fusagasugá", "Girardot", "Mosquera", "Madrid", "Funza", "Cajicá", "Sopó", "Tocancipá"],
    "Huila": ["Neiva", "Pitalito", "Garzón", "La Plata", "Campoalegre", "Gigante", "Palermo"],
    "La Guajira": ["Riohacha", "Maicao", "Uribia", "Manaure"],
    "Magdalena": ["Santa Marta", "Ciénaga", "Fundación", "Plato"],
    "Meta": ["Villavicencio", "Acacías", "Granada", "Puerto López"],
    "Nariño": ["Pasto", "Tumaco", "Ipiales"],
    "Norte de Santander": ["Cúcuta", "Ocaña", "Pamplona", "Villa del Rosario", "Los Patios"],
    "Quindío": ["Armenia", "Calarcá", "Montenegro", "Quimbaya"],
    "Risaralda": ["Pereira", "Dosquebradas", "Santa Rosa de Cabal"],
    "Santander": ["Bucaramanga", "Floridablanca", "Girón", "Piedecuesta", "Barrancabermeja", "San Gil"],
    "Sucre": ["Sincelejo", "Corozal", "San Marcos"],
    "Tolima": ["Ibagué", "Espinal", "Melgar", "Honda", "Mariquita"],
    "Valle del Cauca": ["Cali", "Palmira", "Buenaventura", "Tuluá", "Cartago", "Buga", "Jamundí", "Yumbo"]
}

MUNICIPIOS_TODOS = sorted(list(set([m for lista in DEPARTAMENTO_MUNICIPIOS_MAP.values() for m in lista])))

MODALIDADES_OPCIONES = [
    "Mínima Cuantía",
    "Selección Abreviada",
    "Licitación Pública",
    "Concurso de Méritos",
    "Contratación Directa",
    "Régimen Especial"
]

TIPOS_CONTRATO_OPCIONES = [
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

def match_modalidad_multi(val_mod, sel_modalidades_list):
    if not sel_modalidades_list:
        return True
    val_n = normalizar_texto(val_mod)
    for sel in sel_modalidades_list:
        sel_n = normalizar_texto(sel)
        if "minima" in sel_n and ("minima" in val_n or "mínima" in val_n):
            return True
        if "abreviada" in sel_n and "abreviad" in val_n:
            return True
        if "licitacion" in sel_n and "licitac" in val_n:
            return True
        if "concurso" in sel_n and "concurso" in val_n:
            return True
        if "directa" in sel_n and "directa" in val_n:
            return True
        if "regimen" in sel_n and ("regimen" in val_n or "régimen" in val_n):
            return True
    return False

def match_tipo_contrato_multi(val_tipo, sel_tipos_list):
    if not sel_tipos_list:
        return True
    val_n = normalizar_texto(val_tipo)
    for sel in sel_tipos_list:
        sel_n = normalizar_texto(sel)
        if "obra" in sel_n and "obra" in val_n:
            return True
        if "suministro" in sel_n and "suministr" in val_n:
            return True
        if ("interventoria" in sel_n or "consultoria" in sel_n) and ("interventor" in val_n or "consultor" in val_n or "estudio" in val_n):
            return True
        if "compraventa" in sel_n and ("compra" in val_n or "venta" in val_n):
            return True
        if ("prestacion" in sel_n or "servicios" in sel_n) and ("servicio" in val_n or "prestac" in val_n):
            return True
    return False

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

def get_index_safe(options_list, target_val):
    try:
        return options_list.index(target_val)
    except Exception:
        return 0

# ==============================================================================
# CONEXIÓN Y DESCARGA A SODA API (DATOS.GOV.CO - STRICT 2026 - FULL SERVER FILTER)
# ==============================================================================
@st.cache_data(ttl=300)
def descargar_secop_2026(
    dptos_sel=None,
    ciudades_sel=None,
    modalidad_sel_list=None,
    tipo_contrato_sel_list=None,
    sector_codigo="TODOS",
    dias_ventana=365,
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

    # 1. Filtro Departamento & Ciudad a nivel de Servidor (SODA $where)
    loc_conds = []
    if dptos_sel:
        c_dptos = get_soda_location_conditions('departamento_entidad', dptos_sel)
        loc_conds.extend(c_dptos)
    if ciudades_sel:
        c_ciuds = get_soda_location_conditions('ciudad_entidad', ciudades_sel)
        loc_conds.extend(c_ciuds)
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

    # 3. Modalidad Filter (Multiple)
    if modalidad_sel_list:
        sub_mod = []
        for m_item in modalidad_sel_list:
            if "Mínima" in m_item:
                sub_mod.append("(lower(modalidad_de_contratacion) like '%minima%' or lower(modalidad_de_contratacion) like '%mínima%')")
            elif "Abreviada" in m_item:
                sub_mod.append("lower(modalidad_de_contratacion) like '%abreviad%'")
            elif "Licitación" in m_item:
                sub_mod.append("lower(modalidad_de_contratacion) like '%licitac%'")
            elif "Concurso" in m_item:
                sub_mod.append("lower(modalidad_de_contratacion) like '%concurso%'")
            elif "Directa" in m_item:
                sub_mod.append("lower(modalidad_de_contratacion) like '%directa%'")
            elif "Régimen" in m_item or "Regimen" in m_item:
                sub_mod.append("(lower(modalidad_de_contratacion) like '%regimen%' or lower(modalidad_de_contratacion) like '%régimen%')")
        if sub_mod:
            condiciones.append(f"({' OR '.join(sub_mod)})")

    # 4. Tipo Contrato Filter (Multiple)
    if tipo_contrato_sel_list:
        sub_tipo = []
        for t_item in tipo_contrato_sel_list:
            q_t = normalizar_texto(t_item.split(' ')[0])
            if q_t:
                sub_tipo.append(f"lower(tipo_de_contrato) like '%{q_t[:4]}%'")
        if sub_tipo:
            condiciones.append(f"({' OR '.join(sub_tipo)})")

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
        # Fallback de seguridad abierto
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
# ⚙️ PANTALLA DE INICIO: CONSOLA DE FILTROS DE ENTRADA
# ==============================================================================
st.markdown("### ⚙️ Selecciona y aplica los filtros para encontrar la oportunidad a tu medida")
st.caption("Configura los parámetros clave de ubicación, modalidad, presupuesto y sector para realizar la consulta en SECOP II.")

cfg_saved = st.session_state.get("filtros_guardados", {})

# 1. Ubicación Geográfica Interactivas fuera de form para filtro dinámico de municipio
c1, c2 = st.columns(2)

with c1:
    dptos_sel = st.multiselect(
        "📍 Ubicación Geográfica (Departamento):",
        options=DEPARTAMENTOS_COLOMBIA,
        default=cfg_saved.get("dptos_sel", []),
        key="dptos_sel_widget",
        help="Selecciona uno o varios departamentos para filtrar los municipios disponibles."
    )

# Mapeo dinámico de municipios con procesos según departamento seleccionado
if dptos_sel:
    muni_filtrados = set()
    for d_item in dptos_sel:
        if d_item in DEPARTAMENTO_MUNICIPIOS_MAP:
            muni_filtrados.update(DEPARTAMENTO_MUNICIPIOS_MAP[d_item])
    if muni_filtrados:
        municipios_opciones_actuales = sorted(list(muni_filtrados))
    else:
        municipios_opciones_actuales = MUNICIPIOS_TODOS
else:
    municipios_opciones_actuales = MUNICIPIOS_TODOS

with c2:
    default_ciuds = [c for c in cfg_saved.get("ciudades_sel", []) if c in municipios_opciones_actuales]
    ciudades_sel = st.multiselect(
        "🏙️ Ciudad / Municipio (Sólo Municipios Activos del Departamento):",
        options=municipios_opciones_actuales,
        default=default_ciuds,
        key="ciudades_sel_widget",
        help="Muestra únicamente municipios correspondientes a él o los departamentos seleccionados."
    )

with st.form(key="form_filtros_entrada"):
    # Fila 2: Definición Jurídica y Contractual (MODALIDAD Y TIPO MULTIPLE)
    c3, c4, c5 = st.columns(3)
    with c3:
        modalidad_sel_list = st.multiselect(
            "📜 Modalidad de Contratación (Selección Múltiple):",
            options=MODALIDADES_OPCIONES,
            default=cfg_saved.get("modalidad_sel_list", []),
            help="Puedes elegir una o varias modalidades al mismo tiempo (ej. Licitación Pública + Selección Abreviada)."
        )
    with c4:
        tipo_contrato_sel_list = st.multiselect(
            "📑 Tipo de Contrato (Selección Múltiple):",
            options=TIPOS_CONTRATO_OPCIONES,
            default=cfg_saved.get("tipo_contrato_sel_list", []),
            help="Puedes elegir uno o varios tipos de contrato (ej. Obra Pública + Interventoría)."
        )
    with c5:
        sectores_keys = list(SECTORES_UNSPSC.keys())
        idx_sec = get_index_safe(sectores_keys, cfg_saved.get("sector_sel", sectores_keys[0]))
        sector_sel = st.selectbox(
            "🏢 Sector / Categoría UNSPSC:",
            options=sectores_keys,
            index=idx_sec
        )

    # Fila 3: Presupuesto Mínimo y Máximo por Separado (Cajas de Texto / Numéricas)
    st.markdown("##### 💰 Rangos de Presupuesto ($ COP)")
    cm1, cm2 = st.columns(2)
    with cm1:
        monto_min_m = st.number_input(
            "💵 Valor Mínimo Presupuesto (Millones COP):",
            min_value=0.0,
            value=float(cfg_saved.get("monto_min_m", 0.0)),
            step=10.0,
            help="Escribe el presupuesto mínimo en millones de pesos (ej. 50 para $50.000.000 COP)."
        )
    with cm2:
        monto_max_m = st.number_input(
            "💵 Valor Máximo Presupuesto (Millones COP - 0 para sin límite):",
            min_value=0.0,
            value=float(cfg_saved.get("monto_max_m", 0.0)),
            step=50.0,
            help="Escribe el presupuesto máximo en millones de pesos. Dejar en 0 para no aplicar tope superior."
        )

    # Fila 4: Estado, Fase & Ventana de Tiempos
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

    # Fila 5: Criterios Adicionales & Anti-OPS
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
        "modalidad_sel_list": modalidad_sel_list,
        "tipo_contrato_sel_list": tipo_contrato_sel_list,
        "monto_min_m": monto_min_m,
        "monto_max_m": monto_max_m,
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
    sel_dptos = cfg.get("dptos_sel", [])
    sel_ciudades = cfg.get("ciudades_sel", [])
    sel_mod_list = cfg.get("modalidad_sel_list", [])
    sel_tipo_list = cfg.get("tipo_contrato_sel_list", [])

    with st.spinner("🚀 Cargando oportunidades de SECOP II (2026)..."):
        try:
            df_raw = descargar_secop_2026(
                dptos_sel=sel_dptos,
                ciudades_sel=sel_ciudades,
                modalidad_sel_list=sel_mod_list,
                tipo_contrato_sel_list=sel_tipo_list,
                sector_codigo=cod_sector,
                dias_ventana=m_dias,
                limite=5000
            )
        except Exception as e:
            st.error(f"Error de conexión con Datos Abiertos: {e}")
            df_raw = pd.DataFrame()

    if not df_raw.empty:
        df = df_raw.copy()

        # ----------------------------------------------------------------------
        # APLICACIÓN DE FILTROS RIGUROSOS Y ROBUSTOS
        # ----------------------------------------------------------------------
        
        # 1. Departamento
        if sel_dptos and 'departamento_entidad' in df.columns:
            df = df[df['departamento_entidad'].apply(lambda val: match_location(val, sel_dptos))]

        # 2. Ciudad / Municipio
        if sel_ciudades and 'ciudad_entidad' in df.columns:
            df = df[df['ciudad_entidad'].apply(lambda val: match_location(val, sel_ciudades))]

        # 3. Tipo de Contrato (Múltiple)
        if sel_tipo_list and 'tipo_de_contrato' in df.columns:
            df = df[df['tipo_de_contrato'].apply(lambda val: match_tipo_contrato_multi(val, sel_tipo_list))]

        # 4. Modalidad (Múltiple)
        if sel_mod_list and 'modalidad_de_contratacion' in df.columns:
            df = df[df['modalidad_de_contratacion'].apply(lambda val: match_modalidad_multi(val, sel_mod_list))]

        # 5. Rango Presupuesto (Valor Mínimo y Máximo)
        val_min_p = cfg.get("monto_min_m", 0.0) * 1000000
        val_max_p = cfg.get("monto_max_m", 0.0) * 1000000
        if val_min_p > 0 and 'precio_num' in df.columns:
            df = df[df['precio_num'] >= val_min_p]
        if val_max_p > 0 and 'precio_num' in df.columns:
            df = df[df['precio_num'] <= val_max_p]

        # 6. Estado Resumen
        sel_est = cfg.get("estado_sel", "Todos los Estados")
        if sel_est != "Todos los Estados" and 'estado_resumen' in df.columns:
            df = df[df['estado_resumen'].apply(lambda val: match_estado(val, sel_est))]

        # 7. Fase
        sel_fase = cfg.get("fase_sel", "Todas las Fases")
        if sel_fase != "Todas las Fases" and 'fase' in df.columns:
            df = df[df['fase'].apply(lambda val: match_fase(val, sel_fase))]

        # 8. Filtro Anti-OPS
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

        # 9. Palabra Clave Libre
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
            st.write("")
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
            c_head1, c_head2 = st.columns([2.5, 1.5])
            with c_head1:
                st.markdown("#### ⭐ Oportunidades Destacadas (Resumen Visual)")
            with c_head2:
                criterio_orden_cards = st.selectbox(
                    "Ordenar tarjetas por:",
                    options=[
                        "⏱️ Cierre: Más lejana ➔ Más cercana",
                        "⏱️ Cierre: Más cercana ➔ Más lejana",
                        "💰 Mayor Presupuesto ($ COP)"
                    ],
                    index=0,
                    key="select_orden_cards_v8"
                )

            if "Más lejana" in criterio_orden_cards:
                df_cards = df.sort_values(by=['fecha_cierre_dt', 'precio_num'], ascending=[False, False], na_position='last').head(5)
            elif "Más cercana" in criterio_orden_cards:
                df_cards = df.sort_values(by=['fecha_cierre_dt', 'precio_num'], ascending=[True, False], na_position='last').head(5)
            else:
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
