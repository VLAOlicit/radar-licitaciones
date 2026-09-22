import ast
from datetime import datetime, timedelta
import io
import urllib.parse
import unicodedata
import pandas as pd
import requests
import streamlit as st

# ==============================================================================
# CONFIGURACIÓN DE PÁGINA Y ESTILOS - BID WIN VLAO v2.0
# ==============================================================================
st.set_page_config(
    page_title="BID WIN VLAO - Oportunidades SECOP II 2026",
    layout="wide",
    page_icon="🎯"
)

st.markdown("""
    <style>
    .brand-title {
        font-size: 2.6rem;
        font-weight: 900;
        color: #1E3A8A;
        margin-bottom: 0px;
        letter-spacing: -0.5px;
    }
    .brand-slogan {
        font-size: 1.2rem;
        font-weight: 600;
        color: #2563EB;
        margin-bottom: 4px;
    }
    .brand-line {
        font-size: 0.98rem;
        color: #475569;
        margin-bottom: 22px;
    }
    .stMetric {
        background-color: #F8FAFC;
        padding: 14px;
        border-radius: 10px;
        border-left: 5px solid #1E3A8A;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    .opportunity-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-left: 6px solid #2563EB;
        padding: 18px;
        border-radius: 10px;
        margin-bottom: 16px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .card-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #0F172A;
    }
    .card-badge {
        background-color: #EFF6FF;
        color: #1D4ED8;
        padding: 6px 14px;
        border-radius: 16px;
        font-size: 0.92rem;
        font-weight: 700;
    }
    .phase-badge {
        background-color: #F1F5F9;
        color: #334155;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

# 🎨 1. IDENTIDAD VISUAL Y ENCABEZADO
st.markdown('<div class="brand-title">🎯 BID WIN VLAO</div>', unsafe_allow_html=True)
st.markdown('<div class="brand-slogan">"Te acerca a tu próximo negocio con el Estado"</div>', unsafe_allow_html=True)
st.markdown('<div class="brand-line"><b>Línea de Negocio: VLAO INGENIERÍA S.A.S.</b> (Mantenimiento, Obras Civiles, Cubiertas, Instalaciones Eléctricas, Iluminación, Ferretería, Plomería e Interventoría)</div>', unsafe_allow_html=True)
st.divider()

# ==============================================================================
# DICCIONARIOS Y CONFIGURACIONES GENERALES (SIN FILTROS PREVIOS OBLIGATORIOS)
# ==============================================================================
SECTORES_UNSPSC_OPCIONES = {
    "🌐 Todos los Sectores de la Economía (Sin Filtro Previo)": "TODOS",
    "🏢 Portafolio Combinado VLAO (Obras, Eléctricos, Pinturas, Tuberías, Consultoría, Ferretería)": "72|39|31|30|40|81|80|27|25",
    "🛠️ 3116 / 3010 - Ferretería, Herrajes y Materiales de Construcción": "3116|3010",
    "🏗️ 7210 / 7212 / 7214 / 7215 - Obras Civiles, Edificaciones y Mantenimiento": "7210|7212|7214|7215",
    "⚡ 3912 / 3911 / 2612 - Equipos Eléctricos, Iluminación y Redes": "3912|3911|2612",
    "📐 8110 / 8010 - Ingeniería, Consultoría e Interventoría": "8110|8010",
    "🎨 3121 / 3015 - Pinturas, Acabados e Impermeabilización": "3121|3015",
    "🚰 4014 / 4017 / 3018 - Tuberías, Plomería y Sanitarios": "4014|4017|3018",
    "🔧 2711 / 2510 - Herramientas de Mano y Maquinaria": "2711|2510"
}

DEPARTAMENTOS_COLOMBIA = [
    "TODOS", "Amazonas", "Antioquia", "Arauca", "Atlántico", "Bogotá D.C.", "Bolívar",
    "Boyacá", "Caldas", "Caquetá", "Casanare", "Cauca", "Cesar", "Chocó", "Córdoba",
    "Cundinamarca", "Guainía", "Guaviare", "Huila", "La Guajira", "Magdalena", "Meta",
    "Nariño", "Norte de Santander", "Putumayo", "Quindío", "Risaralda", "San Andrés",
    "Santander", "Sucre", "Tolima", "Valle del Cauca", "Vaupés", "Vichada"
]

MODALIDADES_LISTA = [
    "Todas las Modalidades",
    "Mínima Cuantía",
    "Selección Abreviada",
    "Licitación Pública",
    "Concurso de Méritos",
    "Contratación Directa",
    "Régimen Especial"
]

TIPOS_CONTRATO_LISTA = [
    "Todos los Tipos",
    "Obra Pública",
    "Suministro",
    "Interventoría / Consultoría",
    "Compraventa",
    "Prestación de Servicios"
]

ESTADOS_RESUMEN_LISTA = [
    "Todos los Estados",
    "Borrador",
    "Publicado",
    "Presentación de Ofertas",
    "Convocatoria",
    "Evaluación",
    "Adjudicado"
]

FASES_LISTA = [
    "Todas las Fases",
    "Planeación",
    "Selección",
    "Presentación de ofertas",
    "Borrador"
]

# ==============================================================================
# FUNCIONES AUXILIARES: PARSEO, NORMALIZACIÓN Y FORMATOS
# ==============================================================================
def normalizar_texto(texto):
    if not texto or pd.isna(texto):
        return ""
    texto_str = str(texto)
    nfkd = unicodedata.normalize('NFD', texto_str)
    sin_tildes = "".join([c for c in nfkd if unicodedata.category(c) != 'Mn'])
    return sin_tildes.lower().strip()

def formato_pesos_cop(valor):
    try:
        val = float(valor)
        if pd.isna(val) or val == 0:
            return "$ 0 COP"
        return f"$ {val:,.0f} COP".replace(",", ".")
    except Exception:
        return "$ 0 COP"

def limpiar_url_secop(val):
    if pd.isna(val) or not val:
        return ""
    if isinstance(val, dict):
        return str(val.get('url', '')).strip()
    val_str = str(val).strip()
    if val_str.startswith("{") and ("'url':" in val_str or '"url":' in val_str):
        try:
            d = ast.literal_eval(val_str)
            if isinstance(d, dict):
                return str(d.get('url', '')).strip()
        except Exception:
            pass
    if val_str.startswith("http://") or val_str.startswith("https://"):
        return val_str
    return ""

def parsear_fecha_secop(val):
    if pd.isna(val) or not val:
        return pd.NaT, "Por definir"
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ['none', 'nan', 'null', 'nat']:
        return pd.NaT, "Por definir"
    try:
        dt = pd.to_datetime(val_str, errors='coerce')
        if pd.notna(dt):
            if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
                dt = dt.tz_localize(None)
            elif hasattr(dt, 'tz') and dt.tz is not None:
                dt = dt.tz_localize(None)
            return dt, dt.strftime('%Y-%m-%d')
    except Exception:
        pass
    return pd.NaT, val_str[:10] if len(val_str) >= 10 else val_str

# ==============================================================================
# CONEXIÓN Y DESCARGA A SODA API (DATOS.GOV.CO - CONSULTA ABIERTA)
# ==============================================================================
@st.cache_data(ttl=300)
def descargar_secop_2026_abierto(dias_ventana=365, sector_codigo="TODOS", modalidad_sel="Todas las Modalidades", limite=5000):
    """
    Consulta directa a la API SODA del SECOP II en Datos Abiertos.
    NO APLICA FILTROS PREVIOS OBLIGATORIOS por VLAO. Si sector_codigo es 'TODOS',
    recupera la totalidad de la muestra nacional del periodo seleccionado.
    """
    base_url = "https://www.datos.gov.co/resource/p6dx-8zbt.json"
    
    # Estricto Año 2026
    fecha_inicio_2026 = "2026-01-01T00:00:00"
    if dias_ventana != 365:
        f_calculada = (datetime.now() - timedelta(days=dias_ventana)).strftime("%Y-%m-%dT00:00:00")
        if f_calculada > fecha_inicio_2026:
            fecha_inicio_2026 = f_calculada

    select_cols = (
        "referencia_del_proceso,entidad,departamento_entidad,ciudad_entidad,"
        "codigo_principal_de_categoria,nombre_del_procedimiento,descripci_n_del_procedimiento,"
        "precio_base,modalidad_de_contratacion,tipo_de_contrato,estado_resumen,fase,"
        "fecha_de_publicacion_del,fecha_de_ultima_publicaci,fecha_de_recepcion_de,urlproceso"
    )

    condiciones = [f"fecha_de_publicacion_del >= '{fecha_inicio_2026}'"]

    # UNSPSC Filter: Solo se agrega si el usuario eligió un sector específico o portafolio en la Fase 1
    if sector_codigo != "TODOS":
        cods = sector_codigo.split('|')
        sub_c = [f"codigo_principal_de_categoria like '%{c}%'" for c in cods]
        condiciones.append(f"({' OR '.join(sub_c)})")

    # Modalidad Filter: Solo si se especifica
    if "Mínima" in modalidad_sel:
        condiciones.append("(lower(modalidad_de_contratacion) like '%minima%' or lower(modalidad_de_contratacion) like '%mínima%')")
    elif "Abreviada" in modalidad_sel:
        condiciones.append("lower(modalidad_de_contratacion) like '%abreviad%'")
    elif "Licitación" in modalidad_sel:
        condiciones.append("lower(modalidad_de_contratacion) like '%licitac%'")
    elif "Concurso" in modalidad_sel:
        condiciones.append("lower(modalidad_de_contratacion) like '%concurso%'")
    elif "Directa" in modalidad_sel:
        condiciones.append("lower(modalidad_de_contratacion) like '%directa%'")
    elif "Especial" in modalidad_sel:
        condiciones.append("(lower(modalidad_de_contratacion) like '%regimen%' or lower(modalidad_de_contratacion) like '%régimen%')")

    params = {
        "$select": select_cols,
        "$where": " AND ".join(condiciones),
        "$order": "fecha_de_publicacion_del DESC",
        "$limit": str(limite)
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        resp = requests.get(url, headers=headers, timeout=35)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        # Fallback de seguridad sin filtros de sub-categorías
        conds_fb = [f"fecha_de_publicacion_del >= '{fecha_inicio_2026}'"]
        params_fb = {
            "$select": select_cols,
            "$where": " AND ".join(conds_fb),
            "$order": "fecha_de_publicacion_del DESC",
            "$limit": str(limite)
        }
        url_fb = f"{base_url}?{urllib.parse.urlencode(params_fb)}"
        resp = requests.get(url_fb, headers=headers, timeout=35)
        resp.raise_for_status()
        data = resp.json()

    df = pd.DataFrame(data)

    if not df.empty:
        # Clean URLs
        if 'urlproceso' in df.columns:
            df['urlproceso'] = df['urlproceso'].apply(limpiar_url_secop)
        else:
            df['urlproceso'] = ""

        # Precios
        if 'precio_base' in df.columns:
            df['precio_num'] = pd.to_numeric(df['precio_base'], errors='coerce').fillna(0)
            df['precio_formateado'] = df['precio_num'].apply(formato_pesos_cop)
        else:
            df['precio_num'] = 0
            df['precio_formateado'] = "$ 0 COP"

        # Fecha de Publicacion
        if 'fecha_de_publicacion_del' in df.columns:
            res_pub = [parsear_fecha_secop(v) for v in df['fecha_de_publicacion_del']]
            df['fecha_pub_dt'] = [r[0] for r in res_pub]
            df['fecha_pub_clean'] = [r[1] for r in res_pub]
        else:
            df['fecha_pub_dt'] = pd.NaT
            df['fecha_pub_clean'] = "Por definir"

        # Fecha de Ultima Publicacion
        if 'fecha_de_ultima_publicaci' in df.columns:
            res_ult = [parsear_fecha_secop(v) for v in df['fecha_de_ultima_publicaci']]
            df['fecha_ult_pub_clean'] = [r[1] for r in res_ult]
        else:
            df['fecha_ult_pub_clean'] = df['fecha_pub_clean']

        # Fecha Cierre Ofertas
        if 'fecha_de_recepcion_de' in df.columns:
            res_cie = [parsear_fecha_secop(v) for v in df['fecha_de_recepcion_de']]
            df['fecha_cierre_dt'] = [r[0] for r in res_cie]
            df['fecha_cierre_clean'] = [r[1] if r[1] != "Por definir" else "Por definir en pliegos" for r in res_cie]
        else:
            df['fecha_cierre_dt'] = pd.NaT
            df['fecha_cierre_clean'] = "Por definir en pliegos"

    return df

# ==============================================================================
# EXPORTACIÓN SEGURA A EXCEL (OPENPYXL)
# ==============================================================================
def exportar_df_a_excel(df_filtrado):
    df_export = df_filtrado.copy()
    columnas_visibles = {
        'referencia_del_proceso': 'Referencia SECOP II',
        'entidad': 'Entidad Compradora',
        'departamento_entidad': 'Departamento',
        'ciudad_entidad': 'Ciudad / Municipio',
        'codigo_principal_de_categoria': 'Código UNSPSC / Categoría',
        'nombre_del_procedimiento': 'Título convocatoria',
        'descripci_n_del_procedimiento': 'Objeto detallado del contrato',
        'precio_formateado': 'Presupuesto Base ($ COP)',
        'modalidad_de_contratacion': 'Modalidad',
        'tipo_de_contrato': 'Tipo de Contrato',
        'estado_resumen': 'Estado',
        'fase': 'Fase',
        'fecha_pub_clean': 'Fecha Publicación',
        'fecha_ult_pub_clean': 'Última Publicación',
        'fecha_cierre_clean': 'Cierre Ofertas',
        'urlproceso': 'Link SECOP II'
    }
    cols = [c for c in columnas_visibles.keys() if c in df_export.columns]
    df_export = df_export[cols].rename(columns={c: columnas_visibles[c] for c in cols})

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Oportunidades_BID_WIN_VLAO')
    return buffer.getvalue()

# ==============================================================================
# ⚙️ 2. FASE 1: PANTALLA DE INICIO / CONSOLA DE FILTROS DE ENTRADA
# ==============================================================================
st.markdown("### ⚙️ FASE 1: CONSOLA DE FILTROS DE ENTRADA (AÑO 2026)")
st.caption("Configura los parámetros clave para consultar la totalidad de la base nacional o filtrar por criterios específicos.")

with st.form(key="form_filtros_entrada"):
    # Fila 1: Ubicación & Cliente Estatal
    c1, c2, c3 = st.columns([1.2, 1.2, 1.6])
    
    with c1:
        dptos_sel = st.multiselect(
            "📍 Ubicación Geográfica (Departamento):",
            options=[d for d in DEPARTAMENTOS_COLOMBIA if d != "TODOS"],
            default=[],
            help="Selecciona uno o varios departamentos."
        )
    with c2:
        ciudad_query = st.text_input(
            "🏙️ Ciudad / Municipio:",
            value="",
            placeholder="Ej: Bogotá, Neiva, Yopal, Medellín..."
        )
    with c3:
        entidad_query = st.text_input(
            "🏢 Cliente Estatal (Entidad Compradora):",
            value="",
            placeholder="Ej: SENA, ICBF, Registraduría, Ejército, Alcaldía, Hospital..."
        )

    # Fila 2: Definición Jurídica y Contractual
    c4, c5, c6 = st.columns(3)
    with c4:
        modalidad_sel = st.selectbox(
            "📜 Modalidad de Contratación:",
            options=MODALIDADES_LISTA,
            index=0
        )
    with c5:
        tipo_contrato_sel = st.selectbox(
            "📑 Tipo de Contrato:",
            options=TIPOS_CONTRATO_LISTA,
            index=0
        )
    with c6:
        sector_sel = st.selectbox(
            "🏢 Sector / Categoría UNSPSC:",
            options=list(SECTORES_UNSPSC_OPCIONES.keys()),
            index=0
        )

    # Fila 3: Estado, Fase & Ventana de Tiempos
    c7, c8, c9 = st.columns(3)
    with c7:
        estado_sel = st.selectbox(
            "📌 Estado del Proceso (estado_resumen):",
            options=ESTADOS_RESUMEN_LISTA,
            index=0
        )
    with c8:
        fase_sel = st.selectbox(
            "📋 Etapa / Fase SECOP II (fase):",
            options=FASES_LISTA,
            index=0
        )
    with c9:
        ventana_tiempo = st.selectbox(
            "📅 Ventana de Tiempos (Strict 2026):",
            options=[
                "Últimos 30 días",
                "Últimos 60 días",
                "Últimos 90 días",
                "Todo el Año 2026"
            ],
            index=3
        )

    # Fila 4: Criterios Adicionales & Anti-OPS
    c10, c11 = st.columns([2, 1])
    with c10:
        palabra_clave = st.text_input(
            "🔎 Búsqueda Libre por Palabra Clave (en título u objeto):",
            value="",
            placeholder="Ej: cubierta, ferretería, mantenimiento, redes, impermeabilización..."
        )
    with c11:
        st.write("")
        st.write("")
        filtro_anti_ops = st.checkbox(
            "🛡️ Filtro Anti-OPS (Excluir Contratación Directa PN)",
            value=False,
            help="Excluye servicios profesionales individuales de apoyo a la gestión cuando esté marcada."
        )

    st.markdown("---")
    btn_buscar = st.form_submit_button(
        label="🚀 BUSCAR OPORTUNIDADES DE NEGOCIO EN SECOP II",
        use_container_width=True,
        type="primary"
    )

# ==============================================================================
# 📋 3. FASE 2: PANTALLA DE RESULTADOS (MATRIZ DE OPORTUNIDADES)
# ==============================================================================
if btn_buscar or "ejecutado_busqueda" in st.session_state:
    st.session_state["ejecutado_busqueda"] = True

    # Parse Ventana de tiempo
    m_dias = 365
    if "30" in ventana_tiempo:
        m_dias = 30
    elif "60" in ventana_tiempo:
        m_dias = 60
    elif "90" in ventana_tiempo:
        m_dias = 90

    cod_sector = SECTORES_UNSPSC_OPCIONES[sector_sel]

    with st.spinner("🚀 Ejecutando Modelo de Búsqueda de 2 Etapas en SECOP II (2026)..."):
        try:
            df_raw = descargar_secop_2026_abierto(
                dias_ventana=m_dias,
                sector_codigo=cod_sector,
                modalidad_sel=modalidad_sel,
                limite=5000
            )
        except Exception as e:
            st.error(f"Error de conexión con Datos Abiertos: {e}")
            df_raw = pd.DataFrame()

    if not df_raw.empty:
        df = df_raw.copy()

        # 1. Filtro por Departamento
        if dptos_sel and 'departamento_entidad' in df.columns:
            df = df[df['departamento_entidad'].isin(dptos_sel)]

        # 2. Filtro por Ciudad
        if ciudad_query.strip() and 'ciudad_entidad' in df.columns:
            q_m = normalizar_texto(ciudad_query)
            df = df[df['ciudad_entidad'].apply(normalizar_texto).str.contains(q_m)]

        # 3. Filtro por Entidad Compradora
        if entidad_query.strip() and 'entidad' in df.columns:
            q_e = normalizar_texto(entidad_query)
            df = df[df['entidad'].apply(normalizar_texto).str.contains(q_e)]

        # 4. Filtro por Tipo de Contrato
        if tipo_contrato_sel != "Todos los Tipos" and 'tipo_de_contrato' in df.columns:
            q_t = normalizar_texto(tipo_contrato_sel.split(' ')[0])
            df = df[df['tipo_de_contrato'].apply(normalizar_texto).str.contains(q_t[:4])]

        # 5. Filtro por Estado Resumen
        if estado_sel != "Todos los Estados" and 'estado_resumen' in df.columns:
            q_est = normalizar_texto(estado_sel)
            df = df[df['estado_resumen'].apply(normalizar_texto).str.contains(q_est[:5])]

        # 6. Filtro por Fase
        if fase_sel != "Todas las Fases" and 'fase' in df.columns:
            q_fase = normalizar_texto(fase_sel)
            df = df[df['fase'].apply(normalizar_texto).str.contains(q_fase[:4])]

        # 7. Filtro Anti-OPS
        if filtro_anti_ops and 'modalidad_de_contratacion' in df.columns and 'nombre_del_procedimiento' in df.columns:
            palabras_ops = ['prestacion de servicios', 'honorarios', 'apoyo a la gestion', 'persona natural', 'ops']
            def es_ops(row):
                mod = str(row.get('modalidad_de_contratacion', '')).lower()
                nom = normalizar_texto(row.get('nombre_del_procedimiento', ''))
                if 'directa' in mod:
                    if any(p in nom for p in palabras_ops):
                        return True
                return False
            df = df[~df.apply(es_ops, axis=1)]

        # 8. Filtro por Palabra Clave Libre
        if palabra_clave.strip():
            kw_norm = normalizar_texto(palabra_clave)
            df = df[
                df['nombre_del_procedimiento'].apply(normalizar_texto).str.contains(kw_norm) |
                df['descripci_n_del_procedimiento'].apply(normalizar_texto).str.contains(kw_norm)
            ]

        # ----------------------------------------------------------------------
        # A. MÉTRICAS RÁPIDAS SUPERIORES
        # ----------------------------------------------------------------------
        st.markdown("### 📊 FASE 2: MATRIZ DE RESULTADOS Y OPORTUNIDADES")
        
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric(
                label="🎯 Total Licitaciones Encontradas",
                value=f"{len(df):,} procesos"
            )
        with m2:
            bolsa_tot = df['precio_num'].sum() if 'precio_num' in df.columns else 0
            st.metric(
                label="💰 Bolsa Presupuestada Acumulada",
                value=formato_pesos_cop(bolsa_tot)
            )
        with m3:
            if 'departamento_entidad' in df.columns and not df.empty:
                dpto_lider = df['departamento_entidad'].mode()[0] if not df['departamento_entidad'].mode().empty else "N/I"
                cant_lider = (df['departamento_entidad'] == dpto_lider).sum()
                st.metric(
                    label="📍 Ubicación Líder en Publicaciones",
                    value=f"{dpto_lider}",
                    delta=f"{cant_lider} licitaciones"
                )
            else:
                st.metric(label="📍 Ubicación Líder", value="Por determinar")

        st.divider()

        # ----------------------------------------------------------------------
        # VISUALIZACIÓN EN TARJETAS ESTRELLA (TOP OPORTUNIDADES)
        # ----------------------------------------------------------------------
        if not df.empty:
            st.markdown("#### ⭐ Oportunidades Destacadas (Resumen Visual)")
            df_cards = df.sort_values(by=['precio_num'], ascending=False).head(5)
            
            for idx, row in df_cards.iterrows():
                with st.container():
                    st.markdown(f"""
                    <div class="opportunity-card">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span class="card-title">🏢 {row.get('entidad', 'Entidad Estatal')}</span>
                            <span class="card-badge">💰 {row.get('precio_formateado', '$ 0 COP')}</span>
                        </div>
                        <div style="margin-top:10px; font-size:1.02rem; color:#1E293B;">
                            <b>Objeto:</b> {row.get('nombre_del_procedimiento', 'Sin especificación')}
                        </div>
                        <div style="margin-top:8px; font-size:0.88rem; color:#475569;">
                            📍 <b>Ubicación:</b> {row.get('ciudad_entidad', 'N/I')}, {row.get('departamento_entidad', 'N/I')} | 
                            📜 <b>Modalidad:</b> {row.get('modalidad_de_contratacion', 'N/I')} | 
                            <span class="phase-badge">📌 {row.get('fase', 'N/I')}</span> | 
                            ⏱️ <b>Cierre Ofertas:</b> {row.get('fecha_cierre_clean', 'Por definir')}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    link_p = row.get('urlproceso', '')
                    if link_p:
                        st.markdown(f"🔗 [**Ver Pliegos en SECOP II 🔗**]({link_p})")
                    st.divider()

        # ----------------------------------------------------------------------
        # B. TABLA DE RESULTADOS (st.dataframe)
        # ----------------------------------------------------------------------
        st.markdown(f"#### 📋 Matriz Operativa de Oportunidades ({len(df)} Registros)")
        
        columnas_matriz = {
            'referencia_del_proceso': 'Referencia SECOP II',
            'entidad': 'Entidad Compradora',
            'ciudad_entidad': 'Ciudad / Municipio',
            'codigo_principal_de_categoria': 'Código UNSPSC / Categoría',
            'nombre_del_procedimiento': 'Título convocatoria',
            'descripci_n_del_procedimiento': 'Objeto detallado del contrato',
            'precio_formateado': 'Presupuesto Base ($ COP)',
            'fecha_pub_clean': 'Fecha Publicación',
            'fecha_ult_pub_clean': 'Fecha Última Publicación',
            'fecha_cierre_clean': 'Fecha Cierre Ofertas',
            'urlproceso': 'Link SECOP II'
        }

        cols_presentes = [c for c in columnas_matriz.keys() if c in df.columns]
        df_matriz = df[cols_presentes].rename(columns={c: columnas_matriz[c] for c in cols_presentes})

        st.dataframe(
            df_matriz,
            use_container_width=True,
            column_config={
                "Link SECOP II": st.column_config.LinkColumn(
                    "Link SECOP II",
                    help="Abrir la licitación directamente en la plataforma de Colombia Compra Eficiente",
                    display_text="Ver Pliegos en SECOP II 🔗"
                )
            }
        )

        # Botón de exportación a Excel
        st.markdown("---")
        excel_bytes = exportar_df_a_excel(df)
        st.download_button(
            label="📥 Exportar Matriz Completa a Excel (.xlsx)",
            data=excel_bytes,
            file_name=f"bid_win_vlao_matriz_2026_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    else:
        st.warning("⚠️ No se encontraron oportunidades que coincidan con la combinación de filtros ingresada. Intenta ampliar los criterios o seleccionar 'Todas las Modalidades'.")
