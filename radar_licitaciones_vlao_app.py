import streamlit as st
import pandas as pd
import requests
import urllib.parse
import unicodedata
from datetime import datetime, timedelta

# Configuración de página
st.set_page_config(
    page_title="Radar SECOP II v12 - VLAO INGENIERÍA S.A.S.",
    layout="wide",
    page_icon="🎯"
)

# Estilos CSS
st.markdown("""
<style>
    .main-title { font-size: 2.2rem; color: #1E3A8A; font-weight: bold; margin-bottom: 0px; }
    .sub-title { font-size: 1.1rem; color: #4B5563; margin-bottom: 20px; }
    .badge-info { background-color: #EFF6FF; color: #1E40AF; padding: 10px; border-radius: 8px; font-weight: 500; margin-bottom: 15px; border-left: 4px solid #3B82F6; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🎯 Radar Quirúrgico SECOP II - Versión 12.0</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">VLAO INGENIERÍA S.A.S. | Módulo Inteligente de Búsqueda y Selección de Oportunidades</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# FUNCIONES DE FORMATEO Y NORMALIZACION
# ---------------------------------------------------------

def normalizar_texto(texto):
    """Elimina acentos/tildes y convierte a minúsculas para comparaciones perfectas."""
    if not texto or pd.isna(texto):
        return ""
    texto_str = str(texto)
    nfkd = unicodedata.normalize('NFD', texto_str)
    sin_tildes = "".join([c for c in nfkd if unicodedata.category(c) != 'Mn'])
    return sin_tildes.lower().strip()

def formatear_pesos_colombianos(valor):
    """Convierte un número a formato moneda colombiana con separadores de miles/millones (.)"""
    try:
        val_num = float(valor)
        if pd.isna(val_num) or val_num == 0:
            return "$ 0 COP"
        # Formato estándar con comas y reemplazo a puntos para estilo colombiano
        formateado = f"${val_num:,.0f}".replace(",", ".")
        return f"{formateado} COP"
    except:
        return "$ 0 COP"

# Sidebar - Filtros de Búsqueda
st.sidebar.header("⚙️ Configuración del Radar")

# 1. Buscador libre por palabra clave
palabra_clave = st.sidebar.text_input(
    "🔎 Palabra clave (Objeto o Nombre):",
    "",
    placeholder="Ej: cubierta, ferreteria, mantenimiento, impermeabilizacion, suministro..."
)

# 2. Ventana de Tiempo (Basada estricta y únicamente en FECHA DE PUBLICACIÓN)
periodo = st.sidebar.selectbox(
    "📅 Ventana de Tiempo (Fecha de Publicación):",
    [
        "Todos los procesos recientes (Recomendado)",
        "Últimos 30 Días de Publicación",
        "Últimos 60 Días de Publicación",
        "Últimos 90 Días de Publicación",
        "Publicados en el Año 2026"
    ]
)

# 3. Modalidades completas del SECOP II
MODALIDADES_SECOP = {
    "🌐 Todas las Modalidades (100% del SECOP II - Incluye Contratación Directa de Suministros)": "TODAS",
    "⚡ Mínima Cuantía (Sin RUP - Art. 2 Ley 1150/2007)": "MINIMA",
    "📋 Selección Abreviada (Menor Cuantía / Subasta Inversa)": "ABREVIADA",
    "🏛️ Licitación Pública": "LICITACION",
    "🎓 Concurso de Méritos": "CONCURSO",
    "📑 Contratación Directa (Urgencias Manifiestas / Compras Directas)": "DIRECTA",
    "🏢 Régimen Especial (Empresas Públicas, E.S.E. Hospitales, Universidades)": "REGIMEN_ESPECIAL",
    "🛒 Acuerdo Marco de Precios / Tienda Virtual CCE": "ACUERDO_MARCO"
}

filtro_modalidad = st.sidebar.selectbox(
    "📜 Modalidad de Contratación:",
    options=list(MODALIDADES_SECOP.keys())
)

# 4. Filtro por Ciudad / Municipio
filtro_ciudad_kw = st.sidebar.text_input(
    "📍 Ciudad / Municipio (Barra Lateral):",
    "",
    placeholder="Ej: Bogota, Medellin, Cali, Neiva, Villavicencio..."
)

# 5. Filtro por Entidad Compradora
filtro_entidad_kw = st.sidebar.text_input(
    "🏛️ Entidad Compradora (Barra Lateral):",
    "",
    placeholder="Ej: SENA, ICBF, Registraduria, Ejercito, Alcaldia..."
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
    "📐 Ingeniería, Diseños e Interventoría (8110)": "8110",
    "💻 Tecnología, Software y Comunicaciones (4321/4323)": "4321",
    "🏥 Salud y Equipos Médicos (4200/5100)": "4200",
    "🚗 Vehículos y Maquinaria (2510/7818)": "2510",
    "🛡️ Vigilancia y Seguridad (9212)": "9212"
}

sector_sel = st.sidebar.selectbox(
    "🏢 Sector / Categoría UNSPSC:",
    options=list(CATEGORIAS_UNSPSC.keys())
)

# 7. Cantidad máxima de registros a extraer
limite = st.sidebar.slider("📊 Tamaño del Lote de Extracción (Registros SECOP II):", 500, 10000, 3000, 500)

# ---------------------------------------------------------
# FUNCION DE CONSULTA DE DATOS BASE
# ---------------------------------------------------------

@st.cache_data(ttl=300)
def consultar_secop_v12(max_rows):
    base_url = "https://www.datos.gov.co/resource/p6dx-8zbt.json"
    select_cols = "entidad,departamento_entidad,ciudad_entidad,referencia_del_proceso,codigo_principal_de_categoria,nombre_del_procedimiento,descripci_n_del_procedimiento,modalidad_de_contratacion,precio_base,estado_resumen,fecha_de_publicacion,fecha_de_recepcion_de,urlproceso"
    
    params = {
        "$select": select_cols,
        "$order": "fecha_de_publicacion DESC",
        "$limit": str(max_rows)
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
            df['precio_base_num'] = pd.to_numeric(df['precio_base'], errors='coerce').fillna(0)
        else:
            df['precio_base_num'] = 0.0
            
        # Parseo estricto de FECHA DE PUBLICACIÓN
        if 'fecha_de_publicacion' in df.columns:
            df['fecha_pub_dt'] = pd.to_datetime(df['fecha_de_publicacion'], errors='coerce').dt.tz_localize(None)
            df['fecha_pub_clean'] = df['fecha_pub_dt'].dt.strftime('%Y-%m-%d')
        else:
            df['fecha_pub_dt'] = pd.NaT
            df['fecha_pub_clean'] = "Sin fecha"

        # Fecha de cierre secundaria (solo informativa)
        if 'fecha_de_recepcion_de' in df.columns:
            df['fecha_cierre_clean'] = pd.to_datetime(df['fecha_de_recepcion_de'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M').fillna("No especificada")
        else:
            df['fecha_cierre_clean'] = "No especificada"
            
    return df

with st.spinner("🚀 Conectando directamente con la base nacional del SECOP II (Datos Abiertos)..."):
    try:
        raw_df = consultar_secop_v12(limite)
    except Exception as e:
        st.error(f"Error técnico al conectar con el servidor estatal: {e}")
        raw_df = pd.DataFrame()

# ---------------------------------------------------------
# MOTOR DE FILTRADO EN MEMORIA (PANDAS)
# ---------------------------------------------------------

if not raw_df.empty:
    df = raw_df.copy()
    
    # 1. Filtro Estricto por FECHA DE PUBLICACIÓN
    if 'fecha_pub_dt' in df.columns and df['fecha_pub_dt'].notna().any():
        max_f_pub = df['fecha_pub_dt'].max()
        
        if "30 Días" in periodo:
            corte = max_f_pub - pd.Timedelta(days=30)
            df = df[df['fecha_pub_dt'] >= corte]
        elif "60 Días" in periodo:
            corte = max_f_pub - pd.Timedelta(days=60)
            df = df[df['fecha_pub_dt'] >= corte]
        elif "90 Días" in periodo:
            corte = max_f_pub - pd.Timedelta(days=90)
            df = df[df['fecha_pub_dt'] >= corte]
        elif "Año 2026" in periodo:
            df = df[df['fecha_pub_dt'] >= pd.Timestamp('2026-01-01')]

    # 2. Filtro Anti-OPS de Contratación Directa (Filtro Inteligente de Personal)
    if 'nombre_del_procedimiento' in df.columns and 'descripci_n_del_procedimiento' in df.columns:
        norm_nombre = df['nombre_del_procedimiento'].apply(normalizar_texto)
        norm_desc = df['descripci_n_del_procedimiento'].apply(normalizar_texto)
        
        # Descartar contratos de prestación de servicios profesionales de personas naturales
        patron_ops = 'prestacion de servicios|apoyo a la gestion|honorarios|prestacion de servicio profesional'
        es_ops = norm_nombre.str.contains(patron_ops, na=False) | norm_desc.str.contains(patron_ops, na=False)
        
        # Mantener si NO es OPS o si es de otras modalidades
        df = df[~es_ops]

    # 3. Filtro por Modalidad
    mod_code = MODALIDADES_SECOP[filtro_modalidad]
    if mod_code != "TODAS" and 'modalidad_de_contratacion' in df.columns:
        norm_mod = df['modalidad_de_contratacion'].apply(normalizar_texto)
        if mod_code == "MINIMA":
            df = df[norm_mod.str.contains('minima|cuantia', na=False)]
        elif mod_code == "ABREVIADA":
            df = df[norm_mod.str.contains('abreviada|subasta|menor cuantia', na=False)]
        elif mod_code == "LICITACION":
            df = df[norm_mod.str.contains('licitacion', na=False)]
        elif mod_code == "CONCURSO":
            df = df[norm_mod.str.contains('concurso|meritos', na=False)]
        elif mod_code == "DIRECTA":
            df = df[norm_mod.str.contains('directa', na=False)]
        elif mod_code == "REGIMEN_ESPECIAL":
            df = df[norm_mod.str.contains('especial|regimen', na=False)]
        elif mod_code == "ACUERDO_MARCO":
            df = df[norm_mod.str.contains('marco|tienda', na=False)]

    # 4. Filtro por Categoría UNSPSC
    cod_cat = CATEGORIAS_UNSPSC[sector_sel]
    if cod_cat != "TODOS" and 'codigo_principal_de_categoria' in df.columns:
        df = df[df['codigo_principal_de_categoria'].astype(str).str.contains(cod_cat, na=False)]

    # 5. Filtro por Palabra Clave
    if palabra_clave.strip():
        pk = normalizar_texto(palabra_clave)
        cond_n = df['nombre_del_procedimiento'].apply(normalizar_texto).str.contains(pk, na=False)
        cond_d = df['descripci_n_del_procedimiento'].apply(normalizar_texto).str.contains(pk, na=False)
        df = df[cond_n | cond_d]

    # 6. Filtro por Ciudad (Barra lateral)
    if filtro_ciudad_kw.strip() and 'ciudad_entidad' in df.columns:
        ckw = normalizar_texto(filtro_ciudad_kw)
        df = df[df['ciudad_entidad'].apply(normalizar_texto).str.contains(ckw, na=False)]

    # 7. Filtro por Entidad (Barra lateral)
    if filtro_entidad_kw.strip() and 'entidad' in df.columns:
        ekw = normalizar_texto(filtro_entidad_kw)
        df = df[df['entidad'].apply(normalizar_texto).str.contains(ekw, na=False)]

    # ---------------------------------------------------------
    # DESPLIEGUE EN PANTALLA
    # ---------------------------------------------------------
    
    st.markdown(f'<div class="badge-info">📊 <b>Estado del Radar:</b> Se identificaron <b>{len(df):,}</b> licitaciones corporativas vigentes basadas en la <b>Fecha de Publicación</b>.</div>', unsafe_allow_html=True)
    
    if not df.empty:
        # Métricas principales con formato de moneda colombiana
        bolsa_total = df['precio_base_num'].sum()
        bolsa_fmt = formatear_pesos_colombianos(bolsa_total)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Oportunidades Encontradas", f"{len(df):,}")
        with col2:
            st.metric("Bolsa Total Presupuestada", bolsa_fmt)
        with col3:
            dep_top = df['departamento_entidad'].value_counts().index[0] if ('departamento_entidad' in df.columns and not df.empty) else "N/A"
            st.metric("Departamento Líder", f"{dep_top}")
        with col4:
            m_top = df['modalidad_de_contratacion'].value_counts().index[0] if ('modalidad_de_contratacion' in df.columns and not df.empty) else "N/A"
            st.metric("Modalidad Principal", f"{m_top[:22]}...")

        st.markdown("---")
        
        # Filtros secundarios dinámicos sobre la tabla
        st.subheader("🔍 Filtros Dinámicos en Pantalla")
        col_f1, col_f2, col_f3 = st.columns(3)
        
        with col_f1:
            deptos_opts = sorted([str(d) for d in df['departamento_entidad'].dropna().unique()])
            depto_pantalla = st.multiselect("🗺️ Filtrar por Departamento:", options=deptos_opts, default=[])
        with col_f2:
            ciudades_opts = sorted([str(c) for c in df['ciudad_entidad'].dropna().unique()])
            ciudad_pantalla = st.multiselect("📍 Filtrar por Ciudad / Municipio:", options=ciudades_opts, default=[])
        with col_f3:
            entidades_opts = sorted([str(e) for e in df['entidad'].dropna().unique()])
            entidad_pantalla = st.multiselect("🏛️ Filtrar por Entidad Compradora:", options=entidades_opts, default=[])

        df_pantalla = df.copy()
        if depto_pantalla:
            df_pantalla = df_pantalla[df_pantalla['departamento_entidad'].isin(depto_pantalla)]
        if ciudad_pantalla:
            df_pantalla = df_pantalla[df_pantalla['ciudad_entidad'].isin(ciudad_pantalla)]
        if entidad_pantalla:
            df_pantalla = df_pantalla[df_pantalla['entidad'].isin(entidad_pantalla)]

        # Aplicar formato de moneda legible a la columna de Presupuesto
        df_pantalla['Presupuesto Formateado'] = df_pantalla['precio_base_num'].apply(formatear_pesos_colombianos)

        # Extraer URL limpia
        def extraer_url(val):
            if isinstance(val, dict):
                return val.get('url', '')
            val_str = str(val)
            if 'http' in val_str:
                return val_str
            return ''

        if 'urlproceso' in df_pantalla.columns:
            df_pantalla['url_clean'] = df_pantalla['urlproceso'].apply(extraer_url)
        else:
            df_pantalla['url_clean'] = ''

        # Mapeo de columnas para la tabla interactiva
        cols_map = {
            'fecha_pub_clean': 'Fecha Publicación 📅',
            'referencia_del_proceso': 'Proceso',
            'entidad': 'Entidad Compradora',
            'departamento_entidad': 'Departamento',
            'ciudad_entidad': 'Ciudad / Municipio',
            'modalidad_de_contratacion': 'Modalidad',
            'nombre_del_procedimiento': 'Objeto del Proceso',
            'Presupuesto Formateado': 'Presupuesto ($ COP)',
            'fecha_cierre_clean': 'Cierre Ofertas',
            'url_clean': 'Enlace SECOP II'
        }

        cols_existentes = [c for c in cols_map.keys() if c in df_pantalla.columns]
        data_final = df_pantalla[cols_existentes].rename(columns=cols_map)

        st.subheader("📋 Listado Quirúrgico de Procesos")
        st.dataframe(
            data_final,
            column_config={
                "Enlace SECOP II": st.column_config.LinkColumn("Enlace SECOP II", display_text="Ver Pliegos 🔗"),
                "Presupuesto ($ COP)": st.column_config.TextColumn("Presupuesto ($ COP)"),
                "Fecha Publicación 📅": st.column_config.TextColumn("Fecha Publicación 📅"),
            },
            use_container_width=True,
            hide_index=True
        )

        csv_data = data_final.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar Reporte Completo en CSV / Excel con Presupuestos Formateados",
            data=csv_data,
            file_name=f"Radar_SECOP_v12_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.warning("⚠️ No se encontraron procesos que coincidan con la combinación de filtros activa.")
        st.info("💡 **Sugerencia:** Intenta borrar la palabra clave o ampliar la ventana a 'Todos los procesos recientes' para desplegar más convocatorias.")
""", TargetFile: "/workspace/scratch/radar_licitaciones_vlao_app_v12.py"}
}
EOF
cat << 'EOF' > /workspace/scratch/test_v12.py
import subprocess
print("Writing v12...")
EOF
python3 /workspace/scratch/test_v12.py
