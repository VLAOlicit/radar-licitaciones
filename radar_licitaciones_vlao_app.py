import io
import urllib.parse
import unicodedata
from datetime import datetime, timedelta
import pandas as pd
import requests
import streamlit as st

# ==============================================================================
# CONFIGURACIÓN DE PÁGINA Y ESTILOS DE STREAMLIT
# ==============================================================================
st.set_page_config(
    page_title="Radar SECOP II v16.0 - VLAO INGENIERÍA S.A.S.",
    layout="wide",
    page_icon="🎯"
)

st.markdown("""
    <style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1E3A8A;
        margin-bottom: 0px;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 20px;
    }
    .stMetric {
        background-color: #F3F4F6;
        padding: 12px;
        border-radius: 8px;
        border-left: 4px solid #1E3A8A;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🎯 Radar Quirúrgico SECOP II - Versión 16.7</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title"><b>VLAO INGENIERÍA S.A.S.</b> | Módulo Operativo de Oportunidades (URLs directas SECOP II + Filtros Múltiples de Ubicación y Etapa)</div>', unsafe_allow_html=True)

# ==============================================================================
# DICCIONARIOS DE SECTORES, MODALIDADES Y ESTADOS
# ==============================================================================
CATEGORIAS_UNSPSC = {
    "🌐 Todos los Sectores VLAO (Portafolio Completo)": "TODOS",
    "🏗️ Obras Civiles, Edificaciones y Mantenimiento (7210 / 7212 / 7214 / 7215)": "7210|7212|7214|7215",
    "⚡ Equipos, Materiales Eléctricos e Iluminación (3912 / 3911 / 2612)": "3912|3911|2612",
    "🛠️ Ferretería, Herrajes y Construcción (3116 / 3010)": "3116|3010",
    "🔧 Herramientas de Mano y Maquinaria (2711 / 2510)": "2711|2510",
    "🎨 Pinturas, Acabados e Impermeabilización (3121 / 3015)": "3121|3015",
    "🚰 Tuberías, Plomería y Sanitarios (4014 / 4017 / 3018)": "4014|4017|3018",
    "📐 Consultoría, Diseños e Interventoría (8110 / 8010)": "8110|8010"
}

SECTORES_VLAO_SEGMENTOS = ['72', '39', '31', '30', '40', '81', '80', '27', '25']
SECTORES_VLAO_EXACTOS = ['3116', '3010', '2711', '2510', '3912', '3911', '2612', '3121', '3015', '4014', '4017', '3018', '7210', '7212', '7214', '7215', '8110', '8010']

MODALIDADES_SODA = {
    "🌐 Todas las Modalidades": "TODAS",
    "🏛️ Licitación Pública": "LICITACION",
    "📋 Selección Abreviada (Menor Cuantía / Subasta)": "ABREVIADA",
    "⚡ Mínima Cuantía": "MINIMA",
    "🎓 Concurso de Méritos": "CONCURSO",
    "📑 Contratación Directa": "DIRECTA",
    "🏢 Régimen Especial": "REGIMEN_ESPECIAL"
}

ESTADOS_SODA = {
    "📌 Todos los Estados / Etapas": "TODOS",
    "📝 Presentación de Ofertas / Convocatoria": "OFERTAS",
    "💬 Presentación de Observaciones / Pliegos": "OBSERVACIONES",
    "🙋 Manifestación de Interés": "INTERES",
    "📄 Borrador / Proyecto de Pliegos": "BORRADOR"
}

# ==============================================================================
# FUNCIONES AUXILIARES: NORMALIZACIÓN, FORMATOS, URLS Y FECHAS
# ==============================================================================
def normalizar_texto(texto):
    """Elimina acentos, tildes y caracteres especiales para búsquedas exactas."""
    if not texto or pd.isna(texto):
        return ""
    texto_str = str(texto)
    nfkd = unicodedata.normalize('NFD', texto_str)
    sin_tildes = "".join([c for c in nfkd if unicodedata.category(c) != 'Mn'])
    return sin_tildes.lower().strip()

def formato_pesos_cop(valor):
    """Formatea valores numéricos a Pesos Colombianos ($ COP) con separadores de miles."""
    try:
        val = float(valor)
        if pd.isna(val) or val == 0:
            return "$ 0 COP"
        return f"$ {val:,.0f} COP".replace(",", ".")
    except Exception:
        return "$ 0 COP"

def limpiar_url_secop(val):
    """
    Extrae la URL limpia en formato texto string (http/https).
    Socrata SODA API devuelve urlproceso como dict {'url': 'https://...'}
    Esta función desempaqueta el diccionario para entregar una URL directamente navegable.
    """
    if pd.isna(val) or not val:
        return ""
    if isinstance(val, dict):
        return str(val.get('url', '')).strip()
    val_str = str(val).strip()
    if val_str.startswith("{") and ("'url':" in val_str or '"url":' in val_str):
        import ast
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
    """
    Extrae la fecha en objeto Datetime sin zona horaria (Naive) y texto AAAA-MM-DD.
    Evita errores de comparación (TypeError) y de exportación a Excel (ValueError).
    """
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

# ==============================================================================
# DESCARGA DE DATOS DESDE SODA API CON PARSEO DE URLS
# ==============================================================================
@st.cache_data(ttl=300)
def descargar_base_secop_vlao_60dias(sector_codigo="TODOS", modalidad_codigo="TODAS", estado_codigo="TODOS", limite=5000):
    base_url = "https://www.datos.gov.co/resource/p6dx-8zbt.json"
    fecha_hace_60_dias = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%dT00:00:00")
    
    select_cols = (
        "entidad,departamento_entidad,ciudad_entidad,referencia_del_proceso,"
        "codigo_principal_de_categoria,nombre_del_procedimiento,"
        "descripci_n_del_procedimiento,modalidad_de_contratacion,precio_base,"
        "estado_resumen,fecha_de_publicacion,"
        "fecha_de_recepcion_de,urlproceso"
    )
    
    condiciones = [f"fecha_de_publicacion >= '{fecha_hace_60_dias}'"]
    
    # 1. Filtro UNSPSC SODA
    if sector_codigo != "TODOS":
        codigos = sector_codigo.split('|')
        sub_c = [f"codigo_principal_de_categoria like '%{c}%'" for c in codigos]
        condiciones.append(f"({' OR '.join(sub_c)})")
    else:
        sub_c = [f"codigo_principal_de_categoria like '%{s}%'" for s in SECTORES_VLAO_SEGMENTOS]
        condiciones.append(f"({' OR '.join(sub_c)})")

    # 2. Filtro de Modalidad SODA
    if modalidad_codigo == "LICITACION":
        condiciones.append("(modalidad_de_contratacion like '%Licitaci%' or modalidad_de_contratacion like '%licitaci%' or modalidad_de_contratacion like '%LICITACI%')")
    elif modalidad_codigo == "ABREVIADA":
        condiciones.append("(modalidad_de_contratacion like '%Abreviada%' or modalidad_de_contratacion like '%abreviada%')")
    elif modalidad_codigo == "MINIMA":
        condiciones.append("(modalidad_de_contratacion like '%mínima%' or modalidad_de_contratacion like '%minima%' or modalidad_de_contratacion like '%Mínima%')")
    elif modalidad_codigo == "CONCURSO":
        condiciones.append("(modalidad_de_contratacion like '%Concurso%' or modalidad_de_contratacion like '%concurso%')")
    elif modalidad_codigo == "DIRECTA":
        condiciones.append("(modalidad_de_contratacion like '%Directa%' or modalidad_de_contratacion like '%directa%')")
    elif modalidad_codigo == "REGIMEN_ESPECIAL":
        condiciones.append("(modalidad_de_contratacion like '%Régimen%' or modalidad_de_contratacion like '%regimen%')")

    # 3. Filtro de Estado SODA
    if estado_codigo == "OFERTAS":
        condiciones.append("(estado_resumen like '%oferta%' or estado_resumen like '%Oferta%' or estado_resumen like '%convocatoria%' or estado_resumen like '%Convocatoria%')")
    elif estado_codigo == "OBSERVACIONES":
        condiciones.append("(estado_resumen like '%observac%' or estado_resumen like '%Observac%')")
    elif estado_codigo == "INTERES":
        condiciones.append("(estado_resumen like '%interés%' or estado_resumen like '%interes%' or estado_resumen like '%Interés%')")
    elif estado_codigo == "BORRADOR":
        condiciones.append("(estado_resumen like '%borrador%' or estado_resumen like '%Borrador%')")

    params = {
        "$select": select_cols,
        "$where": " AND ".join(condiciones),
        "$order": "fecha_de_publicacion DESC",
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
        conds_fb = [f"fecha_de_publicacion >= '{fecha_hace_60_dias}'"]
        if modalidad_codigo != "TODAS":
            if modalidad_codigo == "LICITACION":
                conds_fb.append("(modalidad_de_contratacion like '%Licitaci%' or modalidad_de_contratacion like '%licitaci%')")
            elif modalidad_codigo == "ABREVIADA":
                conds_fb.append("(modalidad_de_contratacion like '%Abreviada%' or modalidad_de_contratacion like '%abreviada%')")
            elif modalidad_codigo == "MINIMA":
                conds_fb.append("(modalidad_de_contratacion like '%minima%' or modalidad_de_contratacion like '%mínima%')")
        
        params_fb = {
            "$select": select_cols,
            "$where": " AND ".join(conds_fb),
            "$order": "fecha_de_publicacion DESC",
            "$limit": str(limite)
        }
        url_fb = f"{base_url}?{urllib.parse.urlencode(params_fb)}"
        resp = requests.get(url_fb, headers=headers, timeout=35)
        resp.raise_for_status()
        data = resp.json()

    df = pd.DataFrame(data)
    
    if not df.empty:
        # Limpieza crucial de URL SECOP II
        if 'urlproceso' in df.columns:
            df['urlproceso'] = df['urlproceso'].apply(limpiar_url_secop)
        else:
            df['urlproceso'] = ""

        # Precios
        if 'precio_base' in df.columns:
            df['precio_num'] = pd.to_numeric(df['precio_base'], errors='coerce').fillna(0)
            df['precio_formateado'] = df['precio_num'].apply(formato_pesos_cop)
        else:
            df['precio_num'] = 0
            df['precio_formateado'] = "$ 0 COP"
            
        # Fecha de Publicación
        if 'fecha_de_publicacion' in df.columns:
            res_pub = [parsear_fecha_secop(v) for v in df['fecha_de_publicacion']]
            df['fecha_pub_dt'] = [r[0] for r in res_pub]
            df['fecha_pub_clean'] = [r[1] for r in res_pub]
        else:
            df['fecha_pub_dt'] = pd.NaT
            df['fecha_pub_clean'] = "Por definir"
            
        # Fecha Cierre de Ofertas
        if 'fecha_de_recepcion_de' in df.columns:
            res_cie = [parsear_fecha_secop(v) for v in df['fecha_de_recepcion_de']]
            df['fecha_cierre_clean'] = [r[1] if r[1] != "Por definir" else "Por definir en pliegos" for r in res_cie]
        else:
            df['fecha_cierre_clean'] = "Por definir en pliegos"
            
    return df

# ==============================================================================
# EXPORTACIÓN SEGURA A EXCEL (OPENPYXL)
# ==============================================================================
def exportar_df_a_excel(df_filtrado):
    df_export = df_filtrado.copy()
    
    columnas_visibles = {
        'entidad': 'Entidad Compradora',
        'departamento_entidad': 'Departamento',
        'ciudad_entidad': 'Ciudad / Municipio',
        'referencia_del_proceso': 'Referencia Proceso',
        'nombre_del_procedimiento': 'Objeto del Contrato',
        'modalidad_de_contratacion': 'Modalidad',
        'estado_resumen': 'Estado / Etapa',
        'precio_formateado': 'Presupuesto Estimado ($ COP)',
        'fecha_pub_clean': 'Fecha Publicación',
        'fecha_cierre_clean': 'Fecha Cierre Ofertas',
        'urlproceso': 'Link SECOP II'
    }
    
    cols = [c for c in columnas_visibles.keys() if c in df_export.columns]
    df_export = df_export[cols].rename(columns={c: columnas_visibles[c] for c in cols})
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Oportunidades_SECOP_VLAO')
    return buffer.getvalue()

# ==============================================================================
# BARRA LATERAL (SIDEBAR) CON FILTROS MÚLTIPLES
# ==============================================================================
st.sidebar.header("⚙️ Filtros Inteligentes SECOP II")

# 1. Slider de Lote de Descarga
limite_descarga = st.sidebar.slider("📊 Lote máximo a recuperar de la API:", 1000, 20000, 5000, 1000)

# 2. Sector UNSPSC VLAO
sector_sel = st.sidebar.selectbox(
    "🏢 Sector / Categoría UNSPSC (VLAO):",
    options=list(CATEGORIAS_UNSPSC.keys())
)
codigo_sector = CATEGORIAS_UNSPSC[sector_sel]

# 3. Modalidad de Contratación
modalidad_sel = st.sidebar.selectbox(
    "📜 Modalidad de Contratación:",
    options=list(MODALIDADES_SODA.keys())
)
codigo_modalidad = MODALIDADES_SODA[modalidad_sel]

# 4. Estado / Etapa del Proceso
estado_sel = st.sidebar.selectbox(
    "📌 Etapa / Estado del Proceso (Filtro API):",
    options=list(ESTADOS_SODA.keys())
)
codigo_estado = ESTADOS_SODA[estado_sel]

# 5. Presupuesto Mínimo
monto_minimo_m = st.sidebar.number_input(
    "💵 Presupuesto Mínimo Estimado (Millones COP):",
    min_value=0,
    max_value=10000,
    value=0,
    step=10,
    help="Ejemplo: Si ingresas 50, se ocultarán procesos menores a $ 50.000.000 COP."
)

# Cargar Datos iniciales desde SODA API
with st.spinner("🚀 Consultando base nacional de SECOP II (Datos Abiertos Colombia)..."):
    try:
        df_raw = descargar_base_secop_vlao_60dias(
            sector_codigo=codigo_sector,
            modalidad_codigo=codigo_modalidad,
            estado_codigo=codigo_estado,
            limite=limite_descarga
        )
    except Exception as e:
        st.error(f"Error de conexión con Datos Abiertos: {e}")
        df_raw = pd.DataFrame()

if not df_raw.empty:
    df = df_raw.copy()

    # Filtrado complementario de seguridad en Pandas
    if codigo_sector != "TODOS":
        cods = codigo_sector.split('|')
        def coincide_unspsc(val):
            val_s = str(val)
            return any(c in val_s for c in cods)
        if 'codigo_principal_de_categoria' in df.columns:
            df = df[df['codigo_principal_de_categoria'].apply(coincide_unspsc)]
    else:
        def coincide_vlao(val):
            val_s = str(val)
            return any(c in val_s for c in SECTORES_VLAO_EXACTOS)
        if 'codigo_principal_de_categoria' in df.columns:
            df = df[df['codigo_principal_de_categoria'].apply(coincide_vlao)]

    # Filtro por Modalidad en Pandas
    if codigo_modalidad == "LICITACION" and 'modalidad_de_contratacion' in df.columns:
        df = df[df['modalidad_de_contratacion'].apply(normalizar_texto).str.contains('licitac')]
    elif codigo_modalidad == "ABREVIADA" and 'modalidad_de_contratacion' in df.columns:
        df = df[df['modalidad_de_contratacion'].apply(normalizar_texto).str.contains('abreviad')]
    elif codigo_modalidad == "MINIMA" and 'modalidad_de_contratacion' in df.columns:
        df = df[df['modalidad_de_contratacion'].apply(normalizar_texto).str.contains('minim')]

    # Filtro por Presupuesto Mínimo
    if monto_minimo_m > 0 and 'precio_num' in df.columns:
        limite_pesos = monto_minimo_m * 1000000
        df = df[df['precio_num'] >= limite_pesos]

    # ---------------------------------------------------------
    # FILTROS MÚLTIPLES AVANZADOS (CIUDAD, DEPARTAMENTO Y ETAPAS)
    # ---------------------------------------------------------
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎯 Filtros Múltiples Locales")

    # A. Filtro Múltiple por Etapa / Estado del Proceso
    if 'estado_resumen' in df.columns:
        estados_unicos = sorted([e for e in df['estado_resumen'].dropna().unique() if e])
        estados_sel_multi = st.sidebar.multiselect(
            "📌 Filtrar por una o varias Etapas / Estados:",
            options=estados_unicos,
            default=[],
            help="Selecciona una o varias etapas para acotar la lista."
        )
        if estados_sel_multi:
            df = df[df['estado_resumen'].isin(estados_sel_multi)]

    # B. Filtro Múltiple por Departamento
    if 'departamento_entidad' in df.columns:
        dptos_unicos = sorted([d for d in df['departamento_entidad'].dropna().unique() if d])
        dptos_sel_multi = st.sidebar.multiselect(
            "🗺️ Departamento(s):",
            options=dptos_unicos,
            default=[],
            help="Puedes seleccionar varios departamentos al mismo tiempo."
        )
        if dptos_sel_multi:
            df = df[df['departamento_entidad'].isin(dptos_sel_multi)]

    # C. Filtro Múltiple por Ciudad / Municipio
    if 'ciudad_entidad' in df.columns:
        ciudades_unicas = sorted([c for c in df['ciudad_entidad'].dropna().unique() if c])
        ciudades_sel_multi = st.sidebar.multiselect(
            "📍 Ciudad(es) / Municipio(s):",
            options=ciudades_unicas,
            default=[],
            help="Permite elegir uno o múltiples municipios."
        )
        if ciudades_sel_multi:
            df = df[df['ciudad_entidad'].isin(ciudades_sel_multi)]

    # D. Búsqueda Libre por Palabra Clave
    palabra_clave = st.sidebar.text_input(
        "🔎 Palabra Clave en Objeto:",
        "",
        placeholder="Ej: cubierta, impermeabilizacion, red electrica..."
    )
    if palabra_clave.strip():
        kw_norm = normalizar_texto(palabra_clave)
        df = df[
            df['nombre_del_procedimiento'].apply(normalizar_texto).str.contains(kw_norm) |
            df['descripci_n_del_procedimiento'].apply(normalizar_texto).str.contains(kw_norm)
        ]

    # ==============================================================================
    # TABLERO PRINCIPAL: KPIS Y RESULTADOS
    # ==============================================================================
    st.markdown("### 📊 Indicadores Clave de Oportunidades (KPIs)")
    
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric("🎯 Procesos Filtrados", f"{len(df):,} licitaciones")
    with kpi2:
        monto_tot = df['precio_num'].sum() if 'precio_num' in df.columns else 0
        st.metric("💰 Presupuesto Acumulado", formato_pesos_cop(monto_tot))
    with kpi3:
        monto_prom = df['precio_num'].mean() if 'precio_num' in df.columns and len(df) > 0 else 0
        st.metric("📈 Promedio por Licitación", formato_pesos_cop(monto_prom))
    with kpi4:
        muncs = df['ciudad_entidad'].nunique() if 'ciudad_entidad' in df.columns else 0
        st.metric("📍 Municipios / Ciudades", f"{muncs} activos")

    st.divider()

    # Tabla interactiva
    st.markdown(f"### 📋 Listado Operativo de Licitaciones ({len(df)} Oportunidades)")
    
    cols_mostrar = {
        'entidad': 'Entidad',
        'ciudad_entidad': 'Ciudad / Dpto',
        'nombre_del_procedimiento': 'Objeto del Contrato',
        'modalidad_de_contratacion': 'Modalidad',
        'estado_resumen': 'Estado / Etapa',
        'precio_formateado': 'Presupuesto Estimado',
        'fecha_pub_clean': 'Fecha Publicación',
        'fecha_cierre_clean': 'Cierre Ofertas',
        'urlproceso': 'Link SECOP II'
    }
    
    cols_existentes = [c for c in cols_mostrar.keys() if c in df.columns]
    df_vista = df[cols_existentes].rename(columns={c: cols_mostrar[c] for c in cols_existentes})
    
    st.dataframe(
        df_vista,
        use_container_width=True,
        column_config={
            "Link SECOP II": st.column_config.LinkColumn(
                "Link SECOP II",
                help="Abrir la licitación directamente en la plataforma de Colombia Compra Eficiente",
                display_text="Ver Proceso en SECOP II"
            )
        }
    )

    # Botón de exportación a Excel
    st.markdown("---")
    excel_data = exportar_df_a_excel(df)
    st.download_button(
        label="📥 Exportar Reporte Seleccionado a Excel (.xlsx)",
        data=excel_data,
        file_name=f"radar_secop_vlao_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.warning("⚠️ No se encontraron resultados con los filtros actuales. Te sugerimos ampliar los sectores o eliminar palabras clave.")
