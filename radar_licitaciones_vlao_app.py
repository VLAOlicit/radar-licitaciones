import streamlit as st
import pandas as pd
import requests
import io
import urllib.parse
from datetime import datetime, timedelta

# Configuración de página
st.set_page_config(
    page_title="Radar SECOP II - Oportunidades Vigentes 2026",
    layout="wide",
    page_icon="🎯"
)

st.title("🎯 Radar Quirúrgico SECOP II - Procesos Vigentes 2026")
st.markdown("""
**Buscador enfocado en Oportunidades Reales para Presentar Propuesta.**
Filtra procesos vigentes del año 2026, sin ruido de licitaciones pasadas, con opción de identificar procesos **Sin RUP** (*Mínima Cuantía*) y abiertos a todos los sectores.
""")

# Sidebar - Filtros de Búsqueda
st.sidebar.header("⚙️ Configuración del Radar")

# 1. Filtro de Periodo / Año 2026
periodo = st.sidebar.selectbox(
    "📅 Ventana de Tiempo (Fecha de Publicación):",
    [
        "2do Semestre 2026 (Julio 2026 - Presente)",
        "Año 2026 Completo (Enero 2026 - Presente)",
        "Últimos 30 Días",
        "Últimos 60 Días",
        "Todos los procesos recientes"
    ]
)

# 2. Filtro de RUP / Modalidad
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

# 3. Selector de Sector
sector = st.sidebar.selectbox(
    "🏢 Sector de Negocio:",
    [
        "🌐 Todos los Sectores (Sin Restricción de Categoría)",
        "🛠️ Ferretería, Herramientas, Eléctricos y Pinturas",
        "💻 Tecnología, Software y Comunicaciones",
        "🏥 Salud, Medicamentos y Equipos Médicos",
        "🍎 Alimentos, Catering, Aseo y Cafetería",
        "🚗 Vehículos, Maquinaria, Repuestos y Mantenimiento",
        "🛡️ Vigilancia, Seguridad Privada y Custodia",
        "🏗️ Obra Civil e Infraestructura"
    ]
)

# 4. Buscador Libre
palabra_clave = st.sidebar.text_input("🔎 Palabra clave en el Objeto / Nombre:", "", placeholder="Ej: suministro, herramientas, mantenimiento...")

# 5. Límite de Resultados a extraer de la API
limite = st.sidebar.slider("📊 Límite de registros a descargar del SECOP II:", 1000, 5000, 3000, 500)

# ---------------------------------------------------------
# FUNCION DE DESCARGA CON USER-AGENT Y URLENCODE
# ---------------------------------------------------------

@st.cache_data(ttl=300)
def descargar_datos_secop(limite_registros):
    base_url = "https://www.datos.gov.co/resource/p6dx-8zbt.csv"
    select_cols = "entidad,departamento_entidad,ciudad_entidad,referencia_del_proceso,codigo_principal_de_categoria,nombre_del_procedimiento,descripci_n_del_procedimiento,modalidad_de_contratacion,precio_base,estado_resumen,fecha_de_publicacion,fecha_de_recepcion_de,urlproceso"
    
    # Consulta SODA limpia y robusta (se filtran los vigentes)
    params = {
        '$select': select_cols,
        '$limit': str(limite_registros),
        '$where': "estado_resumen in('Presentación de ofertas','Publicado')",
        '$order': "fecha_de_publicacion DESC"
    }
    
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()
    
    df = pd.read_csv(io.StringIO(response.text))
    if 'precio_base' in df.columns:
        df['precio_base'] = pd.to_numeric(df['precio_base'], errors='coerce').fillna(0)
    if 'fecha_de_publicacion' in df.columns:
        df['fecha_de_publicacion_dt'] = pd.to_datetime(df['fecha_de_publicacion'], errors='coerce')
    return df

with st.spinner("🚀 Conectando de forma segura con la API del SECOP II..."):
    try:
        raw_df = descargar_datos_secop(limite)
        st.success(f"¡Conexión exitosa! Se descargaron {len(raw_df):,} procesos vigentes del SECOP II.")
    except Exception as e:
        st.error("No se pudo conectar con el servidor de Datos Abiertos. Por favor intenta nuevamente en unos segundos.")
        st.caption(f"Detalle técnico: {e}")
        raw_df = pd.DataFrame()

# ---------------------------------------------------------
# FILTRADO INTELIGENTE EN MEMORIA (PANDAS)
# ---------------------------------------------------------

data = raw_df.copy()

