import streamlit as st
import pandas as pd
import requests
import urllib.parse
import unicodedata
from datetime import datetime, timedelta

# ---------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA E INTERFAZ SECOP II
# ---------------------------------------------------------
st.set_page_config(
    page_title="Radar SECOP II v10 - Búsqueda Definitiva Multicriterio",
    layout="wide",
    page_icon="🎯"
)

st.title("🎯 Radar Quirúrgico SECOP II - Versión 10.0 (Filtrado de Alto Rendimiento)")
st.markdown("""
**Plataforma de Inteligencia Contractual para VLAO INGENIERÍA S.A.S. y Proponentes Interesados.**  
*Arquitectura optimizada: Descarga en tiempo real de la base nacional de Colombia Compra Eficiente y procesamiento en memoria en Pandas con normalización Unicode de texto.*
""")

# ---------------------------------------------------------
# FUNCIONES AUXILIARES DE NORMALIZACIÓN Y LIMPIEZA
# ---------------------------------------------------------
def normalizar_texto(texto):
    """Elimina acentos, tildes, caracteres especiales y convierte a minúsculas."""
    if not texto or pd.isna(texto):
        return ""
    texto_str = str(texto)
    nfkd = unicodedata.normalize('NFD', texto_str)
    sin_tildes = "".join([c for c in nfkd if unicodedata.category(c) != 'Mn'])
    return sin_tildes.lower().strip()

def extraer_url(val):
    """Extrae la URL limpia del objeto o string entregado por SODA API."""
    if isinstance(val, dict):
        return val.get('url', '')
    val_str = str(val)
    if 'http' in val_str:
        return val_str
    return ''

# ---------------------------------------------------------
# DESCARGA ROBUSTA DESDE LA API DE DATOS ABIERTOS
# ---------------------------------------------------------
@st.cache_data(ttl=300)
def cargar_base_secop(max_registros):
    """
    Descarga una muestra amplia y reciente directamente del servidor oficial de Datos Abiertos.
    Se extraen los campos clave y se procesan en memoria para evitar bloqueos por sintaxis SoQL.
    """
    base_url = "https://www.datos.gov.co/resource/p6dx-8zbt.json"
    select_cols = (
        "entidad,departamento_entidad,ciudad_entidad,referencia_del_proceso,"
        "codigo_principal_de_categoria,nombre_del_procedimiento,"
        "descripci_n_del_procedimiento,modalidad_de_contratacion,precio_base,"
        "estado_resumen,fecha_de_publicacion,fecha_de_recepcion_de,urlproceso"
    )
    
    params = {
        "$select": select_cols,
        "$order": "fecha_de_publicacion DESC",
        "$limit": str(max_registros)
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
    }
    
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    
    data = resp.json()
    df = pd.DataFrame(data)
    
    if not df.empty:
        # 1. Limpieza de presupuesto
        if 'precio_base' in df.columns:
            df['precio_base'] = pd.to_numeric(df['precio_base'], errors='coerce').fillna(0)
            
        # 2. Parseo homogéneo de fechas sin zona horaria
        if 'fecha_de_publicacion' in df.columns:
            df['fecha_dt'] = pd.to_datetime(df['fecha_de_publicacion'], errors='coerce', format='mixed').dt.tz_localize(None)
            df['fecha_pub_clean'] = df['fecha_dt'].dt.strftime('%Y-%m-%d')
        else:
            df['fecha_dt'] = pd.NaT
            df['fecha_pub_clean'] = ''

        if 'fecha_de_recepcion_de' in df.columns:
            df['fecha_cierre_dt'] = pd.to_datetime(df['fecha_de_recepcion_de'], errors='coerce', format='mixed').dt.tz_localize(None)
            df['fecha_cierre_clean'] = df['fecha_cierre_dt'].dt.strftime('%Y-%m-%d %H:%M')
        else:
            df['fecha_cierre_clean'] = ''

        # 3. Normalización de columnas para búsqueda
        df['norm_nombre'] = df['nombre_del_procedimiento'].apply(normalizar_texto) if 'nombre_del_procedimiento' in df.columns else ""
        df['norm_desc'] = df['descripci_n_del_procedimiento'].apply(normalizar_texto) if 'descripci_n_del_procedimiento' in df.columns else ""
        df['norm_mod'] = df['modalidad_de_contratacion'].apply(normalizar_texto) if 'modalidad_de_contratacion' in df.columns else ""
        df['norm_entidad'] = df['entidad'].apply(normalizar_texto) if 'entidad' in df.columns else ""
        df['norm_ciudad'] = df['ciudad_entidad'].apply(normalizar_texto) if 'ciudad_entidad' in df.columns else ""
        df['norm_depto'] = df['departamento_entidad'].apply(normalizar_texto) if 'departamento_entidad' in df.columns else ""
        
    return df

