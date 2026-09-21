import streamlit as st
import pandas as pd
import requests
import io
import urllib.parse
import datetime

# Configuración de la página
st.set_page_config(
    page_title="Radar de Licitaciones SECOP II - VLAO INGENIERÍA S.A.S.",
    page_icon="🏗️",
    layout="wide"
)

# Estilos CSS
st.markdown("""
<style>
    .main-title { font-size: 2.2rem; color: #1E3A8A; font-weight: bold; margin-bottom: 0px; }
    .sub-title { font-size: 1.1rem; color: #4B5563; margin-bottom: 20px; }
    .badge-info { background-color: #EFF6FF; color: #1E40AF; padding: 12px; border-radius: 8px; font-weight: 500; margin-bottom: 15px; border-left: 5px solid #3B82F6; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🎯 Radar Quirúrgico de Licitaciones SECOP II</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">VLAO INGENIERÍA S.A.S. | Módulo Operativo de Búsqueda y Selección de Procesos</div>', unsafe_allow_html=True)

# Categorías UNSPSC
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

# Sidebar
st.sidebar.header("⚙️ Filtros del Radar")

# 1. Ventana de Tiempo
periodo = st.sidebar.selectbox(
    "📅 Ventana de Tiempo (Fecha de Publicación):",
    [
        "Todos los procesos recientes (Sin restricción)",
        "Últimos 30 Días",
        "Últimos 60 Días",
        "Últimos 90 Días",
        "Año 2026 Completo"
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

# 3. Sector
sector_sel = st.sidebar.selectbox(
    "🏢 Sector / Categoría UNSPSC:",
    options=list(CATEGORIAS_UNSPSC.keys())
)

# 4. Buscador libre
palabra_clave = st.sidebar.text_input("🔎 Palabra clave en el Objeto:", "", placeholder="Ej: suministro, herramientas, mantenimiento...")

# 5. Cantidad de registros a descargar
limite = st.sidebar.slider("📊 Cantidad de registros a descargar del SECOP II:", 1000, 5000, 3000, 500)

@st.cache_data(ttl=300)
def cargar_datos_secop_json(max_rows):
    base_url = "https://www.datos.gov.co/resource/p6dx-8zbt.json"
    select_cols = "entidad,departamento_entidad,ciudad_entidad,referencia_del_proceso,codigo_principal_de_categoria,nombre_del_procedimiento,descripci_n_del_procedimiento,modalidad_de_contratacion,precio_base,estado_resumen,fecha_de_publicacion,fecha_de_recepcion_de,urlproceso"
    
    params = {
        "$select": select_cols,
        "$limit": str(max_rows),
        "$order": "fecha_de_publicacion DESC"
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
    }
    
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    
    data = resp.json()
    df = pd.DataFrame(data)
    
    if not df.empty:
        if 'precio_base' in df.columns:
            df['precio_base'] = pd.to_numeric(df['precio_base'], errors='coerce').fillna(0)
            
        if 'fecha_de_publicacion' in df.columns:
            # Parse dates safely and remove timezone for clean comparison
            df['fecha_dt'] = pd.to_datetime(df['fecha_de_publicacion'], errors='coerce', format='mixed')
            df['fecha_dt'] = df['fecha_dt'].dt.tz_localize(None)
            
    return df

with st.spinner("🚀 Conectando directamente con la API oficial del SECOP II..."):
    try:
        raw_df = cargar_datos_secop_json(limite)
    except Exception as e:
        st.error(f"Error al conectar con la API de Datos Abiertos: {e}")
        raw_df = pd.DataFrame()

if not raw_df.empty:
    st.markdown(f'<div class="badge-info">📊 <b>Base cargada exitosamente:</b> {len(raw_df):,} procesos vigentes y recientes descargados directamente del SECOP II.</div>', unsafe_allow_html=True)
    
    df = raw_df.copy()
    
    # ---------------------------------------------------------
    # APLICACIÓN DE FILTROS EN MEMORIA (PANDAS)
    # ---------------------------------------------------------
    
    # A. Filtro de Fecha (calculado sobre la fecha máxima encontrada en los datos)
    if 'fecha_dt' in df.columns and df['fecha_dt'].notna().any():
        max_fecha_datos = df['fecha_dt'].max()
        
        if "30 Días" in periodo:
            corte = max_fecha_datos - pd.Timedelta(days=30)
            df = df[df['fecha_dt'] >= corte]
        elif "60 Días" in periodo:
            corte = max_fecha_datos - pd.Timedelta(days=60)
            df = df[df['fecha_dt'] >= corte]
        elif "90 Días" in periodo:
            corte = max_fecha_datos - pd.Timedelta(days=90)
            df = df[df['fecha_dt'] >= corte]
        elif "Año 2026" in periodo:
            df = df[df['fecha_dt'] >= pd.Timestamp('2026-01-01')]

    # B. Filtro de RUP / Modalidad
    if "Solo Sin RUP" in filtro_rup and 'modalidad_de_contratacion' in df.columns:
        df = df[df['modalidad_de_contratacion'].astype(str).str.lower().str.contains('mínima cuantía|minima cuantia', na=False)]
    elif "Selección Abreviada" in filtro_rup and 'modalidad_de_contratacion' in df.columns:
        df = df[df['modalidad_de_contratacion'].astype(str).str.lower().str.contains('selección abreviada|seleccion abreviada', na=False)]
    elif "Licitación Pública" in filtro_rup and 'modalidad_de_contratacion' in df.columns:
        df = df[df['modalidad_de_contratacion'].astype(str).str.lower().str.contains('licitación pública|licitacion publica', na=False)]
    elif "Concurso de Méritos" in filtro_rup and 'modalidad_de_contratacion' in df.columns:
        df = df[df['modalidad_de_contratacion'].astype(str).str.lower().str.contains('concurso de méritos|concurso de meritos', na=False)]

    # C. Filtro de Sector UNSPSC
    cod_cat = CATEGORIAS_UNSPSC[sector_sel]
    if cod_cat != "TODOS" and 'codigo_principal_de_categoria' in df.columns:
        df = df[df['codigo_principal_de_categoria'].astype(str).str.contains(cod_cat, na=False)]

    # D. Filtro de Palabra Clave
    if palabra_clave.strip():
        pk = palabra_clave.lower().strip()
        cond_nom = df['nombre_del_procedimiento'].astype(str).str.lower().str.contains(pk, na=False)
        cond_desc = df['descripci_n_del_procedimiento'].astype(str).str.lower().str.contains(pk, na=False)
        df = df[cond_nom | cond_desc]

    # ---------------------------------------------------------
    # MOSTRAR RESULTADOS
    # ---------------------------------------------------------
    
    if not df.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Oportunidades Filtradas", f"{len(df):,}")
        with col2:
            st.metric("Bolsa Total Disponible ($)", f"${df['precio_base'].sum():,.0f} COP")
        with col3:
            dep_top = df['departamento_entidad'].value_counts().index[0] if ('departamento_entidad' in df.columns and not df.empty) else "N/A"
            st.metric("Dep. con Más Procesos", f"{dep_top}")

        st.markdown("---")
        
        # Extraer URL limpia si viene en formato dict/json
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

        cols_finales = [c for c in ['referencia_del_proceso', 'entidad', 'departamento_entidad', 'modalidad_de_contratacion', 'nombre_del_procedimiento', 'precio_base', 'fecha_de_publicacion', 'fecha_de_recepcion_de', 'url_clean'] if c in data_display.columns]

        st.dataframe(
            data_display[cols_finales],
            column_config={
                "url_clean": st.column_config.LinkColumn("Enlace SECOP II", display_text="Ver Pliegos 🔗"),
                "precio_base": st.column_config.NumberColumn("Presupuesto ($ COP)", format="$%'.0f"),
                "referencia_del_proceso": "Proceso",
                "entidad": "Entidad Compradora",
                "departamento_entidad": "Departamento",
                "modalidad_de_contratacion": "Modalidad",
                "nombre_del_procedimiento": "Objeto del Contrato",
                "fecha_de_publicacion": "Fecha Publicación",
                "fecha_de_recepcion_de": "Fecha Cierre"
            },
            use_container_width=True,
            hide_index=True
        )

        csv_data = data_display.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar Reporte Filtrado en CSV / Excel",
            data=csv_data,
            file_name=f"Radar_Licitaciones_VLAO_{periodo.replace(' ', '_')}.csv",
            mime="text/csv"
        )
    else:
        st.warning("⚠️ No se encontraron procesos que coincidan con la combinación exacta de filtros seleccionada.")
        st.info("💡 **Sugerencia:** Prueba cambiando 'Ventana de Tiempo' a *'Todos los procesos recientes'* o borra la palabra clave para ampliar los resultados.")
