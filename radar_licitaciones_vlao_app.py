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

st.markdown('<div class="main-title">🎯 Radar Quirúrgico SECOP II - Versión 16.0</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title"><b>VLAO INGENIERÍA S.A.S.</b> | Módulo Operativo de Oportunidades (SODA API Conexión Robusta + Multimodalidad + Excel Clean)</div>', unsafe_allow_html=True)

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

SECTORES_VLAO_SODA = [
    '3116', '3010', '2711', '2510', '3912', '3911', '2612', '3121',
    '3015', '4014', '4017', '3018', '7210', '7212', '7214', '7215',
    '8110', '8010'
]

MODALIDADES_SODA = {
    "🌐 Todas las Modalidades (Licitación, Selección Abreviada, Mínima, etc.)": "TODAS",
    "🏛️ Licitación Pública": "LICITACION",
    "📋 Selección Abreviada (Menor Cuantía / Subasta)": "ABREVIADA",
    "⚡ Mínima Cuantía": "MINIMA",
    "🎓 Concurso de Méritos": "CONCURSO",
    "📑 Contratación Directa Corporativa": "DIRECTA",
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
# FUNCIONES AUXILIARES: NORMALIZACIÓN, FORMATOS Y FECHAS (TZ-NAIVE)
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
# CONEXIÓN ROBUSTA Y DESCARGA FILTRADA (SODA API CON FALLBACK AUTOMÁTICO)
# ==============================================================================
@st.cache_data(ttl=300)
def descargar_base_secop_vlao_60dias(sector_codigo="TODOS", modalidad_codigo="TODAS", estado_codigo="TODOS", limite=5000):
    """
    Consulta directa a la API SODA de Colombia Compra Eficiente con recuperación inteligente:
    1. Intenta consulta filtrada en servidor SoQL.
    2. Si la API de Datos Abiertos responde con HTTP 400/500 (por consultas complejas),
       ejecuta un fallback seguro de descarga base y aplica el filtro en memoria con Pandas.
    """
    base_url = "https://www.datos.gov.co/resource/p6dx-8zbt.json"
    
    fecha_hace_60_dias = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%dT00:00:00")
    
    select_cols = (
        "entidad,departamento_entidad,ciudad_entidad,referencia_del_proceso,"
        "codigo_principal_de_categoria,nombre_del_procedimiento,"
        "descripci_n_del_procedimiento,modalidad_de_contratacion,precio_base,"
        "estado_resumen,fecha_de_publicacion,"
        "fecha_de_recepcion_de,urlproceso"
    )
    
    # Construcción limpia de cláusula SoQL ($where)
    condiciones = [f"fecha_de_publicacion >= '{fecha_hace_60_dias}'"]
    
    # 1. Sectores UNSPSC
    if sector_codigo != "TODOS":
        codigos = sector_codigo.split('|')
        sub_c = [f"codigo_principal_de_categoria like '%{c}%'" for c in codigos]
        condiciones.append(f"({' OR '.join(sub_c)})")
    
    # 2. Modalidad de Contratación
    if modalidad_codigo == "LICITACION":
        condiciones.append("lower(modalidad_de_contratacion) like '%licitac%'")
    elif modalidad_codigo == "ABREVIADA":
        condiciones.append("lower(modalidad_de_contratacion) like '%abreviad%'")
    elif modalidad_codigo == "MINIMA":
        condiciones.append("(lower(modalidad_de_contratacion) like '%minima%' or lower(modalidad_de_contratacion) like '%mínima%')")
    elif modalidad_codigo == "CONCURSO":
        condiciones.append("lower(modalidad_de_contratacion) like '%concurso%'")
    elif modalidad_codigo == "DIRECTA":
        condiciones.append("lower(modalidad_de_contratacion) like '%directa%'")
    elif modalidad_codigo == "REGIMEN_ESPECIAL":
        condiciones.append("(lower(modalidad_de_contratacion) like '%regimen%' or lower(modalidad_de_contratacion) like '%régimen%')")

    # 3. Estado / Etapa del proceso
    if estado_codigo == "OFERTAS":
        condiciones.append("(lower(estado_resumen) like '%oferta%' or lower(estado_resumen) like '%convocatoria%')")
    elif estado_codigo == "OBSERVACIONES":
        condiciones.append("lower(estado_resumen) like '%observac%'")
    elif estado_codigo == "INTERES":
        condiciones.append("(lower(estado_resumen) like '%interes%' or lower(estado_resumen) like '%interés%')")
    elif estado_codigo == "BORRADOR":
        condiciones.append("lower(estado_resumen) like '%borrador%'")

    params_primary = {
        "$select": select_cols,
        "$where": " AND ".join(condiciones),
        "$order": "fecha_de_publicacion DESC",
        "$limit": str(limite)
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
    }
    
    # Intento 1: Consulta SoQL Servidor
    try:
        url = f"{base_url}?{urllib.parse.urlencode(params_primary)}"
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        # Intento 2 (Fallback Seguro): Descarga base limpia sin $where complejo
        params_fallback = {
            "$select": select_cols,
            "$where": f"fecha_de_publicacion >= '{fecha_hace_60_dias}'",
            "$order": "fecha_de_publicacion DESC",
            "$limit": str(limite)
        }
        url_fb = f"{base_url}?{urllib.parse.urlencode(params_fallback)}"
        resp = requests.get(url_fb, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

    df = pd.DataFrame(data)
    
    if not df.empty:
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
# BARRA LATERAL (SIDEBAR) CON FILTROS EN ORIGEN Y MEMORIA
# ==============================================================================
st.sidebar.header("⚙️ Filtros Inteligentes SODA API")

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
    "📌 Etapa / Estado del Proceso:",
    options=list(ESTADOS_SODA.keys())
)
codigo_estado = ESTADOS_SODA[estado_sel]

# Cargar Datos iniciales
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
        # Si es TODOS, asegurar que pertenezca a alguno de los sectores de VLAO
        def coincide_vlao(val):
            val_s = str(val)
            return any(c in val_s for c in SECTORES_VLAO_SODA)
        if 'codigo_principal_de_categoria' in df.columns:
            df = df[df['codigo_principal_de_categoria'].apply(coincide_vlao)]

    if codigo_modalidad != "TODAS" and 'modalidad_de_contratacion' in df.columns:
        kw_mod = normalizar_texto(modalidad_sel.split(' ')[1] if ' ' in modalidad_sel else modalidad_sel)
        df = df[df['modalidad_de_contratacion'].apply(normalizar_texto).str.contains(kw_mod[:5])]

    # Despliegue de resúmenes de conteo en la barra lateral
    if 'modalidad_de_contratacion' in df.columns:
        conteo_mod = df['modalidad_de_contratacion'].value_counts()
        st.sidebar.markdown("**📜 Modalidades en Pantalla:**")
        for mod_k, cant in conteo_mod.head(5).items():
            st.sidebar.caption(f"• {mod_k}: **{cant}**")

    if 'estado_resumen' in df.columns:
        conteo_est = df['estado_resumen'].value_counts()
        st.sidebar.markdown("**📌 Estados en Pantalla:**")
        for est_k, cant in conteo_est.head(5).items():
            st.sidebar.caption(f"• {est_k}: **{cant}**")

    # 5. Filtro Anti-OPS (Contratación Directa Inteligente)
    incluir_cd_inteligente = st.sidebar.checkbox(
        "🛡️ Filtro Anti-OPS (Excluir Contratación Directa de Personas Naturales)",
        value=False,
        help="Elimina prestación de servicios profesionales individuales y conserva urgencias y contratos corporativos."
    )
    if incluir_cd_inteligente and 'modalidad_de_contratacion' in df.columns and 'nombre_del_procedimiento' in df.columns:
        palabras_ops = ['prestacion de servicios', 'honorarios', 'apoyo a la gestion', 'persona natural', 'ops']
        
        def es_ops(row):
            mod = str(row.get('modalidad_de_contratacion', '')).lower()
            nom = normalizar_texto(row.get('nombre_del_procedimiento', ''))
            if 'directa' in mod:
                if any(p in nom for p in palabras_ops):
                    return True
            return False

        df = df[~df.apply(es_ops, axis=1)]

    # 6. Búsqueda por Ubicación (Ciudad / Municipio / Departamento)
    ciudad_query = st.sidebar.text_input(
        "📍 Ciudad, Municipio o Departamento:",
        "",
        placeholder="Ej: Bogota, Neiva, Huila, Cundinamarca, Yopal..."
    )
    if ciudad_query.strip():
        q_norm = normalizar_texto(ciudad_query)
        df = df[
            df['ciudad_entidad'].apply(normalizar_texto).str.contains(q_norm) |
            df['departamento_entidad'].apply(normalizar_texto).str.contains(q_norm)
        ]
        st.sidebar.caption(f"🔎 Coincidencias en ubicación: **{len(df)}**")

    # 7. Búsqueda por Palabra Clave Libre
    palabra_clave = st.sidebar.text_input(
        "🔎 Palabra Clave en Objeto:",
        "",
        placeholder="Ej: cubierta, impermeabilizacion, red electrica, pintura..."
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
    st.warning("⚠️ No se encontraron resultados con los filtros seleccionados. Te sugerimos seleccionar 'Todas las Modalidades' o aumentar la muestra en la barra lateral.")