if not data.empty:
    # A. Filtro por Fecha / Periodo 2026
    if "2do Semestre 2026" in periodo and 'fecha_de_publicacion_dt' in data.columns:
        data = data[data['fecha_de_publicacion_dt'] >= pd.Timestamp('2026-07-01')]
    elif "Año 2026 Completo" in periodo and 'fecha_de_publicacion_dt' in data.columns:
        data = data[data['fecha_de_publicacion_dt'] >= pd.Timestamp('2026-01-01')]
    elif "Últimos 30 Días" in periodo and 'fecha_de_publicacion_dt' in data.columns:
        hace_30 = pd.Timestamp.now() - pd.Timedelta(days=30)
        data = data[data['fecha_de_publicacion_dt'] >= hace_30]
    elif "Últimos 60 Días" in periodo and 'fecha_de_publicacion_dt' in data.columns:
        hace_60 = pd.Timestamp.now() - pd.Timedelta(days=60)
        data = data[data['fecha_de_publicacion_dt'] >= hace_60]

    # B. Filtro por Modalidad / RUP
    if "Solo Sin RUP" in filtro_rup and 'modalidad_de_contratacion' in data.columns:
        data = data[data['modalidad_de_contratacion'].astype(str).str.lower().str.contains('mínima cuantía|minima cuantia', na=False)]
    elif "Selección Abreviada" in filtro_rup and 'modalidad_de_contratacion' in data.columns:
        data = data[data['modalidad_de_contratacion'].astype(str).str.lower().str.contains('selección abreviada|seleccion abreviada', na=False)]
    elif "Licitación Pública" in filtro_rup and 'modalidad_de_contratacion' in data.columns:
        data = data[data['modalidad_de_contratacion'].astype(str).str.lower().str.contains('licitación pública|licitacion publica', na=False)]
    elif "Concurso de Méritos" in filtro_rup and 'modalidad_de_contratacion' in data.columns:
        data = data[data['modalidad_de_contratacion'].astype(str).str.lower().str.contains('concurso de méritos|concurso de meritos', na=False)]

    # C. Filtro por Sector UNSPSC
    prefixes = []
    if "Ferretería" in sector:
        prefixes = ['3116', '2711', '3010', '3912', '3121', '4014']
    elif "Tecnología" in sector:
        prefixes = ['4321', '4323', '8111']
    elif "Salud" in sector:
        prefixes = ['4200', '5100']
    elif "Alimentos" in sector:
        prefixes = ['5000', '4713']
    elif "Vehículos" in sector:
        prefixes = ['2510', '7818']
    elif "Vigilancia" in sector:
        prefixes = ['9212', '7611']
    elif "Obra Civil" in sector:
        prefixes = ['7214', '7212']

    if prefixes and 'codigo_principal_de_categoria' in data.columns:
        data['cod_str'] = data['codigo_principal_de_categoria'].astype(str)
        pattern = '^(' + '|'.join(prefixes) + ')'
        data = data[data['cod_str'].str.contains(pattern, na=False, regex=True)]

    # D. Filtro por Palabra Clave
    if palabra_clave:
        pk = palabra_clave.lower().strip()
        cond_nom = data['nombre_del_procedimiento'].astype(str).str.lower().str.contains(pk, na=False)
        cond_desc = data['descripci_n_del_procedimiento'].astype(str).str.lower().str.contains(pk, na=False)
        data = data[cond_nom | cond_desc]

    # ---------------------------------------------------------
    # DESPLIEGUE DE RESULTADOS
    # ---------------------------------------------------------
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Oportunidades Encontradas", f"{len(data):,}")
    with col2:
        st.metric("Bolsa Total Disponible ($)", f"${data['precio_base'].sum():,.0f} COP")
    with col3:
        dep_top = data['departamento_entidad'].value_counts().index[0] if ('departamento_entidad' in data.columns and not data.empty) else "N/A"
        st.metric("Dep. con Más Procesos", f"{dep_top}")

    st.markdown("---")
    st.subheader("📋 Lista de Procesos Vigentes para Presentar Oferta")
    
    cols_to_drop = [c for c in ['fecha_de_publicacion_dt', 'cod_str'] if c in data.columns]
    data_display = data.drop(columns=cols_to_drop)

    st.dataframe(
        data_display,
        column_config={
            "urlproceso": st.column_config.LinkColumn("Enlace SECOP II", display_text="Ver Pliegos 🔗"),
            "precio_base": st.column_config.NumberColumn("Presupuesto (COP)", format="$%'.0f"),
            "fecha_de_publicacion": "Fecha Publicación",
            "fecha_de_recepcion_de": "Cierre Ofertas",
            "nombre_del_procedimiento": "Objeto del Proceso",
            "entidad": "Entidad Compradora",
            "modalidad_de_contratacion": "Modalidad"
        },
        use_container_width=True,
        hide_index=True
    )

    csv_data = data_display.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar Reporte Completo en CSV / Excel",
        data=csv_data,
        file_name=f"radar_secop_2026_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )
else:
    if not raw_df.empty:
        st.warning("No se encontraron procesos vigentes que coincidan con los filtros seleccionados. Prueba cambiando el sector o la palabra clave.")
