import streamlit as st
import pandas as pd
import requests
import urllib.parse
import unicodedata
from datetime import datetime, timedelta

# Configuración de página
st.set_page_config(
    page_title="Radar SECOP II v9 - Filtros por Ciudad y Entidad",
    layout="wide",
    page_icon="🎯"
)

st.title("🎯 Radar Quirúrgico SECOP II - Versión 9.0 (Filtros por Ciudad, Municipio y Entidad)")
st.markdown("""
**Buscador Especializado sobre la Base Nacional del SECOP II (Datos Abiertos Colombia).**  
*Ahora con filtros directos por **Ciudad / Municipio**, **Entidad Compradora** y herramientas de filtrado rápido en la tabla.*
""")

# Sidebar - Filtros de Búsqueda
st.sidebar.header("⚙️ Configuración del Radar")

# 1. Buscador libre por palabra clave
palabra_clave = st.sidebar.text_input(
    "🔎 Palabra clave (Objeto o Nombre):",
    "",
    placeholder="Ej: cubierta, ferreteria, mantenimiento, impermeabilizacion, suministro..."
)

# 2. Filtro por Ciudad / Municipio
ciudad_filtro = st.sidebar.text_input(
    "📍 Ciudad / Municipio:",
    "",
    placeholder="Ej: Bogota, Medellin, Cali, Bucaramanga, Neiva, Villavicencio..."
)

# 3. Filtro por Entidad Compradora
entidad_filtro = st.sidebar.text_input(
    "🏛️ Entidad Compradora:",
    "",
    placeholder="Ej: SENA, Alcaldia, Gobernacion, Ejercito, Hospital, ICBF..."
)

# 4. Ventana de Tiempo
periodo = st.sidebar.selectbox(
    "📅 Ventana de Tiempo (Fecha de Publicación):",
    [
        "Todos los procesos recientes (Recomendado)",
        "Últimos 30 Días",
        "Últimos 60 Días",
        "Últimos 90 Días",
        "Año 2026 Completo"
    ]
)

# 5. Modalidades completas del SECOP II / Colombia Compra Eficiente
MODALIDADES_SECOP = {
    "🌐 Todas las Modalidades (Sin Restricción - 100% del SECOP II)": "TODAS",
    "⚡ Mínima Cuantía (Sin RUP - Art. 2 Ley 1150/2007)": "MINIMA",
    "📋 Selección Abreviada (Menor Cuantía / Subasta Inversa)": "ABREVIADA",
    "🏛️ Licitación Pública": "LICITACION",
    "🎓 Concurso de Méritos": "CONCURSO",
    "📑 Contratación Directa": "DIRECTA",
    "🏢 Régimen Especial (Empresas Públicas, E.S.E., Universidades)": "REGIMEN_ESPECIAL",
    "🛒 Acuerdo Marco de Precios / Tienda Virtual CCE": "ACUERDO_MARCO"
}

filtro_rup = st.sidebar.selectbox(
    "📜 Modalidad de Contratación:",
    options=list(MODALIDADES_SECOP.keys())
)

# 6. Categorías UNSPSC
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

sector_sel = st.sidebar.selectbox(
    "🏢 Sector / Categoría UNSPSC:",
    options=list(CATEGORIAS_UNSPSC.keys())
)

# 7. Cantidad de resultados máximos a consultar
limite = st.sidebar.slider("📊 Cantidad máxima de registros a extraer:", 100, 3000, 1500, 100)

# ---------------------------------------------------------
# FUNCIONES AUXILIARES DE NORMALIZACION DE TEXTO
# ---------------------------------------------------------

def normalizar_texto(texto):
    """Elimina acentos/tildes y convierte a minúsculas para comparaciones perfectas."""
    if not texto:
        return ""
    texto_str = str(texto)
    nfkd = unicodedata.normalize('NFD', texto_str)
    sin_tildes = "".join([c for c in nfkd if unicodedata.category(c) != 'Mn'])
    return sin_tildes.lower()

# ---------------------------------------------------------
# FUNCION DE CONSULTA SoQL CON FILTROS DE CIUDAD Y ENTIDAD
# ---------------------------------------------------------

