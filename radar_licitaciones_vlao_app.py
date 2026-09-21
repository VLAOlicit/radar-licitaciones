import streamlit as st
import pandas as pd
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
        "Últimos 60 Días"
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

# 5. Límite de Resultados
limite = st.sidebar.slider("📊 Cantidad de procesos a consultar:", 500, 5000, 2000, 500)

# ---------------------------------------------------------
# CONSTRUCCIÓN DE LA CONSULTA A LA API (SODA / SECOP II)
# ---------------------------------------------------------

where_clauses = ["estado_resumen in('Presentación de ofertas','Publicado')"]

# A. Aplicar Filtro de Fecha (2026)
if "2do Semestre 2026" in periodo:
    where_clauses.append("fecha_de_publicacion >= '2026-07-01T00:00:00.000'")
elif "Año 2026 Completo" in periodo:
    where_clauses.append("fecha_de_publicacion >= '2026-01-01T00:00:00.000'")
elif "Últimos 30 Días" in periodo:
    fecha_30 = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%dT00:00:00.000')
    where_clauses.append(f"fecha_de_publicacion >= '{fecha_30}'")
elif "Últimos 60 Días" in periodo:
    fecha_60 = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%dT00:00:00.000')
    where_clauses.append(f"fecha_de_publicacion >= '{fecha_60}'")

# B. Aplicar Filtro de Modalidad / RUP
if "Solo Sin RUP" in filtro_rup:
    where_clauses.append("(lower(modalidad_de_contratacion) like '%m%nima cuant%a%')")
elif "Selección Abreviada" in filtro_rup:
    where_clauses.append("(lower(modalidad_de_contratacion) like '%selecci%n abreviada%')")
elif "Licitación Pública" in filtro_rup:
    where_clauses.append("(lower(modalidad_de_contratacion) like '%licitaci%n p%blica%')")
elif "Concurso de Méritos" in filtro_rup:
    where_clauses.append("(lower(modalidad_de_contratacion) like '%concurso de m%ritos%')")

# C. Aplicar Filtro de Sector UNSPSC
unspsc_map = {
    "🛠️ Ferretería, Herramientas, Eléctricos y Pinturas": "(codigo_principal_de_categoria like '3116%' OR codigo_principal_de_categoria like '2711%' OR codigo_principal_de_categoria like '3010%' OR codigo_principal_de_categoria like '3912%' OR codigo_principal_de_categoria like '3121%' OR codigo_principal_de_categoria like '4014%')",
    "💻 Tecnología, Software y Comunicaciones": "(codigo_principal_de_categoria like '4321%' OR codigo_principal_de_categoria like '4323%' OR codigo_principal_de_categoria like '8111%')",
    "🏥 Salud, Medicamentos y Equipos Médicos": "(codigo_principal_de_categoria like '4200%' OR codigo_principal_de_categoria like '5100%')",
    "🍎 Alimentos, Catering, Aseo y Cafetería": "(codigo_principal_de_categoria like '5000%' OR codigo_principal_de_categoria like '4713%')",
    "🚗 Vehículos, Maquinaria, Repuestos y Mantenimiento": "(codigo_principal_de_categoria like '2510%' OR codigo_principal_de_categoria like '7818%')",
    "🛡️ Vigilancia, Seguridad Privada y Custodia": "(codigo_principal_de_categoria like '9212%' OR codigo_principal_de_categoria like '7611%')",
    "🏗️ Obra Civil e Infraestructura": "(codigo_principal_de_categoria like '7214%' OR codigo_principal_de_categoria like '7212%')"
}

if sector in unspsc_map:
    where_clauses.append(unspsc_map[sector])

# D. Aplicar Palabra Clave
if palabra_clave:
    pk_clean = palabra_clave.lower().strip()
    where_clauses.append(f"(lower(nombre_del_procedimiento) like '%{pk_clean}%' OR lower(descripci_n_del_procedimiento) like '%{pk_clean}%')")

where_str = " AND ".join(where_clauses)
select_cols = "entidad,departamento_entidad,ciudad_entidad,referencia_del_proceso,codigo_principal_de_categoria,nombre_del_procedimiento,descripci_n_del_procedimiento,modalidad_de_contratacion,precio_base,estado_resumen,fecha_de_publicacion,fecha_de_recepcion_de,urlproceso"

base_url = f"https://www.datos.gov.co/resource/p6dx-8zbt.csv?$select={select_cols}&$limit={limite}&$where={urllib.parse.quote(where_str)}&$order=fecha_de_publicacion DESC"

# Cargar Datos
@st.cache_data(ttl=300)
def cargar_datos(url):
    df = pd.read_csv(url)
    if 'precio_base' in df.columns:
        df['precio_base'] = pd.to_numeric(df['precio_base'], errors='coerce').fillna(0)
    return df

with st.spinner("🚀 Conectando con la API del SECOP II para extraer licitaciones vigentes 2026..."):
    try:
        data = cargar_datos(base_url)
        st.success(f"¡Éxito! Se encontraron **{len(data):,}** licitaciones vigentes publicadas en 2026.")
    except Exception as e:
        st.error("Error temporal al conectar con la API de Datos Abiertos. Intenta nuevamente.")
        data = pd.DataFrame()

# Mostrar Resultados
if not data.empty:
    # Tarjetas Métricas
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Oportunidades Encontradas", f"{len(data):,}")
    with col2:
        st.metric("Bolsa Total Disponible ($)", f"${data['precio_base'].sum():,.0f} COP")
    with col3:
        dep_top = data['departamento_entidad'].value_counts().index[0] if 'departamento_entidad' in data.columns and not data.empty else "N/A"
        st.metric("Dep. con Más Procesos", f"{dep_top}")

    st.markdown("---")
    
    # Filtros rápidos en pantalla
    st.subheader("📋 Lista de Procesos Vigentes para Presentar Oferta")
    
    # Formatear columna URL para visualización limpia
    data_display = data.copy()
    
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

    # Botón de Descarga Excel
    csv_data = data.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar Reporte Completo en CSV / Excel",
        data=csv_data,
        file_name=f"radar_secop_2026_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )
else:
    st.warning("No se encontraron procesos vigentes que coincidan con los filtros seleccionados. Prueba ampliando la ventana de tiempo o cambiando la palabra clave.")
