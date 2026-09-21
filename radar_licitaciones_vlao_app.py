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
    page_title="Radar SECOP II v17.0 - VLAO INGENIERÍA S.A.S.",
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
        background-color: #F8FAFC;
        padding: 12px;
        border-radius: 8px;
        border-left: 4px solid #1E3A8A;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .urgency-red {
        color: #DC2626;
        font-weight: bold;
    }
    .urgency-yellow {
        color: #D97706;
        font-weight: bold;
    }
    .urgency-green {
        color: #059669;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🎯 Radar Inteligente SECOP II - Versión 17.0</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title"><b>VLAO INGENIERÍA S.A.S.</b> | Centro de Inteligencia de Negocios y Licimétrica Comercial</div>', unsafe_allow_html=True)

# ==============================================================================
# DICCIONARIOS Y CONFIGURACIONES DE VLAO INGENIERÍA S.A.S.
# ==============================================================================
CATEGORIAS_UNSPSC = {
    "🌐 Portafolio Completo VLAO": "TODOS",
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
# CONEXIÓN A DATOS ABIERTOS (SODA API CON FECHA_DE_PUBLICACION_DEL)
# ==============================================================================
@st.cache_data(ttl=300)
def descargar_base_secop_vlao_60dias(sector_codigo="TODOS", modalidad_codigo="TODAS", limite=5000):
    base_url = "https://www.datos.gov.co/resource/p6dx-8zbt.json"
    fecha_hace_60_dias = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%dT00:00:00")
    
    select_cols = (
        "entidad,departamento_entidad,ciudad_entidad,referencia_del_proceso,"
        "codigo_principal_de_categoria,nombre_del_procedimiento,"
        "descripci_n_del_procedimiento,modalidad_de_contratacion,precio_base,"
        "estado_resumen,fase,fecha_de_publicacion_del,fecha_de_ultima_publicaci,"
        "fecha_de_recepcion_de,urlproceso"
    )
    
    # IMPORTANTE: Usamos fecha_de_publicacion_del para traer la fecha general sin sesgar a Manifestación de Interés
    condiciones = [f"fecha_de_publicacion_del >= '{fecha_hace_60_dias}'"]
    
    if sector_codigo != "TODOS":
        codigos = sector_codigo.split('|')
        sub_c = [f"codigo_principal_de_categoria like '%{c}%'" for c in codigos]
        condiciones.append(f"({' OR '.join(sub_c)})")
    else:
        sub_c = [f"codigo_principal_de_categoria like '%{s}%'" for s in SECTORES_VLAO_SEGMENTOS]
        condiciones.append(f"({' OR '.join(sub_c)})")

    if modalidad_codigo == "LICITACION":
        condiciones.append("(modalidad_de_contratacion like '%Licitaci%' or modalidad_de_contratacion like '%licitaci%')")
    elif modalidad_codigo == "ABREVIADA":
        condiciones.append("(modalidad_de_contratacion like '%Abreviada%' or modalidad_de_contratacion like '%abreviada%')")
    elif modalidad_codigo == "MINIMA":
        condiciones.append("(modalidad_de_contratacion like '%mínima%' or modalidad_de_contratacion like '%minima%')")
    elif modalidad_codigo == "CONCURSO":
        condiciones.append("(modalidad_de_contratacion like '%Concurso%' or modalidad_de_contratacion like '%concurso%')")
    elif modalidad_codigo == "DIRECTA":
        condiciones.append("(modalidad_de_contratacion like '%Directa%' or modalidad_de_contratacion like '%directa%')")

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
        conds_fb = [f"fecha_de_publicacion_del >= '{fecha_hace_60_dias}'"]
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
            
        if 'fecha_de_recepcion_de' in df.columns:
            res_cie = [parsear_fecha_secop(v) for v in df['fecha_de_recepcion_de']]
            df['fecha_cierre_dt'] = [r[0] for r in res_cie]
            df['fecha_cierre_clean'] = [r[1] if r[1] != "Por definir" else "Por definir en pliegos" for r in res_cie]
        else:
            df['fecha_cierre_dt'] = pd.NaT
            df['fecha_cierre_clean'] = "Por definir en pliegos"
            
        # Cálculo de Urgencia (Días para cierre)
        ahora = pd.Timestamp.now().normalize()
        def calc_dias_restantes(dt):
            if pd.isna(dt):
                return "Por definir"
            diff = (dt - ahora).days
            if diff < 0:
                return "Cerrado"
            elif diff == 0:
                return "🚨 ¡Cierra HOY!"
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
# BARRA LATERAL (SIDEBAR) - FILTROS ORGANIZADOS POR SECCIONES
# ==============================================================================
st.sidebar.header("⚙️ Panel de Filtros Inteligentes")

# 1. Configuración de Descarga
limite_descarga = st.sidebar.slider("📊 Lote de recuperación de Datos Abiertos:", 1000, 20000, 5000, 1000)

# 2. Filtro por Actividad / Sector UNSPSC
sector_sel = st.sidebar.selectbox(
    "🏢 Actividad / Sector UNSPSC (VLAO):",
    options=list(CATEGORIAS_UNSPSC.keys())
)
codigo_sector = CATEGORIAS_UNSPSC[sector_sel]

# 3. Filtro por Tipo de Contrato (Modalidad)
modalidad_sel = st.sidebar.selectbox(
    "📜 Tipo de Contrato / Modalidad:",
    options=list(MODALIDADES_SODA.keys())
)
codigo_modalidad = MODALIDADES_SODA[modalidad_sel]

# Cargar Datos desde API
with st.spinner("🚀 Recuperando licitaciones actualizadas de Colombia Compra Eficiente..."):
    try:
        df_raw = descargar_base_secop_vlao_60dias(
            sector_codigo=codigo_sector,
            modalidad_codigo=codigo_modalidad,
            limite=limite_descarga
        )
    except Exception as e:
        st.error(f"Error de conexión con Datos Abiertos: {e}")
        df_raw = pd.DataFrame()

if not df_raw.empty:
    df = df_raw.copy()

    # A. Filtro por Rango de Montos (Presupuesto)
    st.sidebar.markdown("---")
    st.sidebar.subheader("💰 Filtro por Monto ($ COP)")
    if 'precio_num' in df.columns and df['precio_num'].max() > 0:
        max_monto_m = float(df['precio_num'].max() / 1000000)
        rango_monto_m = st.sidebar.slider(
            "Rango de Presupuesto (Millones COP):",
            min_value=0.0,
            max_value=max(100.0, max_monto_m),
            value=(0.0, max(100.0, max_monto_m)),
            step=10.0,
            format="$%dM"
        )
        min_pesos = rango_monto_m[0] * 1000000
        max_pesos = rango_monto_m[1] * 1000000
        df = df[(df['precio_num'] >= min_pesos) & (df['precio_num'] <= max_pesos)]

    # B. Filtros de Lugar (Ubicación Geográfica Múltiple)
    st.sidebar.markdown("---")
    st.sidebar.subheader("📍 Filtro por Lugar (Ubicación)")
    
    if 'departamento_entidad' in df.columns:
        dptos_unicos = sorted([d for d in df['departamento_entidad'].dropna().unique() if d])
        dptos_sel = st.sidebar.multiselect(
            "🗺️ Departamento(s):",
            options=dptos_unicos,
            default=[]
        )
        if dptos_sel:
            df = df[df['departamento_entidad'].isin(dptos_sel)]

    if 'ciudad_entidad' in df.columns:
        ciudades_unicas = sorted([c for c in df['ciudad_entidad'].dropna().unique() if c])
        ciudades_sel = st.sidebar.multiselect(
            "📍 Ciudad(es) / Municipio(s):",
            options=ciudades_unicas,
            default=[]
        )
        if ciudades_sel:
            df = df[df['ciudad_entidad'].isin(ciudades_sel)]

    # C. Filtros por Estado y Fase
    st.sidebar.markdown("---")
    st.sidebar.subheader("📌 Filtro por Estado y Etapa")
    
    if 'fase' in df.columns:
        fases_unicas = sorted([f for f in df['fase'].dropna().unique() if f])
        fases_sel = st.sidebar.multiselect(
            "📋 Fase / Etapa del Proceso:",
            options=fases_unicas,
            default=[]
        )
        if fases_sel:
            df = df[df['fase'].isin(fases_sel)]

    if 'estado_resumen' in df.columns:
        estados_unicos = sorted([e for e in df['estado_resumen'].dropna().unique() if e])
        estados_sel = st.sidebar.multiselect(
            "📌 Estado del Proceso:",
            options=estados_unicos,
            default=[]
        )
        if estados_sel:
            df = df[df['estado_resumen'].isin(estados_sel)]

    # D. Filtro por Palabra Clave Libre
    st.sidebar.markdown("---")
    palabra_clave = st.sidebar.text_input(
        "🔎 Búsqueda Libre por Palabra Clave:",
        "",
        placeholder="Ej: cubierta, red electrica, impermeabilizacion..."
    )
    if palabra_clave.strip():
        kw_norm = normalizar_texto(palabra_clave)
        df = df[
            df['nombre_del_procedimiento'].apply(normalizar_texto).str.contains(kw_norm) |
            df['descripci_n_del_procedimiento'].apply(normalizar_texto).str.contains(kw_norm)
        ]

    # ==============================================================================
    # TABLERO Y PESTAÑAS INTERACTIVAS
    # ==============================================================================
    # Métricas KPI Superiores
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric("🎯 Oportunidades Filtradas", f"{len(df):,} licitaciones")
    with kpi2:
        monto_tot = df['precio_num'].sum() if 'precio_num' in df.columns else 0
        st.metric("💰 Presupuesto Acumulado", formato_pesos_cop(monto_tot))
    with kpi3:
        monto_prom = df['precio_num'].mean() if 'precio_num' in df.columns and len(df) > 0 else 0
        st.metric("📈 Promedio por Contrato", formato_pesos_cop(monto_prom))
    with kpi4:
        muncs = df['ciudad_entidad'].nunique() if 'ciudad_entidad' in df.columns else 0
        st.metric("📍 Municipios / Ciudades", f"{muncs} activos")

    st.divider()

    # Pestañas principales de navegación
    tab_listado, tab_graficos, tab_urgencia = st.tabs([
        "📋 Listado Operativo de Licitaciones",
        "📊 Analytics y Distribución Visual",
        "⏱️ Radar de Urgencia (Cierre de Ofertas)"
    ])

    # --------------------------------------------------------------------------
    # PESTAÑA 1: LISTADO OPERATIVO
    # --------------------------------------------------------------------------
    with tab_listado:
        st.markdown(f"#### 📋 Oportunidades Encontradas ({len(df)} Registros)")
        
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
        df_vista = df[cols_existentes].rename(columns={c: cols_mostrar[c] for c in cols_existentes})
        
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
            label="📥 Exportar Lista Seleccionada a Excel (.xlsx)",
            data=excel_data,
            file_name=f"radar_vlao_secop_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # --------------------------------------------------------------------------
    # PESTAÑA 2: ANALYTICS Y DISTRIBUCIÓN VISUAL
    # --------------------------------------------------------------------------
    with tab_graficos:
        st.markdown("#### 📊 Análisis Visual de Oportunidades")
        
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            if 'departamento_entidad' in df.columns and not df.empty:
                st.markdown("##### 🗺️ Presupuesto Acumulado por Departamento ($ COP)")
                monto_dpto = df.groupby('departamento_entidad')['precio_num'].sum().sort_values(ascending=False).head(10)
                st.bar_chart(monto_dpto)

        with col_g2:
            if 'modalidad_de_contratacion' in df.columns and not df.empty:
                st.markdown("##### 📜 Distribución de Contratos por Modalidad")
                conteo_mod = df['modalidad_de_contratacion'].value_counts()
                st.bar_chart(conteo_mod)

        st.markdown("---")
        if 'fase' in df.columns and not df.empty:
            st.markdown("##### 📌 Oportunidades por Fase del Proceso")
            conteo_fase = df['fase'].value_counts()
            st.bar_chart(conteo_fase)

    # --------------------------------------------------------------------------
    # PESTAÑA 3: RADAR DE URGENCIA
    # --------------------------------------------------------------------------
    with tab_urgencia:
        st.markdown("#### ⏱️ Próximos Cierres de Ofertas (Prioridad Comercial)")
        
        if 'dias_restantes' in df.columns and not df.empty:
            df_urgentes = df[df['dias_restantes'].str.contains('🔴|🚨|🟡', regex=True)].copy()
            if not df_urgentes.empty:
                st.warning(f"🚨 Se detectaron **{len(df_urgentes)}** licitaciones con cierre en los próximos 7 días.")
                
                cols_urgentes = ['entidad', 'ciudad_entidad', 'nombre_del_procedimiento', 'precio_formateado', 'fecha_cierre_clean', 'dias_restantes', 'urlproceso']
                cols_exist = [c for c in cols_urgentes if c in df_urgentes.columns]
                
                st.dataframe(
                    df_urgentes[cols_exist].rename(columns={
                        'entidad': 'Entidad',
                        'ciudad_entidad': 'Municipio',
                        'nombre_del_procedimiento': 'Objeto',
                        'precio_formateado': 'Presupuesto',
                        'fecha_cierre_clean': 'Cierre Ofertas',
                        'dias_restantes': 'Urgencia',
                        'urlproceso': 'Link SECOP II'
                    }),
                    use_container_width=True,
                    column_config={
                        "Link SECOP II": st.column_config.LinkColumn("Link SECOP II", display_text="Ver Proceso")
                    }
                )
            else:
                st.info("ℹ️ No hay licitaciones críticas con cierre en los próximos 7 días dentro del filtro seleccionado.")

else:
    st.warning("⚠️ No se encontraron resultados con los filtros aplicados. Te sugerimos reiniciar los filtros o aumentar el lote de descarga en la barra lateral.")