@st.cache_data(ttl=300)
def consultar_secop_v9(periodo_sel, rup_nombre, sector_nombre, kw_texto, ciudad_txt, entidad_txt, max_rows):
    base_url = "https://www.datos.gov.co/resource/p6dx-8zbt.json"
    select_cols = "entidad,departamento_entidad,ciudad_entidad,referencia_del_proceso,codigo_principal_de_categoria,nombre_del_procedimiento,descripci_n_del_procedimiento,modalidad_de_contratacion,precio_base,estado_resumen,fecha_de_publicacion,fecha_de_recepcion_de,urlproceso"
    
    where_clauses = []
    
    # A. Palabra clave
    if kw_texto.strip():
        kw_clean = normalizar_texto(kw_texto)
        where_clauses.append(f"(lower(nombre_del_procedimiento) like '%{kw_clean}%' OR lower(descripci_n_del_procedimiento) like '%{kw_clean}%')")
    
    # B. Ciudad / Municipio
    if ciudad_txt.strip():
        ciu_clean = normalizar_texto(ciudad_txt)
        where_clauses.append(f"(lower(ciudad_entidad) like '%{ciu_clean}%' OR lower(departamento_entidad) like '%{ciu_clean}%')")

    # C. Entidad Compradora
    if entidad_txt.strip():
        ent_clean = normalizar_texto(entidad_txt)
        where_clauses.append(f"(lower(entidad) like '%{ent_clean}%')")

    # D. Fecha
    now = datetime.now()
    if "30 Días" in periodo_sel:
        f_lim = (now - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00.000")
        where_clauses.append(f"fecha_de_publicacion >= '{f_lim}'")
    elif "60 Días" in periodo_sel:
        f_lim = (now - timedelta(days=60)).strftime("%Y-%m-%dT00:00:00.000")
        where_clauses.append(f"fecha_de_publicacion >= '{f_lim}'")
    elif "90 Días" in periodo_sel:
        f_lim = (now - timedelta(days=90)).strftime("%Y-%m-%dT00:00:00.000")
        where_clauses.append(f"fecha_de_publicacion >= '{f_lim}'")
    elif "Año 2026" in periodo_sel:
        where_clauses.append("fecha_de_publicacion >= '2026-01-01T00:00:00.000'")

    # E. Modalidad SoQL
    mod_code = MODALIDADES_SECOP[rup_nombre]
    if mod_code == "MINIMA":
        where_clauses.append("(lower(modalidad_de_contratacion) like '%m%nima%' OR lower(modalidad_de_contratacion) like '%cuant%a%')")
    elif mod_code == "ABREVIADA":
        where_clauses.append("(lower(modalidad_de_contratacion) like '%abreviada%' OR lower(modalidad_de_contratacion) like '%selecci%n%')")
    elif mod_code == "LICITACION":
        where_clauses.append("(lower(modalidad_de_contratacion) like '%licitaci%n%' OR lower(modalidad_de_contratacion) like '%licita%')")
    elif mod_code == "CONCURSO":
        where_clauses.append("(lower(modalidad_de_contratacion) like '%concurso%' OR lower(modalidad_de_contratacion) like '%m%ritos%')")
    elif mod_code == "DIRECTA":
        where_clauses.append("(lower(modalidad_de_contratacion) like '%directa%')")
    elif mod_code == "REGIMEN_ESPECIAL":
        where_clauses.append("(lower(modalidad_de_contratacion) like '%especial%')")
    elif mod_code == "ACUERDO_MARCO":
        where_clauses.append("(lower(modalidad_de_contratacion) like '%marco%' OR lower(modalidad_de_contratacion) like '%tienda%')")

    # F. Categoría UNSPSC
    cod_cat = CATEGORIAS_UNSPSC[sector_nombre]
    if cod_cat != "TODOS":
        where_clauses.append(f"(codigo_principal_de_categoria like '%{cod_cat}%')")

    where_str = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    params = {
        "$select": select_cols,
        "$where": where_str,
        "$order": "fecha_de_publicacion DESC",
        "$limit": str(max_rows)
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
    }
    
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    
    resp = requests.get(url, headers=headers, timeout=25)
    resp.raise_for_status()
    
    data = resp.json()
    df = pd.DataFrame(data)
    
    if not df.empty:
        if 'precio_base' in df.columns:
            df['precio_base'] = pd.to_numeric(df['precio_base'], errors='coerce').fillna(0)
            
        if 'fecha_de_publicacion' in df.columns:
            df['fecha_pub_clean'] = pd.to_datetime(df['fecha_de_publicacion'], errors='coerce').dt.strftime('%Y-%m-%d')
            
        if 'fecha_de_recepcion_de' in df.columns:
            df['fecha_cierre_clean'] = pd.to_datetime(df['fecha_de_recepcion_de'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M')
            
    return df

# Ejecutar consulta
with st.spinner("🚀 Consultando la base nacional del SECOP II en tiempo real..."):
    try:
        df = consultar_secop_v9(periodo, filtro_rup, sector_sel, palabra_clave, ciudad_filtro, entidad_filtro, limite)
    except Exception as e:
        st.error(f"Error técnico al consultar el servidor de Datos Abiertos: {e}")
        df = pd.DataFrame()

# ---------------------------------------------------------
# NORMALIZACION Y FILTRADO SECUNDARIO
# ---------------------------------------------------------

if not df.empty:
    mod_code = MODALIDADES_SECOP[filtro_rup]
    
    if mod_code != "TODAS" and 'modalidad_de_contratacion' in df.columns:
        df['mod_norm'] = df['modalidad_de_contratacion'].apply(normalizar_texto)
        
        if mod_code == "MINIMA":
            df = df[df['mod_norm'].str.contains('minima|cuantia', na=False)]
        elif mod_code == "LICITACION":
            df = df[df['mod_norm'].str.contains('licitacion|licitacion publica', na=False)]
        elif mod_code == "ABREVIADA":
            df = df[df['mod_norm'].str.contains('abreviada|subasta|menor cuantia', na=False)]
        elif mod_code == "CONCURSO":
            df = df[df['mod_norm'].str.contains('concurso|meritos', na=False)]
        elif mod_code == "DIRECTA":
            df = df[df['mod_norm'].str.contains('directa', na=False)]
        elif mod_code == "REGIMEN_ESPECIAL":
            df = df[df['mod_norm'].str.contains('especial|regimen', na=False)]
        elif mod_code == "ACUERDO_MARCO":
            df = df[df['mod_norm'].str.contains('marco|tienda', na=False)]

# ---------------------------------------------------------
# DESPLIEGUE Y FILTROS INTERACTIVOS EN PANTALLA
# ---------------------------------------------------------

if not df.empty:
    st.success(f"✅ Se encontraron **{len(df):,}** licitaciones que coinciden con tus filtros.")
    
    # Tarjetas métricas
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Oportunidades Encontradas", f"{len(df):,}")
    with col2:
        st.metric("Bolsa Total Presupuestada ($)", f"${df['precio_base'].sum():,.0f} COP")
    with col3:
        ciud_top = df['ciudad_entidad'].value_counts().index[0] if ('ciudad_entidad' in df.columns and not df.empty) else "N/A"
        st.metric("Ciudad Líder", f"{ciud_top}")
    with col4:
        ent_top = df['entidad'].value_counts().index[0] if ('entidad' in df.columns and not df.empty) else "N/A"
        st.metric("Entidad Principal", f"{ent_top[:22]}...")

    st.markdown("---")
    
    # FILTROS RÁPIDOS SOBRE EL CUADRO
    st.subheader("🔍 Filtros Rápido sobre la Tabla de Resultados")
    f_col1, f_col2, f_col3 = st.columns(3)
    
    with f_col1:
        ciudades_disp = sorted(df['ciudad_entidad'].dropna().unique()) if 'ciudad_entidad' in df.columns else []
        sel_ciudades = st.multiselect("📍 Filtrar por Ciudad/Municipio:", options=ciudades_disp, default=[])
        
    with f_col2:
        deptos_disp = sorted(df['departamento_entidad'].dropna().unique()) if 'departamento_entidad' in df.columns else []
        sel_deptos = st.multiselect("🗺️ Filtrar por Departamento:", options=deptos_disp, default=[])

    with f_col3:
        entidades_disp = sorted(df['entidad'].dropna().unique()) if 'entidad' in df.columns else []
        sel_entidades = st.multiselect("🏛️ Filtrar por Entidad Compradora:", options=entidades_disp, default=[])

    # Aplicar filtros en pantalla
    df_filtrado = df.copy()
    if sel_ciudades:
        df_filtrado = df_filtrado[df_filtrado['ciudad_entidad'].isin(sel_ciudades)]
    if sel_deptos:
        df_filtrado = df_filtrado[df_filtrado['departamento_entidad'].isin(sel_deptos)]
    if sel_entidades:
        df_filtrado = df_filtrado[df_filtrado['entidad'].isin(sel_entidades)]

    st.markdown("---")
    st.subheader("📋 Listado Detallado de Procesos del SECOP II")

    def extraer_url(val):
        if isinstance(val, dict):
            return val.get('url', '')
        val_str = str(val)
        if 'http' in val_str:
            return val_str
        return ''

    data_display = df_filtrado.copy()
    if 'urlproceso' in data_display.columns:
        data_display['url_clean'] = data_display['urlproceso'].apply(extraer_url)
    else:
        data_display['url_clean'] = ''

    cols_map = {
        'referencia_del_proceso': 'Proceso',
        'entidad': 'Entidad Compradora',
        'ciudad_entidad': 'Ciudad / Municipio',
        'departamento_entidad': 'Departamento',
        'modalidad_de_contratacion': 'Modalidad',
        'estado_resumen': 'Estado',
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
        label="📥 Descargar Reporte Filtrado en CSV / Excel",
        data=csv_data,
        file_name=f"Radar_SECOP_v9_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )
else:
    st.warning("⚠️ No se encontraron procesos vigentes con la combinación de filtros seleccionada.")
    st.info("""
    💡 **Sugerencia:**
    * Si escribiste una ciudad específica en la barra lateral (ej: *Bogota*), intenta dejarla en blanco y usar los **desplegables sobre la tabla** para filtrar ciudades interactivamente.
    * Amplía la ventana de tiempo a **'Todos los procesos recientes'**.
    """)
