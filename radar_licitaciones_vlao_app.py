import streamlit as st
import pandas as pd
import urllib.parse
import datetime

# Configuración de la página
st.set_page_config(
    page_title="Radar de Licitaciones SECOP II - VLAO INGENIERÍA S.A.S.",
    page_icon="🏗️",
    layout="wide"
)

# Estilos CSS personalizados
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        color: #1E3A8A;
        font-weight: bold;
        margin-bottom: 0px;
    }
    .sub-title {
        font-size: 1.1rem;
        color: #4B5563;
        margin-bottom: 20px;
    }
    .metric-card {
        background-color: #F3F4F6;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #1E3A8A;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🎯 Radar Quirúrgico de Licitaciones SECOP II</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">VLAO INGENIERÍA S.A.S. | Módulo Operativo de Búsqueda y Selección de Procesos</div>', unsafe_allow_html=True)

# Categorías UNSPSC por defecto
CATEGORIAS_UNSPSC = {
    "3116 - Ferretería y Herrajes": "3116%",
    "2711 - Herramientas de Mano": "2711%",
    "3010 / 3019 - Materiales de Construcción y Acabados": "3010%",
    "3912 - Equipos y Suministros Eléctricos": "3912%",
    "3121 - Pinturas, Esmaltes y Recubrimientos": "3121%",
    "4014 - Tuberías, Plomería y Grifería": "4014%",
    "3911 - Iluminación y Luminarias": "3911%",
    "7210 - Mantenimiento e Instalaciones": "7210%"
}

# Sidebar - Filtros
st.sidebar.header("🔍 Filtros de Búsqueda Quirúrgica")

# Filtro por Palabras Clave
palabras_clave = st.sidebar.text_input(
    "Palabra clave en el objeto (ej. ferreteria, pintura, tuberia):",
    value=""
)

# Filtro por Categorías UNSPSC
cats_seleccionadas = st.sidebar.multiselect(
    "Sectores y Categorías UNSPSC:",
    options=list(CATEGORIAS_UNSPSC.keys()),
    default=list(CATEGORIAS_UNSPSC.keys())[:4]
)

# Filtro por Estado
estados = st.sidebar.multiselect(
    "Estado del Proceso:",
    options=["Presentación de ofertas", "Publicado", "Borrador", "Seleccionado"],
    default=["Presentación de ofertas", "Publicado"]
)

# Limit de registros
limite = st.sidebar.slider("Número máximo de registros a traer:", min_value=500, max_value=10000, value=3000, step=500)

@st.cache_data(ttl=600)
def cargar_datos_secop(cats, estados_sel, kw, max_rows):
    where_clauses = []
    
    if estados_sel:
        estados_str = ",".join([f"'{e}'" for e in estados_sel])
        where_clauses.append(f"estado_resumen in({estados_str})")
        
    if cats:
        cat_conditions = [f"codigo_principal_de_categoria like '{CATEGORIAS_UNSPSC[c]}'" for c in cats]
        where_clauses.append(f"({' OR '.join(cat_conditions)})")
        
    if kw.strip():
        kw_clean = kw.strip().lower()
        where_clauses.append(f"(lower(nombre_del_procedimiento) like '%{kw_clean}%' OR lower(descripci_n_del_procedimiento) like '%{kw_clean}%')")
        
    where_str = " AND ".join(where_clauses) if where_clauses else ""
    
    base_url = "https://www.datos.gov.co/resource/p6dx-8zbt.csv"
    select_cols = "entidad,departamento_entidad,ciudad_entidad,referencia_del_proceso,codigo_principal_de_categoria,nombre_del_procedimiento,descripci_n_del_procedimiento,modalidad_de_contratacion,tipo_de_contrato,precio_base,estado_resumen,fecha_de_publicacion,fecha_de_recepcion_de,urlproceso"
    
    query_params = {
        "$select": select_cols,
        "$limit": max_rows,
        "$order": "fecha_de_publicacion DESC"
    }
    if where_str:
        query_params["$where"] = where_str
        
    url = f"{base_url}?{urllib.parse.urlencode(query_params)}"
    
    try:
        df = pd.read_csv(url)
        return df
    except Exception as e:
        st.error(f"Error al conectar con la API de Datos Abiertos: {e}")
        return pd.DataFrame()

with st.spinner("Consultando SECOP II en tiempo real..."):
    df = cargar_datos_secop(cats_seleccionadas, estados, palabras_clave, limite)

if not df.empty:
    st.success(f"✅ Se encontraron **{len(df)}** oportunidades activas alineadas con el portafolio de VLAO INGENIERÍA S.A.S.")
    
    # Métricas clave arriba
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Procesos Encontrados", f"{len(df):,}")
    with col2:
        if "precio_base" in df.columns:
            total_val = pd.to_numeric(df["precio_base"], errors="coerce").sum()
            st.metric("Bolsa Total Presupuestada", f"${total_val:,.0f} COP")
    with col3:
        deptos_count = df["departamento_entidad"].nunique() if "departamento_entidad" in df.columns else 0
        st.metric("Departamentos con Oferta", f"{deptos_count}")

    st.markdown("---")
    
    # Filtros secundarios en pantalla
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        deptos = sorted(df["departamento_entidad"].dropna().unique())
        depto_sel = st.multiselect("Filtrar por Departamento:", options=deptos, default=[])
    with col_f2:
        modalidades = sorted(df["modalidad_de_contratacion"].dropna().unique())
        mod_sel = st.multiselect("Filtrar por Modalidad:", options=modalidades, default=[])
        
    df_filtrado = df.copy()
    if depto_sel:
        df_filtrado = df_filtrado[df_filtrado["departamento_entidad"].isin(depto_sel)]
    if mod_sel:
        df_filtrado = df_filtrado[df_filtrado["modalidad_de_contratacion"].isin(mod_sel)]

    # Mostrar Tabla Interactiva
    st.subheader("📋 Listado Quirúrgico de Oportunidades")
    
    # Formatear columna URL para enlace
    st.dataframe(
        df_filtrado[[
            "referencia_del_proceso", "entidad", "departamento_entidad", 
            "modalidad_de_contratacion", "nombre_del_procedimiento", 
            "precio_base", "fecha_de_recepcion_de", "urlproceso"
        ]],
        column_config={
            "urlproceso": st.column_config.LinkColumn("Enlace SECOP II", display_text="Ver Pliegos 🔗"),
            "precio_base": st.column_config.NumberColumn("Presupuesto ($ COP)", format="$%d"),
            "referencia_del_proceso": "Proceso",
            "entidad": "Entidad Compradora",
            "departamento_entidad": "Departamento",
            "modalidad_de_contratacion": "Modalidad",
            "nombre_del_procedimiento": "Objeto del Contrato",
            "fecha_de_recepcion_de": "Fecha Cierre"
        },
        use_container_width=True,
        hide_index=True
    )
    
    # Botón de Descarga
    csv_data = df_filtrado.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar Reporte en Excel / CSV para el Equipo Comercial",
        data=csv_data,
        file_name=f"Radar_Licitaciones_VLAO_{datetime.date.today()}.csv",
        mime="text/csv"
    )
else:
    st.warning("No se encontraron procesos con los filtros seleccionados. Intenta ampliar las palabras clave o seleccionar más categorías.")
