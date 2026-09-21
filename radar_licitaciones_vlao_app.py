import streamlit as st
import pandas as pd
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
Filtra procesos en tiempo real del SECOP II sin riesgo de errores de conexión. Permite identificar oportunidades **Sin RUP** (*Mínima Cuantía*), filtrar por periodo del 2026, sectores o palabras clave.
""")

# Sidebar - Filtros
st.sidebar.header("⚙️ Configuración del Radar")

# 1. Filtro de Periodo / Año
periodo = st.sidebar.selectbox(
    "📅 Ventana de Tiempo (Fecha de Publicación):",
    [
        "2do Semestre 2026 (Julio 2026 - Presente)",
        "Año 2026 Completo (Enero 2026 - Presente)",
        "Últimos 30 Días",
        "Últimos 60 Días",
        "Ver Todos los Procesos Recientes"
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
        "🌐 Todos los Sectores (Sin Restricción)",
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
palabra_clave = st.sidebar.text_input(
    "🔎 Palabra clave en el Objeto / Nombre:", 
    "", 
    placeholder="Ej: suministro, herramientas, mantenimiento, pintura..."
)

# 5. Cantidad de Registros a Descargar
limite = st.sidebar.slider("📊 Cantidad de procesos a consultar en SECOP II:", 1000, 5000, 3000, 500)

# URL Limpia e Infalible para SODA API
API_URL = f"https://www.datos.gov.co/resource/p6dx-8zbt.csv?$select=entidad,departamento_entidad,ciudad_entidad,referencia_del_proceso,codigo_principal_de_categoria,nombre_del_procedimiento,descripci_n_del_procedimiento,modalidad_de_contratacion,precio_base,estado_resumen,fecha_de_publicacion,fecha_de_recepcion_de,urlproceso&$limit={limite}&$order=fecha_de_publicacion DESC"

@st.cache_data(ttl=300)
def obtener_datos(url):
    df = pd.read_csv(url)
    # Limpieza inicial
    if 'precio_base' in df.columns:
        df['precio_base'] = pd.to_numeric(df['precio_base'], errors='coerce').fillna(0)
    if 'fecha_de_publicacion' in df.columns:
        df['fecha_dt'] = pd.to_datetime(df['fecha_de_publicacion'], errors='coerce')
    return df

with st.spinner("🚀 Conectando con la API oficial de Datos Abiertos Colombia..."):
    try:
        raw_df = obtener_datos(API_URL)
        error_conexion = False
    except Exception as e:
        error_conexion = True
        raw_df = pd.DataFrame()

if error_conexion:
    st.error("⚠️ No se pudo conectar directamente con el servidor de Datos Abiertos. Por favor verifica tu conexión a internet o intenta nuevamente en unos segundos.")
elif raw_df.empty:
    st.warning("El servidor no retornó datos en este momento.")
else:
    # ---------------------------------------------------------
    # FILTRADO ROBUSTO EN MEMORIA CON PANDAS
    # ---------------------------------------------------------
    df_filtered = raw_df.copy()

    # A. Estado activo por defecto (solo procesos vigentes o en presentación de ofertas)
    if 'estado_resumen' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['estado_resumen'].astype(str).str.lower().isin(['presentación de ofertas', 'presentacion de ofertas', 'publicado'])]

    # B. Filtro de Fechas
    now = datetime.now()
    if 'fecha_dt' in df_filtered.columns:
        if "2do Semestre 2026" in periodo:
            df_filtered = df_filtered[df_filtered['fecha_dt'] >= pd.Timestamp('2026-07-01')]
        elif "Año 2026 Completo" in periodo:
            df_filtered = df_filtered[df_filtered['fecha_dt'] >= pd.Timestamp('2026-01-01')]
        elif "Últimos 30 Días" in periodo:
            fecha_lim = now - timedelta(days=30)
            df_filtered = df_filtered[df_filtered['fecha_dt'] >= fecha_lim]
        elif "Últimos 60 Días" in periodo:
            fecha_lim = now - timedelta(days=60)
            df_filtered = df_filtered[df_filtered['fecha_dt'] >= fecha_lim]

    # C. Filtro de RUP / Modalidad
    if 'modalidad_de_contratacion' in df_filtered.columns:
        mod_col = df_filtered['modalidad_de_contratacion'].astype(str).str.lower()
        if "Solo Sin RUP" in filtro_rup:
            df_filtered = df_filtered[mod_col.str.contains('mínima|minima', regex=True, na=False)]
        elif "Selección Abreviada" in filtro_rup:
            df_filtered = df_filtered[mod_col.str.contains('abreviada', regex=True, na=False)]
        elif "Licitación Pública" in filtro_rup:
            df_filtered = df_filtered[mod_col.str.contains('licitación|licitacion', regex=True, na=False)]
        elif "Concurso de Méritos" in filtro_rup:
            df_filtered = df_filtered[mod_col.str.contains('méritos|meritos', regex=True, na=False)]

    # D. Filtro de Sector UNSPSC
    if sector != "🌐 Todos los Sectores (Sin Restricción)" and 'codigo_principal_de_categoria' in df_filtered.columns:
        unspsc_prefixes = {
            "🛠️ Ferretería, Herramientas, Eléctricos y Pinturas": ('3116', '2711', '3010', '3912', '3121', '4014'),
            "💻 Tecnología, Software y Comunicaciones": ('4321', '4323', '8111'),
            "🏥 Salud, Medicamentos y Equipos Médicos": ('4200', '5100'),
            "🍎 Alimentos, Catering, Aseo y Cafetería": ('5000', '4713'),
            "🚗 Vehículos, Maquinaria, Repuestos y Mantenimiento": ('2510', '7818'),
            "🛡️ Vigilancia, Seguridad Privada y Custodia": ('9212', '7611'),
            "🏗️ Obra Civil e Infraestructura": ('7214', '7212')
        }
        prefixes = unspsc_prefixes.get(sector, ())
        if prefixes:
            cod_col = df_filtered['codigo_principal_de_categoria'].astype(str)
            df_filtered = df_filtered[cod_col.str.startswith(prefixes)]

    # E. Filtro de Palabra Clave
    if palabra_clave.strip():
        pk = palabra_clave.lower().strip()
        nomb = df_filtered['nombre_del_procedimiento'].astype(str).str.lower()
        desc = df_filtered['descripci_n_del_procedimiento'].astype(str).str.lower()
        df_filtered = df_filtered[nomb.str.contains(pk, na=False) | desc.str.contains(pk, na=False)]

    # ---------------------------------------------------------
    # DESPLIEGUE DE RESULTADOS EN STREAMLIT
    # ---------------------------------------------------------
    st.success(f"¡Éxito! Se encontraron **{len(df_filtered):,}** licitaciones vigentes con tus filtros seleccionados.")

    # Métricas
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Procesos Encontrados", f"{len(df_filtered):,}")
    with col2:
        bolsa = df_filtered['precio_base'].sum() if 'precio_base' in df_filtered.columns else 0
        st.metric("Bolsa Total ($ COP)", f"${bolsa:,.0f}")
    with col3:
        top_dep = df_filtered['departamento_entidad'].mode()[0] if 'departamento_entidad' in df_filtered.columns and not df_filtered.empty else "N/A"
        st.metric("Departamento Principal", top_dep)

    st.markdown("---")

    if not df_filtered.empty:
        # Preparar columnas para tabla
        cols_to_show = ['entidad', 'departamento_entidad', 'modalidad_de_contratacion', 'nombre_del_procedimiento', 'precio_base', 'fecha_de_publicacion', 'fecha_de_recepcion_de', 'urlproceso']
        available_cols = [c for c in cols_to_show if c in df_filtered.columns]
        
        display_df = df_filtered[available_cols].copy()

        st.dataframe(
            display_df,
            column_config={
                "urlproceso": st.column_config.LinkColumn("Enlace SECOP II", display_text="Ver Pliegos 🔗"),
                "precio_base": st.column_config.NumberColumn("Presupuesto ($ COP)", format="$%'.0f"),
                "fecha_de_publicacion": "Fecha Publicación",
                "fecha_de_recepcion_de": "Cierre Ofertas",
                "nombre_del_procedimiento": "Objeto del Proceso",
                "entidad": "Entidad Compradora",
                "modalidad_de_contratacion": "Modalidad",
                "departamento_entidad": "Departamento"
            },
            use_container_width=True,
            hide_index=True
        )

        # Botón de Descarga Excel
        csv_bytes = df_filtered.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar Reporte Filtrado en Excel / CSV",
            data=csv_bytes,
            file_name=f"radar_secop_2026_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
    else:
        st.warning("No hay procesos que coincidan exactamente con la combinación de filtros seleccionados. Intenta cambiar el sector, la palabra clave o ampliar la ventana de tiempo.")
