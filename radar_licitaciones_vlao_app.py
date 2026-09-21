import streamlit as st
import pandas as pd
import requests
import urllib.parse
from datetime import datetime, timedelta

# Configuración de página
st.set_page_config(
    page_title="Radar SECOP II v4 - Búsqueda Directa en Base Nacional",
    layout="wide",
    page_icon="🎯"
)

st.title("🎯 Radar Quirúrgico SECOP II - Versión 4.0")
st.markdown("""
**Buscador Directo en la Base Nacional de Datos Abiertos del SECOP II.**  
*Consulta en tiempo real sobre la totalidad de licitaciones públicas en Colombia, filtrando directamente en el servidor estatal.*
""")

# Sidebar - Filtros de Búsqueda
st.sidebar.header("⚙️ Filtros Quirúrgicos de Búsqueda")

# 1. Ventana de Tiempo
periodo = st.sidebar.selectbox(
    "📅 Ventana de Tiempo (Fecha de Publicación):",
    [
        "Últimos 30 Días",
        "Últimos 60 Días",
        "Últimos 90 Días",
        "Año 2026 Completo",
        "Todos los procesos vigentes"
    ]
)

# 2. Exigencia de RUP / Modalidad
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

# 3. Categorías UNSPSC
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

# 4. Buscador libre
palabra_clave = st.sidebar.text_input(
    "🔎 Palabra clave en el Objeto o Nombre:",
    "",
    placeholder="Ej: cubierta, ferreteria, mantenimiento, impermeabilizacion..."
)

# 5. Cantidad de resultados máximos
limite = st.sidebar.slider("📊 Cantidad máxima de registros a extraer:", 100, 2000, 1000, 100)

# ---------------------------------------------------------
# CONSTRUCCIÓN DE LA CONSULTA SoQL PARA LA API DE DATOS ABIERTOS
# ---------------------------------------------------------

@st.cache_data(ttl=300)
def consultar_secop_v4(periodo_sel, rup_sel, sector_nombre, kw_texto, max_rows):
    base_url = "https://www.datos.gov.co/resource/p6dx-8zbt.json"
    select_cols = "entidad,departamento_entidad,ciudad_entidad,referencia_del_proceso,codigo_principal_de_categoria,nombre_del_procedimiento,descripci_n_del_procedimiento,modalidad_de_contratacion,precio_base,estado_resumen,fecha_de_publicacion,fecha_de_recepcion_de,urlproceso"
    
    where_clauses = ["(lower(estado_resumen) like '%oferta%' OR lower(estado_resumen) like '%publicado%')"]
    
    # A. Filtro por Fecha en la API
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

    # B. Filtro por Modalidad / RUP en la API
    if "Solo Sin RUP" in rup_sel:
        where_clauses.append("(lower(modalidad_de_contratacion) like '%m%nima%cuant%a%')")
    elif "Selección Abreviada" in rup_sel:
        where_clauses.append("(lower(modalidad_de_contratacion) like '%selecci%n%abreviada%')")
    elif "Licitación Pública" in rup_sel:
        where_clauses.append("(lower(modalidad_de_contratacion) like '%licitaci%n%p%blica%')")
    elif "Concurso de Méritos" in rup_sel:
        where_clauses.append("(lower(modalidad_de_contratacion) like '%concurso%m%ritos%')")

    # C. Filtro por Categoría UNSPSC en la API
    cod_cat = CATEGORIAS_UNSPSC[sector_nombre]
    if cod_cat != "TODOS":
        where_clauses.append(f"(codigo_principal_de_categoria like '%{cod_cat}%')")

    # D. Filtro por Palabra Clave en la API
    if kw_texto.strip():
        kw_clean = kw_texto.lower().strip()
        where_clauses.append(f"(lower(nombre_del_procedimiento) like '%{kw_clean}%' OR lower(descripci_n_del_procedimiento) like '%{kw_clean}%')")

    where_str = " AND ".join(where_clauses)
    
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
with st.spinner("🚀 Consultando la base de datos nacional del SECOP II en tiempo real..."):
    try:
        df = consultar_secop_v4(periodo, filtro_rup, sector_sel, palabra_clave, limite)
    except Exception as e:
        st.error(f"Error técnico al consultar el servidor de Datos Abiertos: {e}")
        df = pd.DataFrame()

# ---------------------------------------------------------
# DESPLIEGUE DE RESULTADOS
# ---------------------------------------------------------

if not df.empty:
    st.success(f"✅ Se encontraron **{len(df):,}** licitaciones vigentes en la base nacional que coinciden exactamente con tus criterios.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Procesos Encontrados", f"{len(df):,}")
    with col2:
        st.metric("Bolsa Total Disponible ($)", f"${df['precio_base'].sum():,.0f} COP")
    with col3:
        dep_top = df['departamento_entidad'].value_counts().index[0] if ('departamento_entidad' in df.columns and not df.empty) else "N/A"
        st.metric("Dep. con Más Procesos", f"{dep_top}")

    st.markdown("---")
    st.subheader("📋 Licitaciones Vigentes para Presentar Oferta")

    # Extraer URL limpia para el botón SECOP II
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

    # Renombrar columnas para visualización clara
    cols_map = {
        'referencia_del_proceso': 'Proceso',
        'entidad': 'Entidad Compradora',
        'departamento_entidad': 'Departamento',
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
        label="📥 Descargar Reporte Completo en CSV / Excel",
        data=csv_data,
        file_name=f"Radar_SECOP_v4_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )
else:
    st.warning("⚠️ No se encontraron convocatorias abiertas en la base nacional que coincidan con todos los filtros combinados.")
    st.info("""
    💡 **Sugerencias de búsqueda:**
    * Si buscaste una palabra clave específica como **'cubierta'**, prueba ampliando a **'mantenimiento'**, **'impermeabilizacion'**, **'obra'** o **'cubiertas'**.
    * Cambia la ventana de tiempo a **'Últimos 60 Días'** o **'Año 2026 Completo'**.
    * Asegúrate de tener seleccionado **'Todas las Modalidades'** o **'Todos los Sectores'** para ampliar el universo de búsqueda.
    """)
