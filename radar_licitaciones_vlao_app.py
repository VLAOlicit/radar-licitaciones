import streamlit as st
import pandas as pd
import requests
import urllib.parse
import unicodedata
from datetime import datetime, timedelta

# Configuración de la página en Streamlit
st.set_page_config(
    page_title="Radar SECOP II v15 - VLAO INGENIERÍA S.A.S.",
    layout="wide",
    page_icon="🎯"
)

# Estilos CSS personalizados
st.markdown("""
<style>
    .main-title { font-size: 2.2rem; color: #1E3A8A; font-weight: bold; margin-bottom: 0px; }
    .sub-title { font-size: 1.1rem; color: #4B5563; margin-bottom: 15px; }
    .badge-info { background-color: #EFF6FF; color: #1E40AF; padding: 12px; border-radius: 8px; font-weight: 500; margin-bottom: 15px; border-left: 5px solid #3B82F6; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🎯 Radar Quirúrgico SECOP II - Versión 15.0</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title"><b>VLAO INGENIERÍA S.A.S.</b> | Módulo Operativo de Oportunidades (Conexión Estable sin Errores de Columna + Formato $ COP)</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# FUNCIONES AUXILIARES: NORMALIZACIÓN Y FORMATO DE MONEDA
# ---------------------------------------------------------
def normalizar_texto(texto):
    """Elimina acentos, tildes y caracteres especiales para búsquedas exactas."""
    if not texto or pd.isna(texto):
        return ""
    texto_str = str(texto)
    nfkd = unicodedata.normalize('NFD', texto_str)
    sin_tildes = "".join([c for c in nfkd if unicodedata.category(c) != 'Mn'])
    return sin_tildes.lower().strip()

def formato_pesos_cop(valor):
    """Formatea valores numéricos a Pesos Colombianos con separadores de miles y millones (puntos)."""
    try:
        val = float(valor)
        if pd.isna(val) or val == 0:
            return "$ 0 COP"
        return f"$ {val:,.0f} COP".replace(",", ".")
    except Exception:
        return "$ 0 COP"

# ---------------------------------------------------------
# BARRA LATERAL (SIDEBAR) - CONFIGURACIÓN DE FILTROS
# ---------------------------------------------------------
st.sidebar.header("⚙️ Filtros Principales del Radar")

# 1. Palabra Clave Libre
palabra_clave = st.sidebar.text_input(
    "🔎 Palabra clave (Objeto o Nombre):",
    "",
    placeholder="Ej: cubierta, ferreteria, mantenimiento, impermeabilizacion, suministro, redes..."
)

# 2. Ventana de Tiempo
periodo = st.sidebar.selectbox(
    "📅 Ventana de Tiempo (Fecha de Publicación):",
    [
        "Todos los procesos recientes (Recomendado)",
        "Últimos 30 Días de Publicación",
        "Últimos 60 Días de Publicación",
        "Últimos 90 Días de Publicación",
        "Año 2026 Completo"
    ]
)

# 3. Modalidades completas del SECOP II
MODALIDADES_SECOP = {
    "🌐 Todas las Modalidades (100% del SECOP II)": "TODAS",
    "⚡ Mínima Cuantía (Sin RUP - Art. 2 Ley 1150/2007)": "MINIMA",
    "📋 Selección Abreviada (Menor Cuantía / Subasta Inversa)": "ABREVIADA",
    "🏛️ Licitación Pública": "LICITACION",
    "🎓 Concurso de Méritos": "CONCURSO",
    "📑 Contratación Directa Corporativa": "DIRECTA",
    "🏢 Régimen Especial (Empresas Públicas, Hospitales, Universidades)": "REGIMEN_ESPECIAL",
    "🛒 Acuerdo Marco de Precios / Tienda Virtual CCE": "ACUERDO_MARCO"
}

modalidad_sel = st.sidebar.selectbox(
    "📜 Modalidad de Contratación:",
    options=list(MODALIDADES_SECOP.keys())
)

# Interruptor de Contratación Directa Inteligente (Filtro Anti-OPS)
incluir_cd_inteligente = st.sidebar.checkbox(
    "🛡️ Contratación Directa Inteligente (Excluir OPS / Honorarios)",
    value=True,
    help="Al estar activado, elimina automáticamente las contrataciones directas de personas naturales (OPS) y conserva únicamente urgencias manifiestas, suministros y obras corporativas."
)

# 4. Búsqueda por Ciudad / Municipio
ciudad_query = st.sidebar.text_input(
    "📍 Búsqueda por Ciudad / Municipio:",
    "",
    placeholder="Ej: Bogota, Medellin, Cali, Neiva, Villavicencio..."
)

# 5. Búsqueda por Entidad Compradora
entidad_query = st.sidebar.text_input(
    "🏛️ Búsqueda por Entidad Compradora:",
    "",
    placeholder="Ej: SENA, Ejercito, Registraduria, ICBF, Alcaldia, Hospital..."
)

# 6. Sectores UNSPSC de VLAO INGENIERÍA S.A.S.
CATEGORIAS_UNSPSC = {
    "🌐 Todos los Sectores (Sin Restricción)": "TODOS",
    "🛠️ Ferretería, Herrajes y Construcción (3116 / 3010)": "3116|3010",
    "🔧 Herramientas de Mano y Maquinaria (2711 / 2510)": "2711|2510",
    "⚡ Equipos, Materiales Eléctricos e Iluminación (3912 / 3911 / 2612)": "3912|3911|2612",
    "🎨 Pinturas, Acabados e Impermeabilización (3121 / 3015)": "3121|3015",
    "🚰 Tuberías, Plomería y Sanitarios (4014 / 4017 / 3018)": "4014|4017|3018",
    "🏗️ Obras Civiles, Edificaciones y Mantenimiento (7210 / 7212 / 7214 / 7215)": "7210|7212|7214|7215",
    "📐 Consultoría, Diseños e Interventoría (8110 / 8010)": "8110|8010"
}

sector_sel = st.sidebar.selectbox(
    "🏢 Sector / Categoría UNSPSC:",
    options=list(CATEGORIAS_UNSPSC.keys())
)

# 7. Slider de Lote de Descarga
limite_descarga = st.sidebar.slider("📊 Muestra descargada de Datos Abiertos:", 1000, 10000, 5000, 1000)

# ---------------------------------------------------------
# DESCARGA DE DATOS EN VIVO DE DATOS.GOV.CO (SODA API)
# ---------------------------------------------------------
@st.cache_data(ttl=300)
def descargar_base_secop(limite):
    base_url = "https://www.datos.gov.co/resource/p6dx-8zbt.json"
    # Campos válidos oficiales del esquema p6dx-8zbt del SECOP II
    select_cols = "entidad,departamento_entidad,ciudad_entidad,referencia_del_proceso,codigo_principal_de_categoria,nombre_del_procedimiento,descripci_n_del_procedimiento,modalidad_de_contratacion,precio_base,estado_resumen,fecha_de_publicacion,fecha_de_recepcion_de,urlproceso"
    
    params = {
        "$select": select_cols,
        "$limit": str(limite),
        "$order": "fecha_de_publicacion DESC"
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
        if 'precio_base' in df.columns:
            df['precio_num'] = pd.to_numeric(df['precio_base'], errors='coerce').fillna(0)
            df['precio_formateado'] = df['precio_num'].apply(formato_pesos_cop)
        else:
            df['precio_num'] = 0
            df['precio_formateado'] = "$ 0 COP"
            
        # PROCESAMIENTO ROBUSTO DE FECHAS
        if 'fecha_de_publicacion' in df.columns:
            df['fecha_pub_dt'] = pd.to_datetime(df['fecha_de_publicacion'], errors='coerce')
            df['fecha_pub_clean'] = df['fecha_pub_dt'].dt.strftime('%Y-%m-%d').fillna("Publicado recientemente")
        else:
            df['fecha_pub_dt'] = pd.NaT
            df['fecha_pub_clean'] = "Publicado recientemente"
            
        if 'fecha_de_recepcion_de' in df.columns:
            df['fecha_cierre_dt'] = pd.to_datetime(df['fecha_de_recepcion_de'], errors='coerce')
            df['fecha_cierre_clean'] = df['fecha_cierre_dt'].dt.strftime('%Y-%m-%d %H:%M').fillna("Por definir en pliegos")
        else:
            df['fecha_cierre_clean'] = "Por definir en pliegos"
            
    return df

with st.spinner("🚀 Conectando en vivo con la base de datos del SECOP II (Datos Abiertos Colombia)..."):
    try:
        df_raw = descargar_base_secop(limite_descarga)
    except Exception as e:
        st.error(f"Error técnico de conexión con el servidor de Datos Abiertos: {e}")
        df_raw = pd.DataFrame()

# ---------------------------------------------------------
# MOTOR DE FILTRADO INTELIGENTE EN MEMORIA (PANDAS)
# ---------------------------------------------------------
if not df_raw.empty:
    df = df_raw.copy()
    
    # Pre-crear columnas normalizadas sin tildes para filtros instantáneos
    df['nom_norm'] = df['nombre_del_procedimiento'].apply(normalizar_texto)
    df['desc_norm'] = df['descripci_n_del_procedimiento'].apply(normalizar_texto)
    df['mod_norm'] = df['modalidad_de_contratacion'].apply(normalizar_texto)
    df['ciudad_norm'] = df['ciudad_entidad'].apply(normalizar_texto)
    df['entidad_norm'] = df['entidad'].apply(normalizar_texto)
    df['depto_norm'] = df['departamento_entidad'].apply(normalizar_texto)
    
    # A. Filtro Anti-OPS en Contratación Directa
    if incluir_cd_inteligente:
        is_cd = df['mod_norm'].str.contains('directa', na=False)
        terms_ops = 'prestacion de servicios|apoyo a la gestion|honorarios|profesionales|persona natural'
        is_ops = df['nom_norm'].str.contains(terms_ops, na=False) | df['desc_norm'].str.contains(terms_ops, na=False)
        terms_corp = 'suministro|compra|adquisicion|obra|mantenimiento|adecuacion|impermeabilizacion|cubierta|equipos|materiales|interventoria'
        is_corp = df['nom_norm'].str.contains(terms_corp, na=False) | df['desc_norm'].str.contains(terms_corp, na=False)
        
        descartar_ops = is_cd & is_ops & (~is_corp)
        df = df[~descartar_ops]

    # B. Filtro de Palabra Clave libre
    if palabra_clave.strip():
        pk = normalizar_texto(palabra_clave)
        cond_nom = df['nom_norm'].str.contains(pk, na=False)
        cond_desc = df['desc_norm'].str.contains(pk, na=False)
        df = df[cond_nom | cond_desc]

    # C. FILTRO INTELIGENTE DE FECHA DE PUBLICACIÓN (Conserva registros sin fecha que estén activos)
    if 'fecha_pub_dt' in df.columns and df['fecha_pub_dt'].notna().any():
        valid_dates = df['fecha_pub_dt'].dropna()
        max_fecha_pub = valid_dates.max() if not valid_dates.empty else pd.Timestamp.now()
        
        if "30 Días" in periodo:
            corte = max_fecha_pub - pd.Timedelta(days=30)
            df = df[(df['fecha_pub_dt'] >= corte) | (df['fecha_pub_dt'].isna())]
        elif "60 Días" in periodo:
            corte = max_fecha_pub - pd.Timedelta(days=60)
            df = df[(df['fecha_pub_dt'] >= corte) | (df['fecha_pub_dt'].isna())]
        elif "90 Días" in periodo:
            corte = max_fecha_pub - pd.Timedelta(days=90)
            df = df[(df['fecha_pub_dt'] >= corte) | (df['fecha_pub_dt'].isna())]
        elif "Año 2026" in periodo:
            df = df[(df['fecha_pub_dt'] >= pd.Timestamp('2026-01-01')) | (df['fecha_pub_dt'].isna())]

    # D. Filtro de Modalidad
    cod_mod = MODALIDADES_SECOP[modalidad_sel]
    if cod_mod == "MINIMA":
        df = df[df['mod_norm'].str.contains('minima|cuantia', na=False)]
    elif cod_mod == "ABREVIADA":
        df = df[df['mod_norm'].str.contains('abreviada|subasta|menor cuantia', na=False)]
    elif cod_mod == "LICITACION":
        df = df[df['mod_norm'].str.contains('licitacion', na=False)]
    elif cod_mod == "CONCURSO":
        df = df[df['mod_norm'].str.contains('concurso|meritos', na=False)]
    elif cod_mod == "DIRECTA":
        df = df[df['mod_norm'].str.contains('directa', na=False)]
    elif cod_mod == "REGIMEN_ESPECIAL":
        df = df[df['mod_norm'].str.contains('especial|regimen', na=False)]
    elif cod_mod == "ACUERDO_MARCO":
        df = df[df['mod_norm'].str.contains('marco|tienda', na=False)]

    # E. Filtro por Ciudad / Municipio (Barra lateral)
    if ciudad_query.strip():
        cq = normalizar_texto(ciudad_query)
        df = df[df['ciudad_norm'].str.contains(cq, na=False)]

    # F. Filtro por Entidad Compradora (Barra lateral)
    if entidad_query.strip():
        eq = normalizar_texto(entidad_query)
        df = df[df['entidad_norm'].str.contains(eq, na=False)]

    # G. Filtro por Sector UNSPSC
    cod_cat = CATEGORIAS_UNSPSC[sector_sel]
    if cod_cat != "TODOS" and 'codigo_principal_de_categoria' in df.columns:
        pattern = cod_cat
        df = df[df['codigo_principal_de_categoria'].astype(str).str.contains(pattern, na=False)]

    # ---------------------------------------------------------
    # FILTROS EN PANTALLA (DESPLEGABLES SOBRE LA TABLA)
    # ---------------------------------------------------------
    st.markdown(f'<div class="badge-info">📊 <b>Muestra examinada del SECOP II:</b> {len(df_raw):,} registros descargados | <b>Coincidencias encontradas:</b> {len(df):,} procesos.</div>', unsafe_allow_html=True)
    
    st.subheader("🔍 Filtros Interactivos sobre la Tabla de Resultados")
    f_col1, f_col2, f_col3 = st.columns(3)
    
    with f_col1:
        ciudades_disp = sorted(df['ciudad_entidad'].dropna().unique())
        ciudad_f = st.multiselect("📍 Filtrar por Ciudad / Municipio:", options=ciudades_disp, default=[])
        
    with f_col2:
        entidades_disp = sorted(df['entidad'].dropna().unique())
        entidad_f = st.multiselect("🏛️ Filtrar por Entidad Compradora:", options=entidades_disp, default=[])
        
    with f_col3:
        modalidades_disp = sorted(df['modalidad_de_contratacion'].dropna().unique())
        modalidad_f = st.multiselect("📜 Filtrar por Modalidad Exacta:", options=modalidades_disp, default=[])

    # Aplicar selecciones en pantalla
    if ciudad_f:
        df = df[df['ciudad_entidad'].isin(ciudad_f)]
    if entidad_f:
        df = df[df['entidad'].isin(entidad_f)]
    if modalidad_f:
        df = df[df['modalidad_de_contratacion'].isin(modalidad_f)]

    # ---------------------------------------------------------
    # DESPLIEGUE DE RESULTADOS Y METRICAS FORMATEADAS
    # ---------------------------------------------------------
    if not df.empty:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Licitaciones Activas", f"{len(df):,}")
        with col2:
            bolsa_total = df['precio_num'].sum()
            st.metric("Bolsa Presupuestada", formato_pesos_cop(bolsa_total))
        with col3:
            dep_top = df['departamento_entidad'].value_counts().index[0] if ('departamento_entidad' in df.columns and not df.empty) else "N/A"
            st.metric("Departamento Líder", f"{dep_top}")
        with col4:
            muni_top = df['ciudad_entidad'].value_counts().index[0] if ('ciudad_entidad' in df.columns and not df.empty) else "N/A"
            st.metric("Municipio Líder", f"{muni_top}")

        st.markdown("---")
        st.subheader("📋 Matriz Operativa de Licitaciones para VLAO INGENIERÍA S.A.S.")

        # Limpiar URL del proceso
        def extraer_url(val):
            if isinstance(val, dict):
                return val.get('url', '')
            val_str = str(val)
            if 'http' in val_str:
                return val_str
            return ''

        data_display = df.copy()
        if 'urlproceso' in data_display.columns:
            data_display['url_clean'] = data_display['urlproceso'].apply(extraer_url)
        else:
            data_display['url_clean'] = ''

        cols_map = {
            'referencia_del_proceso': 'Proceso',
            'entidad': 'Entidad Compradora',
            'departamento_entidad': 'Departamento',
            'ciudad_entidad': 'Ciudad / Municipio',
            'modalidad_de_contratacion': 'Modalidad',
            'nombre_del_procedimiento': 'Objeto del Proceso',
            'precio_formateado': 'Presupuesto ($ COP)',
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
                "Presupuesto ($ COP)": st.column_config.TextColumn("Presupuesto ($ COP)"),
                "Fecha Publicación": st.column_config.TextColumn("Fecha Publicación 📅"),
                "Cierre Ofertas": st.column_config.TextColumn("Cierre Ofertas ⏰")
            },
            use_container_width=True,
            hide_index=True
        )

        csv_data = data_final.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Descargar Reporte Comercial en Excel / CSV",
            data=csv_data,
            file_name=f"Radar_SECOP_v15_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
    else:
        st.warning("⚠️ No se encontraron procesos que coincidan con la combinación exacta de filtros seleccionada.")
        st.info("""
        💡 **Sugerencias de búsqueda:**
        * Si aplicaste un filtro estricto por ciudad o palabra clave, prueba desmarcando los desplegables de selección múltiple en pantalla.
        * Asegúrate de tener seleccionada la opción **'🌐 Todas las Modalidades'** o **'Todos los procesos recientes'** para ampliar la búsqueda.
        """)
else:
    st.error("No fue posible descargar datos del SECOP II. Por favor refresca la aplicación.")
