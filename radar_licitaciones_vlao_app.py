import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime

# Configuración de página
st.set_page_config(
    page_title="Radar de Licitaciones SECOP II - VLAO INGENIERÍA S.A.S.",
    page_icon="🎯",
    layout="wide"
)

st.title("🎯 Radar Quirúrgico de Licitaciones SECOP II")
st.markdown("""
Plataforma en tiempo real para rastrear oportunidades de contratación pública en Colombia (*Datos Abiertos / SECOP II*).
Encuentra procesos de **Mínima Cuantía (Sin RUP)**, **Selección Abreviada**, **Licitaciones** y más en todos los sectores.
""")

# Sidebar - Filtros de Búsqueda
st.sidebar.header("🔍 Filtros de Búsqueda")

# 1. Cantidad a consultar
limite = st.sidebar.slider("📊 Registros a consultar del SECOP II:", min_value=1000, max_value=5000, value=3000, step=500)

# 2. Periodo / Año
periodo = st.sidebar.selectbox(
    "📅 Periodo de Publicación:",
    [
        "Todos los registros recientes (Recomendado)",
        "Año 2026",
        "Año 2025",
        "Últimos 30 Días",
        "Últimos 90 Días"
    ]
)

# 3. Exigencia de RUP / Modalidad
filtro_rup = st.sidebar.selectbox(
    "📜 Modalidad / Exigencia RUP:",
    [
        "Todas las Modalidades (Con y Sin RUP)",
        "⚡ Solo Sin RUP (Mínima Cuantía - Art. 2 Ley 1150/2007)",
        "Selección Abreviada de Menor Cuantía",
        "Licitación Pública",
        "Concurso de Méritos",
        "Contratación Directa"
    ]
)

# 4. Sector
sector = st.sidebar.selectbox(
    "🏢 Sector Económico:",
    [
        "🌐 Todos los Sectores",
        "🛠️ Ferretería, Herramientas, Eléctricos y Pinturas",
        "💻 Tecnología, Software y Comunicaciones",
        "🏥 Salud, Medicamentos y Equipos Médicos",
        "🍎 Alimentos, Catering, Aseo y Cafetería",
        "🚗 Vehículos, Maquinaria y Repuestos",
        "🛡️ Vigilancia y Seguridad",
        "🏗️ Obra Civil e Infraestructura"
    ]
)

# 5. Buscador Libre
palabra_clave = st.sidebar.text_input("🔎 Palabra clave en el objeto/nombre:", "", placeholder="Ej. ferretería, tubería, insumos...")

# ---------------------------------------------------------
# DESCARGA DE DATOS DESDE LA API SODA (JSON)
# ---------------------------------------------------------
@st.cache_data(ttl=300)
def descargar_datos_secop_json(max_records):
    base_url = "https://www.datos.gov.co/resource/p6dx-8zbt.json"
    
    select_fields = (
        "entidad,departamento_entidad,ciudad_entidad,referencia_del_proceso,"
        "codigo_principal_de_categoria,nombre_del_procedimiento,descripci_n_del_procedimiento,"
        "modalidad_de_contratacion,tipo_de_contrato,precio_base,estado_resumen,"
        "fecha_de_publicacion,fecha_de_recepcion_de,urlproceso"
    )
    
    params = {
        "$select": select_fields,
        "$limit": str(max_records),
        "$order": "fecha_de_publicacion DESC"
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
    }
    
    response = requests.get(base_url, params=params, headers=headers, timeout=25)
    response.raise_for_status()
    data_json = response.json()
    
    records = []
    for item in data_json:
        url_obj = item.get('urlproceso', '')
        if isinstance(url_obj, dict):
            url_str = url_obj.get('url', '')
        else:
            url_str = str(url_obj or '')
            
        precio = float(item.get('precio_base', 0) or 0)
        
        records.append({
            'entidad': item.get('entidad', 'N/A'),
            'departamento_entidad': item.get('departamento_entidad', 'N/A'),
            'ciudad_entidad': item.get('ciudad_entidad', 'N/A'),
            'referencia_del_proceso': item.get('referencia_del_proceso', 'N/A'),
            'codigo_principal_de_categoria': item.get('codigo_principal_de_categoria', 'N/A'),
            'nombre_del_procedimiento': item.get('nombre_del_procedimiento', ''),
            'descripci_n_del_procedimiento': item.get('descripci_n_del_procedimiento', ''),
            'modalidad_de_contratacion': item.get('modalidad_de_contratacion', 'N/A'),
            'precio_base': precio,
            'estado_resumen': item.get('estado_resumen', 'N/A'),
            'fecha_de_publicacion': str(item.get('fecha_de_publicacion', ''))[:10],
            'fecha_de_recepcion_de': str(item.get('fecha_de_recepcion_de', ''))[:10],
            'urlproceso': url_str
        })
        
    df = pd.DataFrame(records)
    if 'fecha_de_publicacion' in df.columns:
        df['fecha_dt'] = pd.to_datetime(df['fecha_de_publicacion'], errors='coerce')
    return df

