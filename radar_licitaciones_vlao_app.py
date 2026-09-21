import io
import urllib.parse
import unicodedata
from datetime import datetime, timedelta
import pandas as pd
import requests
import streamlit as st

# ==============================================================================
# CONFIGURACIÓN DE PÁGINA Y ESTILOS
# ==============================================================================
st.set_page_config(
    page_title="Radar SECOP II v18.0 - VLAO INGENIERÍA S.A.S.",
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
        margin-bottom: 15px;
    }
    .stMetric {
        background-color: #F8FAFC;
        padding: 12px;
        border-radius: 8px;
        border-left: 4px solid #1E3A8A;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .opportunity-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-left: 5px solid #2563EB;
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }
    .card-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1E293B;
    }
    .card-badge {
        background-color: #EFF6FF;
        color: #1D4ED8;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🎯 Radar de Alta Especificidad SECOP II - Versión 18.0</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title"><b>VLAO INGENIERÍA S.A.S.</b> | Módulo de Oportunidades Concretas y Filtrado Quirúrgico</div>', unsafe_allow_html=True)

# ==============================================================================
# DICCIONARIOS Y ESPECIALIDADES ESTRATÉGICAS VLAO INGENIERÍA S.A.S.
# ==============================================================================
ESPECIALIDADES_VLAO = {
    "🌐 Portafolio Estratégico Completo VLAO": "TODOS",
    "🏗️ Obras Civiles y Edificaciones (Mantenimiento, Remodelación, Estructuras)": "7212|7214|7210|7215",
    "⚡ Redes Eléctricas e Iluminación (Subestaciones, Iluminación LED, Cableado)": "3912|3911|2612",
    "🎨 Impermeabilización, Pinturas, Aislamientos y Cubiertas": "3121|3015",
    "🚰 Redes Hidrosanitarias, Tuberías y Plomería": "4014|4017|3018",
    "📐 Consultoría, Diseños, Estudios e Interventoría de Ingeniería": "8110|8010",
    "🛠️ Ferretería, Equipos y Suministros Técnicos": "3116|3010|2711|2510"
}

SECTORES_VLAO_SEGMENTOS = ['72', '39', '31', '30', '40', '81', '80', '27', '25']

MODALIDADES_SODA = {
    "🌐 Todas las Modalidades Competitivas": "COMPETITIVAS",
    "🏛️ Licitación Pública": "LICITACION",
    "📋 Selección Abreviada (Menor Cuantía / Subasta)": "ABREVIADA",
    "⚡ Mínima Cuantía": "MINIMA",
    "🎓 Concurso de Méritos": "CONCURSO",
    "📑 Todas las Modalidades (Incluye Contratación Directa)": "TODAS"
}

# ==============================================================================
# FUNCIONES AUXILIARES
# ==============================================================================
def normalizar_texto(texto):
    if not texto or pd.isna(texto):
        return ""
    texto_str = str(texto)
    nfkd = unicodedata.normalize('NFD', texto_str)
    sin_tildes = "".join([c for c in nfkd if unicodedata.category(c) != 'Mn'])
    return sin_tildes.lower().strip()

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
# CONEXIÓN Y DESCARGA FILTRADA EN SERVIDOR (SODA API - DATOS.GOV.CO)
# ==============================================================================
@st.cache_data(ttl=300)
def descargar_base_secop_vlao_60dias(sector_codigo="TODOS", modalidad_codigo="COMPETITIVAS", limite=5000):
    base_url = "https://www.datos.gov.co/resource/p6dx-8zbt.json"
    fecha_hace_60_dias = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%dT00:00:00")
    
    select_cols = (
        "entidad,departamento_entidad,ciudad_entidad,referencia_del_proceso,"
        "codigo_principal_de_categoria,nombre_del_procedimiento,"
        "descripci_n_del_procedimiento,modalidad_de_contratacion,precio_base,"
        "estado_resumen,fase,fecha_de_publicacion_del,fecha_de_ultima_publicaci,"
        "fecha_de_recepcion_de,urlproceso"
    )
    
    # Usamos fecha_de_publicacion_del para traer publicaciones generales
    condiciones = [f"fecha_de_publicacion_del >= '{fecha_hace_60_dias}'"]
    
    # Filtro por códigos UNSPSC de VLAO
    if sector_codigo != "TODOS":
        codigos = sector_codigo.split('|')
        sub_c = [f"codigo_principal_de_categoria like '%{c}%'" for c in codigos]
        condiciones.append(f"({' OR '.join(sub_c)})")
    else:
        sub_c = [f"codigo_principal_de_categoria like '%{s}%'" for s in SECTORES_VLAO_SEGMENTOS]
        condiciones.append(f"({' OR '.join(sub_c)})")

    # Modalidades
    if modalidad_codigo == "COMPETITIVAS":
        condiciones.append("(lower(modalidad_de_contratacion) not like '%directa%')")
    elif modalidad_codigo == "LICITACION":
        condiciones.append("(lower(modalidad_de_contratacion) like '%licitac%')")
    elif modalidad_codigo == "ABREVIADA":
        condiciones.append("(lower(modalidad_de_contratacion) like '%abreviad%')")
    elif modalidad_codigo == "MINIMA":
        condiciones.append("(lower(modalidad_de_contratacion) like '%minima%' or lower(modalidad_de_contratacion) like '%mínima%')")
    elif modalidad_codigo == "CONCURSO":
        condiciones.append("(lower(modalidad_de_contratacion) like '%concurso%')")

    params = {
        "": select_cols,
        "": " AND ".join(condiciones),
        "": "fecha_de_publicacion_del DESC",
        "": str(limite)
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
        conds_fb = [f"fecha_de_publicacion_del >= '{fecha_hace_60_dias}'"]
        params_fb = {
            "": select_cols,
            "": " AND ".join(conds_fb),
            "": "fecha_de_publicacion_del DESC",
            "": str(limite)
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
            
        if 'fecha_de_recepcion_de' in df.columns:
            res_cie = [parsear_fecha_secop(v) for v in df['fecha_de_recepcion_de']]
            df['fecha_cierre_dt'] = [r[0] for r in res_cie]
            df['fecha_cierre_clean'] = [r[1] if r[1] != "Por definir" else "Por definir en pliegos" for r in res_cie]
        else:
            df['fecha_cierre_dt'] = pd.NaT
            df['fecha_cierre_clean'] = "Por definir en pliegos"
            
        # Urgencia
        ahora = pd.Timestamp.now().normalize()
        def calc_dias_restantes(dt):
            if pd.isna(dt):
                return "Por definir"
            diff = (dt - ahora).days
            if diff < 0:
                return "Cerrado"
            elif diff == 0:
                return "🚨 Cierra HOY"
            elif diff <= 3:
                return f"🔴 {diff} días"
            elif diff <= 7:
                return f"🟡 {diff} días"
            else:
                return f"🟢 {diff} días"
        
        df['dias_restantes'] = df['fecha_cierre_dt'].apply(calc_dias_restantes)

    return df

# ==============================================================================
# EXPORTACIÓN SEGURA A EXCEL
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
        'estado_resumen': 'Estado',
        'fase': 'Fase del Proceso',
        'precio_formateado': 'Presupuesto Estimado ($ COP)',
        'fecha_pub_clean': 'Fecha Publicación',
        'fecha_cierre_clean': 'Fecha Cierre Ofertas',
        'dias_restantes': 'Urgencia Cierre',
        'urlproceso': 'Link SECOP II'
    }
    cols = [c for c in columnas_visibles.keys() if c in df_export.columns]
    df_export = df_export[cols].rename(columns={c: columnas_visibles[c] for c in cols})
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Oportunidades_SECOP_VLAO')
    return buffer.getvalue()

# ==============================================================================
# BARRA LATERAL (SIDEBAR) - MODO DE ALTA ESPECIFICIDAD
# ==============================================================================
st.sidebar.header("⚙️ Panel de Control Quirúrgico")

# 1. MODO ENFOQUE QUIRÚRGICO (FILTRO AUTOMÁTICO DE ALTA RELEVANCIA)
modo_especifico = st.sidebar.toggle(
    "🎯 Activar Modo Misión VLAO (Alta Especificidad)",
    value=True,
    help="Aplica automáticamente presupuestos mínimos, excluye contrataciones directas y filtra fases activas para entregar resultados concretos.")

# 2. Especialidades VLAO
especialidad_sel = st.sidebar.selectbox(
    "🏢 Línea de Negocio / Especialidad:",
    options=list(ESPECIALIDADES_VLAO.keys())
)
codigo_especialidad = ESPECIALIDADES_VLAO[especialidad_sel]

# 3. Modalidad
modalidad_sel = st.sidebar.selectbox(
    "📜 Modalidad de Contratación:",
    options=list(MODALIDADES_SODA.keys())
)
codigo_modalidad = MODALIDADES_SODA[modalidad_sel]

# Descargar Lote inicial
limite_descarga = 5000 if modo_especifico else 10000
with st.spinner("🚀 Rastrenando oportunidades concretas en SECOP II..."):
    try:
        df_raw = descargar_base_secop_vlao_60dias(
            sector_codigo=codigo_especialidad,
            modalidad_codigo=codigo_modalidad,
            limite=limite_descarga
        )
    except Exception as e:
        st.error(f"Error de conexión con Datos Abiertos: {e}")
        df_raw = pd.DataFrame()

if not df_raw.empty:
    df = df_raw.copy()

    # A. APLICACIÓN DE FILTROS EN MODO ESPECÍFICO
    if modo_especifico:
        # Excluir contrataciones directas de personas naturales / OPS
        if 'modalidad_de_contratacion' in df.columns:
            df = df[~df['modalidad_de_contratacion'].apply(normalizar_texto).str.contains('directa')]
        
        # Filtrar solo fases abiertas/accionables por defecto
        if 'fase' in df.columns:
            fases_deseadas = ['Selección', 'Presentación de ofertas', 'Convocatoria', 'Borrador', 'Proyecto de pliegos']
            def es_fase_activa(val):
                v_norm = normalizar_texto(val)
                return any(f.lower() in v_norm for f, in [(f,) for f in ['seleccion', 'oferta', 'convocatoria', 'borrador', 'pliego']])
            df = df[df['fase'].apply(es_fase_activa)]

    # B. Presupuesto Mínimo
    st.sidebar.markdown("---")
    st.sidebar.subheader("💰 Presupuesto Mínimo ($ COP)")
    monto_min_def = 30.0 if modo_especifico else 0.0
    monto_minimo_m = st.sidebar.number_input(
        "Presupuesto Mínimo Estimado (Millones COP):",
        min_value=0.0,
        max_value=10000.0,
        value=monto_min_def,
        step=10.0,
        help="Descarta contratos de cuantías menores irrelevantes."    )
    if monto_minimo_m > 0 and 'precio_num' in df.columns:
        df = df[df['precio_num'] >= (monto_minimo_m * 1000000)]

    # C. Filtros Múltiples de Ubicación
    st.sidebar.markdown("---")
    st.sidebar.subheader("📍 Filtro por Ubicación")
    
    if 'departamento_entidad' in df.columns:
        dptos_unicos = sorted([d for d in df['departamento_entidad'].dropna().unique() if d])
        dptos_sel = st.sidebar.multiselect("🗺️ Departamento(s):", options=dptos_unicos, default=[])
        if dptos_sel:
            df = df[df['departamento_entidad'].isin(dptos_sel)]

    if 'ciudad_entidad' in df.columns:
        ciudades_unicas = sorted([c for c in df['ciudad_entidad'].dropna().unique() if c])
        ciudades_sel = st.sidebar.multiselect("📍 Ciudad(es) / Municipio(s):", options=ciudades_unicas, default=[])
        if ciudades_sel:
            df = df[df['ciudad_entidad'].isin(ciudades_sel)]

    # D. Palabra Clave
    st.sidebar.markdown("---")
    palabra_clave = st.sidebar.text_input(
        "🔎 Búsqueda Libre por Palabra Clave:",
        "",
        placeholder="Ej: cubierta, red electrica, impermeabilizacion..."    )
    if palabra_clave.strip():
        kw_norm = normalizar_texto(palabra_clave)
        df = df[
            df['nombre_del_procedimiento'].apply(normalizar_texto).str.contains(kw_norm) |
            df['descripci_n_del_procedimiento'].apply(normalizar_texto).str.contains(kw_norm)
        ]

    # ==============================================================================
    # TABLERO Y RESULTADOS CONCRETOS
    # ==============================================================================
    # KPIs Superiores
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("🎯 Oportunidades Clave", f"{len(df):,} licitaciones")
    with k2:
        monto_tot = df['precio_num'].sum() if 'precio_num' in df.columns else 0
        st.metric("💰 Presupuesto Acumulado", formato_pesos_cop(monto_tot))
    with k3:
        monto_prom = df['precio_num'].mean() if 'precio_num' in df.columns and len(df) > 0 else 0
        st.metric("📈 Promedio por Contrato", formato_pesos_cop(monto_prom))
    with k4:
        muncs = df['ciudad_entidad'].nunique() if 'ciudad_entidad' in df.columns else 0
        st.metric("📍 Municipios / Ciudades", f"{muncs} activos")

    st.divider()

    # SECCIÓN RECOMENDADA: TOP 10 OPORTUNIDADES ESTRELLA
    if not df.empty:
        st.markdown("### ⭐ Top 10 Oportunidades de Alto Valor (Prioridad Comercial)")
        df_top = df.sort_values(by=['precio_num', 'fecha_pub_dt'], ascending=[False, False]).head(10)
        
        for idx, row in df_top.iterrows():
            with st.container():
                st.markdown(f"""
                <div class="opportunity-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span class="card-title">🏢 {row.get('entidad', 'Entidad Estatal')}</span>
                        <span class="card-badge">💰 {row.get('precio_formateado', '$ 0 COP')}</span>
                    </div>
                    <div style="margin-top:8px; font-size:0.95rem; color:#334155;">
                        <b>Objeto:</b> {row.get('nombre_del_procedimiento', 'Sin descripción')}
                    </div>
                    <div style="margin-top:8px; font-size:0.85rem; color:#64748B;">
                        📍 <b>Ubicación:</b> {row.get('ciudad_entidad', 'N/I')}, {row.get('departamento_entidad', 'N/I')} | 
                        📜 <b>Modalidad:</b> {row.get('modalidad_de_contratacion', 'N/I')} | 
                        📌 <b>Fase:</b> {row.get('fase', 'N/I')} | 
                        ⏱️ <b>Urgencia Cierre:</b> {row.get('dias_restantes', 'Por definir')}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                url_link = row.get('urlproceso', '')
                if url_link:
                    st.markdown(f"[👉 Abrir Licitación en SECOP II]({url_link})")
                st.divider()

    # TABLA INTERACTIVA DETALLADA (TOP 50 CONCRETAS)
    st.markdown("### 📋 Listado Detallado de Oportunidades Filtradas")
    st.caption("Mostrando las principales coincidencia exactas ordenadas por presupuesto e impacto.")
    
    cols_mostrar = {
        'entidad': 'Entidad Compradora',
        'ciudad_entidad': 'Municipio',
        'departamento_entidad': 'Departamento',
        'nombre_del_procedimiento': 'Objeto del Contrato',
        'modalidad_de_contratacion': 'Modalidad',
        'fase': 'Fase',
        'precio_formateado': 'Presupuesto Estimado',
        'fecha_pub_clean': 'Publicación',
        'fecha_cierre_clean': 'Cierre Ofertas',
        'dias_restantes': 'Urgencia',
        'urlproceso': 'Link SECOP II'
    }
    
    cols_existentes = [c for c in cols_mostrar.keys() if c in df.columns]
    df_vista = df[cols_existentes].rename(columns={c: cols_mostrar[c] for c in cols_existentes}).head(50)
    
    st.dataframe(
        df_vista,
        use_container_width=True,
        column_config={
            "Link SECOP II": st.column_config.LinkColumn(
                "Link SECOP II",
                help="Abrir la licitación directamente en la plataforma de Colombia Compra Eficiente",
                display_text="Ver Proceso"
            )
        }
    )

    st.markdown("---")
    excel_data = exportar_df_a_excel(df)
    st.download_button(
        label="📥 Exportar Reporte Completo Seleccionado a Excel (.xlsx)",
        data=excel_data,
        file_name=f"radar_vlao_especifico_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.warning("⚠️ No se encontraron resultados que cumplan los criterios de alta especificidad. Te sugerimos reducir el presupuesto mínimo o desactivar el 'Modo Misión VLAO'.")
