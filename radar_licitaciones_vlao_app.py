import streamlit as st
import pandas as pd
import requests
import urllib.parse
from datetime import datetime, timedelta

# Configuración de página
st.set_page_config(
    page_title="Radar SECOP II v6 - Búsqueda Quirúrgica por Modalidad",
    layout="wide",
    page_icon="🎯"
)

st.title("🎯 Radar Quirúrgico SECOP II - Versión 6.0 (Filtros por Modalidad y RUP)")
st.markdown("""
**Buscador Especializado de Licitaciones Públicas en Colombia (Datos Abiertos / SECOP II).**  
*Optimizado para identificar procesos **Sin RUP** (*Mínima Cuantía*), **Selección Abreviada**, **Licitación Pública** y **Concurso de Méritos**.*
""")

# Sidebar - Filtros de Búsqueda
st.sidebar.header("⚙️ Configuración del Radar")

# 1. Buscador libre por palabra clave
palabra_clave = st.sidebar.text_input(
    "🔎 Palabra clave (Objeto o Nombre):",
    "",
    placeholder="Ej: cubierta, ferreteria, mantenimiento, impermeabilizacion..."
)

# 2. Ventana de Tiempo
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

# 3. Exigencia de RUP / Modalidad de Contratación
filtro_rup = st.sidebar.selectbox(
    "📜 Exigencia de RUP / Modalidad:",
    [
        "Todas las Modalidades (Con y Sin RUP)",
        "⚡ Solo Sin RUP (Mínima Cuantía - Art. 2 Ley 1150/2007)",
        "Selección Abreviada de Menor Cuantía",
        "Licitación Pública",
        "Concurso de Méritos"
    ]
)

# 4. Categorías UNSPSC
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

# 5. Cantidad de resultados máximos a extraer
limite = st.sidebar.slider("📊 Cantidad máxima de registros a consultar:", 100, 3000, 1000, 100)

# ---------------------------------------------------------
# FUNCION DE CONSULTA INTELIGENTE Y ROBUSTA A LA API DE DATOS ABIERTOS
# ---------------------------------------------------------

@st.cache_data(ttl=300)
def consultar_secop_v6(periodo_sel, rup_sel, sector_nombre, kw_texto, max_rows):
    base_url = "https://www.datos.gov.co/resource/p6dx-8zbt.json"
    select_cols = "entidad,departamento_entidad,ciudad_entidad,referencia_del_proceso,codigo_principal_de_categoria,nombre_del_procedimiento,descripci_n_del_procedimiento,modalidad_de_contratacion,precio_base,estado_resumen,fecha_de_publicacion,fecha_de_recepcion_de,urlproceso"
    
    where_clauses = []
    
    # A. Filtro por Palabra Clave (Búsqueda amplia en nombre o descripción)
    if kw_texto.strip():
        kw_clean = kw_texto.lower().strip()
        where_clauses.append(f"(lower(nombre_del_procedimiento) like '%{kw_clean}%' OR lower(descripci_n_del_procedimiento) like '%{kw_clean}%')")
    
    # B. Filtro por Ventana de Tiempo
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

    # C. Filtro por Modalidad de Contratación (Lógica SoQL sin problemas de tildes)
    if "Solo Sin RUP" in rup_sel:
        where_clauses.append("(lower(modalidad_de_contratacion) like '%nima%' OR lower(modalidad_de_contratacion) like '%cuant%a%')")
    elif "Selección Abreviada" in rup_sel:
        where_clauses.append("(lower(modalidad_de_contratacion) like '%breviad%' OR lower(modalidad_de_contratacion) like '%subasta%')")
    elif "Licitación Pública" in rup_sel:
        where_clauses.append("(lower(modalidad_de_contratacion) like '%licita%')")
    elif "Concurso de Méritos" in rup_sel:
        where_clauses.append("(lower(modalidad_de_contratacion) like '%concurso%' OR lower(modalidad_de_contratacion) like '%rito%')")

    # D. Filtro por Categoría UNSPSC
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

        # Refinamiento y verificación estricta en Pandas para la Modalidad
        if "Solo Sin RUP" in rup_sel and 'modalidad_de_contratacion' in df.columns:
            df = df[df['modalidad_de_contratacion'].astype(str).str.contains('mínima|minima|cuantía|cuantia|nima', case=False, na=False)]
        elif "Selección Abreviada" in rup_sel and 'modalidad_de_contratacion' in df.columns:
            df = df[df['modalidad_de_contratacion'].astype(str).str.contains('abreviada|subasta|menor', case=False, na=False)]
        elif "Licitación Pública" in rup_sel and 'modalidad_de_contratacion' in df.columns:
            df = df[df['modalidad_de_contratacion'].astype(str).str.contains('licitación|licitacion', case=False, na=False)]
        elif "Concurso de Méritos" in rup_sel and 'modalidad_de_contratacion' in df.columns:
            df = df[df['modalidad_de_contratacion'].astype(str).str.contains('mérito|merito|concurso', case=False, na=False)]

    return df

# Ejecutar consulta
with st.spinner("🚀 Rastreando procesos en la base oficial del SECOP II..."):
    try:
        df = consultar_secop_v6(periodo, filtro_rup, sector_sel, palabra_clave, limite)
    except Exception as e:
        st.error(f"Error técnico al consultar el servidor de Datos Abiertos: {e}")
        df = pd.DataFrame()

# ---------------------------------------------------------
# DESPLIEGUE DE RESULTADOS E INTERFAZ
# ---------------------------------------------------------

if not df.empty:
    st.success(f"✅ Se encontraron **{len(df):,}** licitaciones activas alineadas con el filtro: **'{filtro_rup}'**.")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Oportunidades Encontradas", f"{len(df):,}")
    with col2:
        st.metric("Bolsa Presupuestada ($)", f"${df['precio_base'].sum():,.0f} COP")
    with col3:
        dep_top = df['departamento_entidad'].value_counts().index[0] if ('departamento_entidad' in df.columns and not df.empty) else "N/A"
        st.metric("Dep. Principal", f"{dep_top}")
    with col4:
        mod_top = df['modalidad_de_contratacion'].value_counts().index[0] if ('modalidad_de_contratacion' in df.columns and not df.empty) else "N/A"
        st.metric("Modalidad Dominante", f"{mod_top}")

    st.markdown("---")
    st.subheader(f"📋 Licitaciones Filtradas por Modalidad: {filtro_rup}")

    # Extraer URL limpia para el enlace SECOP II
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

    # Renombrar columnas para la tabla interactiva
    cols_map = {
        'referencia_del_proceso': 'Proceso / Ref.',
        'entidad': 'Entidad Compradora',
        'departamento_entidad': 'Departamento',
        'modalidad_de_contratacion': 'Modalidad de Contratación',
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
        file_name=f"Radar_SECOP_v6_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )
else:
    st.warning(f"⚠️ No se encontraron procesos para la modalidad **'{filtro_rup}'** con los filtros actuales.")
    st.info("""
    💡 **Sugerencia de ajuste:**
    * **Cambia a 'Todas las Modalidades (Con y Sin RUP)':** Si estás buscando una palabra clave específica como **'cubierta'** o **'herramientas'**, es posible que la entidad la haya publicado mediante Contratación Directa o Selección Abreviada.
    * **Ventana de Tiempo:** Selecciona **'Todos los procesos recientes (Recomendado)'**.
    """)