with st.spinner("🚀 Conectando en vivo con el servidor del SECOP II (datos.gov.co)..."):
    try:
        raw_df = descargar_datos_secop_json(limite)
        st.success(f"¡Conexión exitosa! Se obtuvieron **{len(raw_df):,}** procesos recientes directamente de la base oficial del SECOP II.")
    except Exception as e:
        st.error(f"Error de conexión con la API de Datos Abiertos: {e}")
        raw_df = pd.DataFrame()

# ---------------------------------------------------------
# FILTRADO DINÁMICO EN MEMORIA (PANDAS)
# ---------------------------------------------------------
df = raw_df.copy()

if not df.empty:
    # A. Filtro por Periodo
    if "Año 2026" in periodo and 'fecha_dt' in df.columns:
        df = df[df['fecha_dt'].dt.year == 2026]
    elif "Año 2025" in periodo and 'fecha_dt' in df.columns:
        df = df[df['fecha_dt'].dt.year == 2025]
    elif "Últimos 30 Días" in periodo and 'fecha_dt' in df.columns:
        hace_30 = pd.Timestamp.now() - pd.Timedelta(days=30)
        df = df[df['fecha_dt'] >= hace_30]
    elif "Últimos 90 Días" in periodo and 'fecha_dt' in df.columns:
        hace_90 = pd.Timestamp.now() - pd.Timedelta(days=90)
        df = df[df['fecha_dt'] >= hace_90]

    # B. Filtro por Modalidad / RUP
    if "Solo Sin RUP" in filtro_rup:
        df = df[df['modalidad_de_contratacion'].str.lower().str.contains('mínima cuantía|minima cuantia', na=False)]
    elif "Selección Abreviada" in filtro_rup:
        df = df[df['modalidad_de_contratacion'].str.lower().str.contains('selección abreviada|seleccion abreviada', na=False)]
    elif "Licitación Pública" in filtro_rup:
        df = df[df['modalidad_de_contratacion'].str.lower().str.contains('licitación pública|licitacion publica', na=False)]
    elif "Concurso de Méritos" in filtro_rup:
        df = df[df['modalidad_de_contratacion'].str.lower().str.contains('concurso de méritos|concurso de meritos', na=False)]
    elif "Contratación Directa" in filtro_rup:
        df = df[df['modalidad_de_contratacion'].str.lower().str.contains('directa', na=False)]

    # C. Filtro por Sector UNSPSC
    prefixes = []
    if "Ferretería" in sector:
        prefixes = ['3116', '2711', '3010', '3019', '3912', '3121', '4014', '3911', '7210']
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

    if prefixes and 'codigo_principal_de_categoria' in df.columns:
        pattern = '^(' + '|'.join(prefixes) + ')'
        df = df[df['codigo_principal_de_categoria'].astype(str).str.contains(pattern, na=False, regex=True)]

    # D. Palabra clave
    if palabra_clave.strip():
        pk = palabra_clave.lower().strip()
        cond_nom = df['nombre_del_procedimiento'].str.lower().str.contains(pk, na=False)
        cond_desc = df['descripci_n_del_procedimiento'].str.lower().str.contains(pk, na=False)
        df = df[cond_nom | cond_desc]

    # ---------------------------------------------------------
    # MOSTRAR RESULTADOS Y MÉTRICAS
    # ---------------------------------------------------------
    if not df.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Oportunidades Coincidentes", f"{len(df):,}")
        with col2:
            st.metric("Bolsa Total Disponible ($)", f"${df['precio_base'].sum():,.0f} COP")
        with col3:
            top_dep = df['departamento_entidad'].value_counts().index[0] if not df.empty else "N/A"
            st.metric("Departamento Principal", f"{top_dep}")

        st.markdown("---")
        st.subheader("📋 Licitaciones y Oportunidades Encontradas")

        display_df = df.drop(columns=['fecha_dt'], errors='ignore')

        st.dataframe(
            display_df,
            column_config={
                "urlproceso": st.column_config.LinkColumn("Enlace SECOP II", display_text="Ver Pliegos 🔗"),
                "precio_base": st.column_config.NumberColumn("Presupuesto (COP)", format="$%'.0f"),
                "fecha_de_publicacion": "Fecha Publicación",
                "fecha_de_recepcion_de": "Cierre Ofertas",
                "nombre_del_procedimiento": "Objeto del Proceso",
                "entidad": "Entidad Compradora",
                "modalidad_de_contratacion": "Modalidad",
                "departamento_entidad": "Departamento",
                "referencia_del_proceso": "Proceso"
            },
            use_container_width=True,
            hide_index=True
        )

        csv_bytes = display_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Descargar Reporte en CSV / Excel",
            data=csv_bytes,
            file_name=f"radar_secop_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.warning(f"⚠️ De los {len(raw_df):,} procesos descargados del SECOP II, ninguno coincidió exactamente con los filtros seleccionados.")
        st.info("💡 **Sugerencia:** Selecciona *'Todos los registros recientes'* en el periodo o cambia a *'Todos los Sectores'* en el menú lateral.")