# ---------------------------------------------------------
# BARRA LATERAL - CONTROLES Y FILTROS
# ---------------------------------------------------------
st.sidebar.header("⚙️ Configuración del Radar")

# Slider de límite de datos a consultar
limite_descarga = st.sidebar.slider(
    "📊 Tamaño del lote descargado del SECOP II:",
    min_value=1000, max_value=10000, value=5000, step=1000,
    help="Aumenta este valor si deseas explorar un histórico más amplio de licitaciones."
)

with st.spinner("🚀 Conectando directamente con la API del SECOP II..."):
    try:
        raw_df = cargar_base_secop(limite_descarga)
    except Exception as e:
        st.error(f"Error técnico al conectar con Datos Abiertos: {e}")
        raw_df = pd.DataFrame()

if not raw_df.empty:
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔎 Filtros de Búsqueda Quirúrgica")

    # 1. Palabra Clave
    kw_input = st.sidebar.text_input(
        "🔎 Palabra Clave (Objeto / Nombre):",
        value="",
        placeholder="Ej: cubierta, ferreteria, mantenimiento, herramientas..."
    )

    # 2. Ventana de Tiempo
    opciones_periodo = [
        "Todos los procesos descargados (Sin restricción de fecha)",
        "Últimos 30 Días",
        "Últimos 60 Días",
        "Últimos 90 Días",
        "Año 2026 Completo"
    ]
    periodo_sel = st.sidebar.selectbox("📅 Ventana de Tiempo (Publicación):", opciones_periodo)

    # 3. Modalidad de Contratación
    MODALIDADES_DICT = {
        "🌐 Todas las Modalidades (100% SECOP II)": "TODAS",
        "⚡ Mínima Cuantía (Sin RUP - Art. 2 Ley 1150/2007)": "MINIMA",
        "📋 Selección Abreviada (Menor Cuantía / Subasta)": "ABREVIADA",
        "🏛️ Licitación Pública": "LICITACION",
        "🎓 Concurso de Méritos": "CONCURSO",
        "📑 Contratación Directa": "DIRECTA",
        "🏢 Régimen Especial (Empresas Públicas, E.S.E.)": "REGIMEN_ESPECIAL",
        "🛒 Acuerdo Marco / Tienda Virtual CCE": "ACUERDO_MARCO"
    }
    modalidad_sel = st.sidebar.selectbox("📜 Modalidad de Contratación:", options=list(MODALIDADES_DICT.keys()))

    # 4. Categoría UNSPSC
    CATEGORIAS_UNSPSC = {
        "🌐 Todos los Sectores (Sin Restricción)": "TODOS",
        "🛠️ Ferretería y Herrajes (3116)": "3116",
        "🔧 Herramientas de Mano (2711)": "2711",
        "🏗️ Materiales de Construcción (3010 / 3019)": "3010",
        "⚡ Equipos y Suministros Eléctricos (3912)": "3912",
        "🎨 Pinturas y Recubrimientos (3121)": "3121",
        "🚰 Tuberías y Plomería (4014)": "4014",
        "💡 Iluminación y Luminarias (3911)": "3911",
        "💻 Tecnología, Software y Comunicaciones (4321/4323)": "4321",
        "🏥 Salud y Equipos Médicos (4200/5100)": "4200",
        "🚗 Vehículos y Maquinaria (2510/7818)": "2510",
        "🛡️ Vigilancia y Seguridad (9212)": "9212"
    }
    sector_sel = st.sidebar.selectbox("🏢 Sector / Categoría UNSPSC:", options=list(CATEGORIAS_UNSPSC.keys()))

    # 5. Filtro de Ubicación
    ciudad_kw = st.sidebar.text_input("📍 Ciudad / Municipio:", value="", placeholder="Ej: Bogota, Medellin, Cali, Neiva...")
    entidad_kw = st.sidebar.text_input("🏛️ Entidad Compradora:", value="", placeholder="Ej: SENA, Alcaldia, Ejercito, Hospital...")

    # ---------------------------------------------------------
    # PROCESAMIENTO MULTICRITERIO EN PANDAS
    # ---------------------------------------------------------
    df = raw_df.copy()

    # A. Filtro por Palabra Clave
    if kw_input.strip():
        pk = normalizar_texto(kw_input)
        df = df[df['norm_nombre'].str.contains(pk, na=False) | df['norm_desc'].str.contains(pk, na=False)]

    # B. Filtro por Fecha
    if "Sin restricción" not in periodo_sel and df['fecha_dt'].notna().any():
        max_fecha = df['fecha_dt'].max()
        if "30 Días" in periodo_sel:
            corte = max_fecha - timedelta(days=30)
            df = df[df['fecha_dt'] >= corte]
        elif "60 Días" in periodo_sel:
            corte = max_fecha - timedelta(days=60)
            df = df[df['fecha_dt'] >= corte]
        elif "90 Días" in periodo_sel:
            corte = max_fecha - timedelta(days=90)
            df = df[df['fecha_dt'] >= corte]
        elif "Año 2026" in periodo_sel:
            df = df[df['fecha_dt'] >= pd.Timestamp('2026-01-01')]

    # C. Filtro por Modalidad
    cod_mod = MODALIDADES_DICT[modalidad_sel]
    if cod_mod == "MINIMA":
        df = df[df['norm_mod'].str.contains('minima|cuantia', na=False)]
    elif cod_mod == "ABREVIADA":
        df = df[df['norm_mod'].str.contains('abreviada|subasta|menor cuantia', na=False)]
    elif cod_mod == "LICITACION":
        df = df[df['norm_mod'].str.contains('licitacion|licitacion publica', na=False)]
    elif cod_mod == "CONCURSO":
        df = df[df['norm_mod'].str.contains('concurso|meritos', na=False)]
    elif cod_mod == "DIRECTA":
        df = df[df['norm_mod'].str.contains('directa', na=False)]
    elif cod_mod == "REGIMEN_ESPECIAL":
        df = df[df['norm_mod'].str.contains('especial|regimen', na=False)]
    elif cod_mod == "ACUERDO_MARCO":
        df = df[df['norm_mod'].str.contains('marco|tienda', na=False)]

    # D. Filtro por Categoría UNSPSC
    cod_cat = CATEGORIAS_UNSPSC[sector_sel]
    if cod_cat != "TODOS" and 'codigo_principal_de_categoria' in df.columns:
        df = df[df['codigo_principal_de_categoria'].astype(str).str.contains(cod_cat, na=False)]

    # E. Filtro por Ciudad
    if ciudad_kw.strip():
        ckw = normalizar_texto(ciudad_kw)
        df = df[df['norm_ciudad'].str.contains(ckw, na=False)]

    # F. Filtro por Entidad
    if entidad_kw.strip():
        ekw = normalizar_texto(entidad_kw)
        df = df[df['norm_entidad'].str.contains(ekw, na=False)]

    # ---------------------------------------------------------
    # DESPLIEGUE DE RESULTADOS Y FILTROS INTERACTIVOS EN PANTALLA
    # ---------------------------------------------------------
    st.markdown(f"📊 **Lote Base Descargado:** `{len(raw_df):,}` procesos recientes | 🎯 **Coincidencias Filtradas:** `{len(df):,}` licitaciones")

    if not df.empty:
        # Filtros secundarios interactivos en pantalla (Multiselect sobre resultados)
        st.markdown("##### 🎛️ Refinar Resultados en Pantalla (Filtro Rápido)")
        f_col1, f_col2, f_col3 = st.columns(3)
        
        with f_col1:
            list_deptos = sorted([d for d in df['departamento_entidad'].dropna().unique() if d])
            sel_deptos = st.multiselect("Filtrar por Departamento:", options=list_deptos)
        with f_col2:
            list_ciudades = sorted([c for c in df['ciudad_entidad'].dropna().unique() if c])
            sel_ciudades = st.multiselect("Filtrar por Ciudad / Municipio:", options=list_ciudades)
        with f_col3:
            list_entidades = sorted([e for e in df['entidad'].dropna().unique() if e])
            sel_entidades = st.multiselect("Filtrar por Entidad Compradora:", options=list_entidades)

        if sel_deptos:
            df = df[df['departamento_entidad'].isin(sel_deptos)]
        if sel_ciudades:
            df = df[df['ciudad_entidad'].isin(sel_ciudades)]
        if sel_entidades:
            df = df[df['entidad'].isin(sel_entidades)]

        # Métricas Clave
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Licitaciones Visibles", f"{len(df):,}")
        with m2:
            st.metric("Bolsa Total Disponible", f"${df['precio_base'].sum():,.0f} COP")
        with m3:
            top_depto = df['departamento_entidad'].value_counts().index[0] if 'departamento_entidad' in df.columns and not df.empty else "N/A"
            st.metric("Departamento Líder", top_depto)
        with m4:
            top_mod = df['modalidad_de_contratacion'].value_counts().index[0] if 'modalidad_de_contratacion' in df.columns and not df.empty else "N/A"
            st.metric("Modalidad Dominante", top_mod[:20])

        st.markdown("---")

        # Preparación de la Tabla
        data_display = df.copy()
        data_display['url_clean'] = data_display['urlproceso'].apply(extraer_url) if 'urlproceso' in data_display.columns else ""

        cols_map = {
            'referencia_del_proceso': 'Proceso',
            'entidad': 'Entidad Compradora',
            'departamento_entidad': 'Departamento',
            'ciudad_entidad': 'Ciudad / Municipio',
            'modalidad_de_contratacion': 'Modalidad',
            'nombre_del_procedimiento': 'Objeto del Proceso',
            'precio_base': 'Presupuesto ($ COP)',
            'fecha_pub_clean': 'Fecha Publicación',
            'fecha_cierre_clean': 'Cierre Ofertas',
            'url_clean': 'Enlace SECOP II'
        }

        cols_existentes = [c for c in cols_map.keys() if c in data_display.columns]
        data_final = data_display[cols_existentes].rename(columns=cols_map)

        st.dataframe(
            data_final,
            column_config={
                "Enlace SECOP II": st.column_config.LinkColumn("Enlace SECOP II", display_text="Ver Pliegos 🔗"),
                "Presupuesto ($ COP)": st.column_config.NumberColumn("Presupuesto ($ COP)", format="$%'.0f"),
            },
            use_container_width=True,
            hide_index=True
        )

        csv_data = data_final.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar Reporte Personalizado en CSV / Excel",
            data=csv_data,
            file_name=f"Radar_SECOP_v10_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.warning("⚠️ No se encontraron procesos que coincidan con la combinación exacta de filtros seleccionada.")
        st.info("""
        💡 **Sugerencia:**
        * Si aplicaste múltiples criterios a la vez (ej. *Licitación Pública + Ciudad Específica + Palabra Clave*), intenta borrar la ciudad o cambiar la ventana a **'Todos los procesos descargados'** para ampliar la muestra.
        * Puedes aumentar el **'Tamaño del lote descargado'** en el control superior de la barra lateral a 10,000 registros para revisar un periodo más amplio del SECOP II.
        """)
else:
    st.error("No se pudieron cargar datos del SECOP II. Verifica la conexión con la API de Datos Abiertos.")
