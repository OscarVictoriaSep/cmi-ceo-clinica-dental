"""
DASHBOARD CMI — CEO CLÍNICA DENTAL SANTIAGO
Versión: 1.0 | Julio 2026
Dashboard Streamlit conectado a Supabase
"""

import os
import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime

# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="CMI — CEO Clínica Dental",
    page_icon="🦷",
    layout="wide",
    initial_sidebar_state="expanded"
)

SUPABASE_URL = os.environ.get("SUPABASE_URL", st.secrets.get("SUPABASE_URL",""))
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", st.secrets.get("SUPABASE_ANON_KEY",""))

MESES = {1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",
         7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"}

# Colores marca CEO
COLOR_BG = "#000000"
COLOR_WHITE = "#FFFFFF"
COLOR_GRAY = "#E3E3E3"
COLOR_GREEN = "#28A745"
COLOR_YELLOW = "#FFC107"
COLOR_RED = "#DC3545"
COLOR_BLUE = "#0D47A1"

# ============================================================
# CONEXIÓN SUPABASE
# ============================================================

@st.cache_resource
def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

@st.cache_data(ttl=300)
def cargar_periodos():
    sb = get_supabase()
    resp = sb.table("periodos").select("*").order("anio", desc=True).order("mes", desc=True).execute()
    return resp.data

@st.cache_data(ttl=300)
def cargar_kpis(anio, mes):
    sb = get_supabase()
    resp = sb.table("kpis").select("*").eq("anio", anio).eq("mes", mes).execute()
    return resp.data

@st.cache_data(ttl=300)
def cargar_kpis_anterior(anio, mes):
    mes_ant = mes - 1 if mes > 1 else 12
    anio_ant = anio if mes > 1 else anio - 1
    sb = get_supabase()
    resp = sb.table("kpis").select("*").eq("anio", anio_ant).eq("mes", mes_ant).execute()
    return resp.data

@st.cache_data(ttl=300)
def cargar_doctores(anio, mes):
    sb = get_supabase()
    resp = sb.table("kpi_doctores").select("*").eq("anio", anio).eq("mes", mes).execute()
    return resp.data

@st.cache_data(ttl=300)
def cargar_mix(anio, mes):
    sb = get_supabase()
    resp = sb.table("kpi_mix_categorias").select("*").eq("anio", anio).eq("mes", mes).execute()
    return resp.data

@st.cache_data(ttl=300)
def cargar_club(anio, mes):
    sb = get_supabase()
    resp = sb.table("kpi_club_sonrisa").select("*").eq("anio", anio).eq("mes", mes).execute()
    return resp.data[0] if resp.data else {}

@st.cache_data(ttl=300)
def cargar_trazabilidad(anio, mes):
    sb = get_supabase()
    resp = sb.table("kpi_trazabilidad").select("*").eq("anio", anio).eq("mes", mes).execute()
    return resp.data

@st.cache_data(ttl=300)
def cargar_presupuesto(anio, mes):
    sb = get_supabase()
    resp = sb.table("presupuesto_anual").select("*").eq("anio", anio).eq("mes", mes).execute()
    return resp.data[0] if resp.data else {}

@st.cache_data(ttl=300)
def cargar_historico_kpis(anio, mes, kpi_id, n_meses=6):
    sb = get_supabase()
    registros = []
    mes_actual = mes
    anio_actual = anio
    for _ in range(n_meses):
        resp = sb.table("kpis").select("anio,mes,valor,estado").eq("anio", anio_actual).eq("mes", mes_actual).eq("kpi_id", kpi_id).execute()
        if resp.data:
            r = resp.data[0]
            r["periodo"] = f"{MESES.get(r['mes'],r['mes'])[:3]} {r['anio']}"
            registros.append(r)
        mes_actual -= 1
        if mes_actual == 0:
            mes_actual = 12
            anio_actual -= 1
    return list(reversed(registros))

# ============================================================
# UTILIDADES UI
# ============================================================

def fmt_clp(valor):
    if valor is None:
        return "N/D"
    return f"${valor:,.0f}".replace(",",".")

def fmt_pct(valor):
    if valor is None:
        return "N/D"
    return f"{valor:.1f}%"

def color_estado(estado):
    if estado == "✅":
        return COLOR_GREEN
    elif estado == "🟡":
        return COLOR_YELLOW
    elif estado == "🔴":
        return COLOR_RED
    return "#888888"

def kpi_card(titulo, valor, objetivo, unidad, estado, nota=None, delta=None):
    color = color_estado(estado)
    delta_html = ""
    if delta is not None:
        delta_color = COLOR_GREEN if delta >= 0 else COLOR_RED
        delta_symbol = "▲" if delta >= 0 else "▼"
        delta_html = f'<span style="color:{delta_color};font-size:12px">{delta_symbol} {abs(delta):.1f}%</span>'

    nota_html = f'<div style="color:#888;font-size:11px;margin-top:4px">{nota}</div>' if nota else ""

    st.markdown(f"""
    <div style="background:#1a1a1a;border-left:4px solid {color};
                padding:16px;border-radius:8px;margin-bottom:8px">
        <div style="color:#aaa;font-size:11px;text-transform:uppercase;letter-spacing:1px">{titulo}</div>
        <div style="color:{COLOR_WHITE};font-size:28px;font-weight:700;margin:4px 0">
            {valor} <span style="font-size:14px;color:#aaa">{unidad}</span>
            {delta_html}
        </div>
        <div style="color:{color};font-size:13px">{estado} Objetivo: {objetivo}</div>
        {nota_html}
    </div>
    """, unsafe_allow_html=True)

def seccion_header(titulo, color):
    st.markdown(f"""
    <div style="background:{color};color:white;padding:10px 16px;
                border-radius:6px;margin:20px 0 10px 0;font-weight:700;font-size:16px">
        {titulo}
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# CSS GLOBAL
# ============================================================

st.markdown("""
<style>
    .stApp { background-color: #0a0a0a; }
    .stApp > header { background-color: #000000; }
    div[data-testid="metric-container"] { background: #1a1a1a; padding: 12px; border-radius: 8px; }
    .stSelectbox > div > div { background: #1a1a1a; color: white; }
    .stDataFrame { background: #1a1a1a; }
    h1, h2, h3 { color: #ffffff; }
    .stMarkdown { color: #e0e0e0; }
    [data-testid="stSidebar"] { background: #111111; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# LAYOUT PRINCIPAL
# ============================================================

# Header
st.markdown("""
<div style="background:#000;padding:20px;border-bottom:2px solid #333;margin-bottom:20px">
    <h1 style="color:white;margin:0;font-size:24px">🦷 CEO Clínica Dental — Cuadro de Mando Integral</h1>
    <p style="color:#aaa;margin:4px 0 0 0;font-size:13px">Centro de Especialidades Odontológicas Santiago SpA</p>
</div>
""", unsafe_allow_html=True)

# Sidebar — Selección de período
with st.sidebar:
    st.markdown("### 📅 Período")
    periodos = cargar_periodos()

    if not periodos:
        st.error("No hay datos cargados. Ejecuta el importador primero.")
        st.stop()

    opciones = [f"{MESES.get(p['mes'],p['mes'])} {p['anio']}" for p in periodos]
    seleccion = st.selectbox("Seleccionar mes:", opciones)

    idx = opciones.index(seleccion)
    periodo_sel = periodos[idx]
    anio_sel = periodo_sel["anio"]
    mes_sel = periodo_sel["mes"]

    st.markdown(f"**Procesado:** {periodo_sel.get('fecha_procesado','')[:10]}")
    st.markdown("---")
    st.markdown("### 🔍 Navegación")
    vista = st.radio("Ver sección:", [
        "📊 Resumen General",
        "💼 Comercial",
        "⚙️ Operación",
        "📋 Mix de Servicios",
        "👨‍⚕️ Doctores",
        "💰 Financiero",
        "🌟 Programas Comerciales",
    ])

# Cargar datos
kpis = cargar_kpis(anio_sel, mes_sel)
kpis_ant = cargar_kpis_anterior(anio_sel, mes_sel)
presupuesto = cargar_presupuesto(anio_sel, mes_sel)

def get_kpi(kpi_id):
    for k in kpis:
        if k["kpi_id"] == kpi_id:
            return k
    return {}

def get_kpi_ant(kpi_id):
    for k in kpis_ant:
        if k["kpi_id"] == kpi_id:
            return k
    return {}

def delta_vs_anterior(kpi_id):
    actual = get_kpi(kpi_id)
    anterior = get_kpi_ant(kpi_id)
    if actual.get("valor") and anterior.get("valor") and anterior["valor"] != 0:
        return ((actual["valor"] - anterior["valor"]) / abs(anterior["valor"])) * 100
    return None

# ============================================================
# VISTA: RESUMEN GENERAL
# ============================================================

if vista == "📊 Resumen General":
    st.markdown(f"## Resumen — {MESES.get(mes_sel,'')} {anio_sel}")

    # Semáforo general
    total_kpis = len(kpis)
    verdes = sum(1 for k in kpis if k.get("estado") == "✅")
    rojos = sum(1 for k in kpis if k.get("estado") == "🔴")
    amarillos = sum(1 for k in kpis if k.get("estado") == "🟡")
    info = sum(1 for k in kpis if k.get("estado") in ["ℹ️","⚠️","⏳"])

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""<div style="background:#1a3a1a;border:1px solid #28a745;padding:16px;
            border-radius:8px;text-align:center">
            <div style="color:#28a745;font-size:32px;font-weight:700">{verdes}</div>
            <div style="color:#aaa;font-size:12px">KPIs en ✅ verde</div></div>""",
            unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div style="background:#3a1a1a;border:1px solid #dc3545;padding:16px;
            border-radius:8px;text-align:center">
            <div style="color:#dc3545;font-size:32px;font-weight:700">{rojos}</div>
            <div style="color:#aaa;font-size:12px">KPIs en 🔴 rojo</div></div>""",
            unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div style="background:#3a2a00;border:1px solid #ffc107;padding:16px;
            border-radius:8px;text-align:center">
            <div style="color:#ffc107;font-size:32px;font-weight:700">{amarillos}</div>
            <div style="color:#aaa;font-size:12px">KPIs en 🟡 alerta</div></div>""",
            unsafe_allow_html=True)
    with col4:
        st.markdown(f"""<div style="background:#1a1a2a;border:1px solid #4a90d9;padding:16px;
            border-radius:8px;text-align:center">
            <div style="color:#4a90d9;font-size:32px;font-weight:700">{total_kpis}</div>
            <div style="color:#aaa;font-size:12px">KPIs totales</div></div>""",
            unsafe_allow_html=True)

    st.markdown("---")

    # KPIs críticos del mes
    st.markdown("### KPIs Críticos")

    # Financiero
    col1, col2, col3 = st.columns(3)
    ppto = presupuesto.get("ventas", 0)
    k18 = get_kpi("18")
    ing_real = k18.get("valor", 0) or 0
    cumpl = (ing_real / ppto * 100) if ppto > 0 else 0
    estado18 = "✅" if cumpl >= 100 else ("🟡" if cumpl >= 90 else "🔴")

    with col1:
        kpi_card("Facturación vs Presupuesto",
                 fmt_pct(cumpl), "≥100%", "", estado18,
                 nota=f"{fmt_clp(ing_real)} / {fmt_clp(ppto)}",
                 delta=delta_vs_anterior("18"))

    k19 = get_kpi("19")
    margen = k19.get("valor")
    obj_margen = presupuesto.get("margen_pct")
    estado19 = "✅" if (margen and obj_margen and margen >= obj_margen) else "🔴"
    with col2:
        kpi_card("Margen Operacional",
                 fmt_pct(margen), fmt_pct(obj_margen), "", estado19,
                 nota="Objetivo según presupuesto mensual")

    k1 = get_kpi("1")
    with col3:
        kpi_card("Tasa Cierre Presupuestos",
                 fmt_pct(k1.get("valor")), "≥70%", "",
                 k1.get("estado","⚠️"),
                 delta=delta_vs_anterior("1"))

    col1, col2, col3 = st.columns(3)
    k10a = get_kpi("10a")
    with col1:
        kpi_card("Atenciones Totales",
                 str(int(k10a.get("valor",0) or 0)), "≥487", "atenciones",
                 k10a.get("estado","⚠️"),
                 delta=delta_vs_anterior("10a"))

    k8 = get_kpi("8")
    with col2:
        kpi_card("Ingresos por Atención",
                 fmt_clp(k8.get("valor")), "≥$45.000", "",
                 k8.get("estado","⚠️"),
                 delta=delta_vs_anterior("8"))

    kT = get_kpi("T")
    with col3:
        kpi_card("Trazabilidad de Origen",
                 fmt_pct(kT.get("valor")), "≥90%", "",
                 kT.get("estado","⚠️"),
                 nota="Prerequisito para CPA y ROAS")

    # Tabla resumen todos los KPIs
    st.markdown("---")
    st.markdown("### Tabla de KPIs")

    filas = []
    for k in kpis:
        if k.get("valor") is not None:
            val_fmt = fmt_clp(k["valor"]) if k.get("unidad") == "CLP" else fmt_pct(k["valor"]) if k.get("unidad") == "%" else str(int(k["valor"]))
        else:
            val_fmt = k.get("valor_texto", "N/D")

        obj_fmt = k.get("objetivo_texto") or (fmt_clp(k["objetivo"]) if k.get("unidad") == "CLP" and k.get("objetivo") else fmt_pct(k["objetivo"]) if k.get("unidad") == "%" and k.get("objetivo") else str(k.get("objetivo","—")))

        filas.append({
            "Estado": k.get("estado","—"),
            "KPI": k.get("kpi_nombre",""),
            "Sección": k.get("seccion",""),
            "Resultado": val_fmt,
            "Objetivo": obj_fmt,
        })

    if filas:
        df = pd.DataFrame(filas)
        st.dataframe(df, use_container_width=True, hide_index=True,
                     column_config={"Estado": st.column_config.TextColumn(width="small")})

# ============================================================
# VISTA: COMERCIAL
# ============================================================

elif vista == "💼 Comercial":
    st.markdown(f"## Comercial — {MESES.get(mes_sel,'')} {anio_sel}")

    seccion_header("📋 Presupuestos", COLOR_BLUE)
    col1, col2, col3 = st.columns(3)
    k1 = get_kpi("1")
    k2 = get_kpi("2")
    k3 = get_kpi("3")
    with col1:
        kpi_card("Tasa Cierre", fmt_pct(k1.get("valor")), "≥70%", "", k1.get("estado","⚠️"), delta=delta_vs_anterior("1"))
    with col2:
        kpi_card("Presupuestos Generados", str(int(k2.get("valor",0) or 0)), "≥230", "unidades", k2.get("estado","⚠️"))
    with col3:
        kpi_card("Captación Seguimiento", fmt_pct(k3.get("valor")), "≥20%", "", k3.get("estado","⚠️"))

    seccion_header("📡 Publicidad Digital", COLOR_BLUE)
    kT = get_kpi("T")
    st.markdown(f"""
    <div style="background:#1a1a1a;padding:12px;border-radius:8px;margin-bottom:12px">
        <span style="color:#aaa;font-size:12px">TRAZABILIDAD DE ORIGEN </span>
        <span style="color:{'#28a745' if kT.get('estado')=='✅' else '#dc3545'};font-size:18px;font-weight:700">
            {fmt_pct(kT.get('valor'))} {kT.get('estado','')}</span>
        <span style="color:#888;font-size:12px"> (objetivo ≥90% para validar CPA y ROAS)</span>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    k4 = get_kpi("4")
    k5 = get_kpi("5")
    k6 = get_kpi("6")
    k7 = get_kpi("7")

    with col1:
        st.markdown("**Meta Ads**")
        kpi_card("CPA Meta Ads", k4.get("valor_texto") or fmt_clp(k4.get("valor")), "Por definir", "", k4.get("estado","⚠️"), nota=k4.get("nota"))
        kpi_card("ROAS Meta Ads", f"{k6.get('valor','N/D')}x" if k6.get('valor') else "N/D", "≥3,5x", "", k6.get("estado","⚠️"), nota="Piso mensual — ROAS real considera LTV")
    with col2:
        st.markdown("**Google Ads**")
        kpi_card("CPA Google Ads", k5.get("valor_texto") or fmt_clp(k5.get("valor")), "Por definir", "", k5.get("estado","⚠️"), nota=k5.get("nota"))
        kpi_card("ROAS Google Ads", f"{k7.get('valor','N/D')}x" if k7.get('valor') else "N/D", "≥3,5x", "", k7.get("estado","⚠️"), nota="Piso mensual — ROAS real considera LTV")

    # Tabla trazabilidad
    traz = cargar_trazabilidad(anio_sel, mes_sel)
    if traz:
        st.markdown("#### Detalle por Canal")
        df_t = pd.DataFrame(traz)
        cols = ["canal","pacientes","ingresos","inversion","cpa","roas"]
        cols_ex = [c for c in cols if c in df_t.columns]
        st.dataframe(df_t[cols_ex], use_container_width=True, hide_index=True)

# ============================================================
# VISTA: OPERACIÓN
# ============================================================

elif vista == "⚙️ Operación":
    st.markdown(f"## Operación — {MESES.get(mes_sel,'')} {anio_sel}")

    col1, col2 = st.columns(2)
    k8 = get_kpi("8")
    k9 = get_kpi("9")
    k10a = get_kpi("10a")
    k10b = get_kpi("10b")
    k11 = get_kpi("11")

    with col1:
        kpi_card("Ingresos por Atención", fmt_clp(k8.get("valor")), "≥$45.000", "", k8.get("estado","⚠️"), delta=delta_vs_anterior("8"))
        kpi_card("Atenciones Totales", str(int(k10a.get("valor",0) or 0)), "≥487", "atenciones", k10a.get("estado","⚠️"), delta=delta_vs_anterior("10a"))
        kpi_card("Producción por Sillón", fmt_clp(k11.get("valor")), "≥$10.986.906", "", k11.get("estado","⚠️"))
    with col2:
        kpi_card("Asistencia a Citas", fmt_pct(k9.get("valor")), "≥80%", "", k9.get("estado","⚠️"), delta=delta_vs_anterior("9"))
        kpi_card("Pacientes Únicos", str(int(k10b.get("valor",0) or 0)), "≥415", "pacientes", k10b.get("estado","⚠️"))

    # Tendencia atenciones
    hist = cargar_historico_kpis(anio_sel, mes_sel, "10a", n_meses=6)
    if hist:
        st.markdown("#### Tendencia Atenciones (6 meses)")
        df_hist = pd.DataFrame(hist)
        if "valor" in df_hist.columns and "periodo" in df_hist.columns:
            st.bar_chart(df_hist.set_index("periodo")["valor"])

# ============================================================
# VISTA: MIX DE SERVICIOS
# ============================================================

elif vista == "📋 Mix de Servicios":
    st.markdown(f"## Mix de Servicios — {MESES.get(mes_sel,'')} {anio_sel}")

    mix = cargar_mix(anio_sel, mes_sel)
    k13 = get_kpi("13")
    k14 = get_kpi("14")

    col1, col2 = st.columns(2)
    with col1:
        kpi_card("Casos Nuevos Ortodoncia", str(int(k13.get("valor",0) or 0)), "≥12", "casos", k13.get("estado","⚠️"))
    with col2:
        kpi_card("Casos Nuevos Implantes", str(int(k14.get("valor",0) or 0)), "≥11", "casos", k14.get("estado","⚠️"))

    if mix:
        st.markdown("#### Facturación por Categoría")
        df_mix = pd.DataFrame(mix)
        df_mix = df_mix.sort_values("ingresos", ascending=False)

        if "categoria" in df_mix.columns and "ingresos" in df_mix.columns:
            cols_show = ["categoria","ingresos","pct_real","pct_historico"]
            cols_ex = [c for c in cols_show if c in df_mix.columns]
            df_show = df_mix[cols_ex].copy()
            df_show.columns = ["Categoría","Ingresos ($)","% Real","% Histórico"]
            st.dataframe(df_show, use_container_width=True, hide_index=True,
                         column_config={
                             "Ingresos ($)": st.column_config.NumberColumn(format="$%d"),
                             "% Real": st.column_config.NumberColumn(format="%.1f%%"),
                             "% Histórico": st.column_config.NumberColumn(format="%.1f%%"),
                         })

            st.bar_chart(df_mix.set_index("categoria")["ingresos"])

# ============================================================
# VISTA: DOCTORES
# ============================================================

elif vista == "👨‍⚕️ Doctores":
    st.markdown(f"## Doctores — {MESES.get(mes_sel,'')} {anio_sel}")
    doctores = cargar_doctores(anio_sel, mes_sel)
    ppto_mes = presupuesto.get("ventas", 0)

    if doctores:
        # Tasa de Cierre
        seccion_header("Tasa de Cierre por Doctor", "#E65100")
        filas_tc = []
        for d in sorted(doctores, key=lambda x: -(x.get("presupuestos_generados") or 0)):
            tasa = d.get("tasa_cierre")
            obj = d.get("objetivo_tasa_cierre", 70)
            estado = "✅" if (tasa and obj and tasa >= obj) else "🔴" if tasa is not None else "—"
            filas_tc.append({
                "Estado": estado,
                "Doctor": d["doctor"].title(),
                "Especialidad": d.get("especialidad",""),
                "Generados": d.get("presupuestos_generados", 0),
                "Capturados": d.get("presupuestos_capturados", 0),
                "Tasa Cierre": f"{tasa:.1f}%" if tasa else "N/D",
                "Objetivo": f"{obj:.0f}%",
            })
        st.dataframe(pd.DataFrame(filas_tc), use_container_width=True, hide_index=True)

        # Productividad
        seccion_header("Productividad por Doctor", "#E65100")
        filas_prod = []
        for d in sorted(doctores, key=lambda x: -(x.get("ingresos") or 0)):
            ing = d.get("ingresos", 0) or 0
            pct = d.get("pct_historico", 0) or 0
            obj_ing = ppto_mes * pct / 100 if ppto_mes and pct else None
            cumpl = (ing / obj_ing * 100) if obj_ing and obj_ing > 0 else None
            estado = "✅" if (cumpl and cumpl >= 90) else "🔴" if cumpl is not None else "—"
            filas_prod.append({
                "Estado": estado,
                "Doctor": d["doctor"].title(),
                "Especialidad": d.get("especialidad",""),
                "Ingresos": ing,
                "Objetivo": obj_ing,
                "Cumplimiento": f"{cumpl:.1f}%" if cumpl else "N/D",
            })
        st.dataframe(pd.DataFrame(filas_prod), use_container_width=True, hide_index=True,
                     column_config={
                         "Ingresos": st.column_config.NumberColumn(format="$%d"),
                         "Objetivo": st.column_config.NumberColumn(format="$%d"),
                     })
    else:
        st.info("No hay datos de doctores para este período.")

# ============================================================
# VISTA: FINANCIERO
# ============================================================

elif vista == "💰 Financiero":
    st.markdown(f"## Financiero — {MESES.get(mes_sel,'')} {anio_sel}")

    k18 = get_kpi("18")
    k19 = get_kpi("19")
    k20 = get_kpi("20")
    ppto = presupuesto.get("ventas", 0)
    ppto_res = presupuesto.get("resultado_operacional", 0)
    ppto_margen = presupuesto.get("margen_pct", 0)

    ing_real = k18.get("valor", 0) or 0
    cumpl18 = (ing_real / ppto * 100) if ppto > 0 else 0
    estado18 = "✅" if cumpl18 >= 100 else ("🟡" if cumpl18 >= 90 else "🔴")

    col1, col2, col3 = st.columns(3)
    with col1:
        kpi_card("Facturación Real", fmt_clp(ing_real),
                 f"≥{fmt_clp(ppto)}", "", estado18,
                 nota=f"Cumplimiento: {cumpl18:.1f}%")
    with col2:
        margen = k19.get("valor")
        estado19 = "✅" if (margen and ppto_margen and margen >= ppto_margen) else "🔴"
        kpi_card("Margen Operacional", fmt_pct(margen),
                 f"≥{fmt_pct(ppto_margen)}", "", estado19,
                 nota=f"Objetivo presupuesto: {fmt_pct(ppto_margen)}")
    with col3:
        kpi20_ant = get_kpi_ant("18")
        ing_ant = kpi20_ant.get("valor", 0) or 0
        var = ((ing_real - ing_ant) / abs(ing_ant) * 100) if ing_ant != 0 else None
        if var is None:
            estado20 = "⚠️"
        elif var >= -5:
            estado20 = "✅"
        elif var >= -15:
            estado20 = "🟡"
        else:
            estado20 = "🔴"
        kpi_card("Variación vs Mes Anterior",
                 fmt_pct(var) if var is not None else "N/D",
                 "Verde ≥-5%", "", estado20,
                 nota=f"Mes anterior: {fmt_clp(ing_ant)}")

    # Presupuesto anual
    st.markdown("---")
    st.markdown("#### Presupuesto 2026 — Resumen Anual")
    sb = get_supabase()
    resp_ppto = sb.table("presupuesto_anual").select("*").eq("anio", anio_sel).order("mes").execute()
    if resp_ppto.data:
        df_ppto = pd.DataFrame(resp_ppto.data)
        df_ppto["Mes"] = df_ppto["mes"].map(MESES)
        df_ppto = df_ppto[["Mes","ventas","resultado_operacional","margen_pct"]]
        df_ppto.columns = ["Mes","Ventas ($)","Resultado ($)","Margen %"]
        st.dataframe(df_ppto, use_container_width=True, hide_index=True,
                     column_config={
                         "Ventas ($)": st.column_config.NumberColumn(format="$%d"),
                         "Resultado ($)": st.column_config.NumberColumn(format="$%d"),
                         "Margen %": st.column_config.NumberColumn(format="%.1f%%"),
                     })

# ============================================================
# VISTA: PROGRAMAS COMERCIALES
# ============================================================

elif vista == "🌟 Programas Comerciales":
    st.markdown(f"## Programas Comerciales — {MESES.get(mes_sel,'')} {anio_sel}")

    club = cargar_club(anio_sel, mes_sel)
    k21a = get_kpi("21a")
    k21b = get_kpi("21b")
    k21c = get_kpi("21c")
    k22 = get_kpi("22")
    k23 = get_kpi("23")

    seccion_header("🌟 Club Sonrisa CEO", "#006064")

    col1, col2, col3 = st.columns(3)
    with col1:
        kpi_card("Ingresos Club Sonrisa", fmt_clp(k21a.get("valor")), "≥$17.849.110", "", k21a.get("estado","⚠️"),
                 nota=k21a.get("nota"))
    with col2:
        kpi_card("Tasa de Afiliación", fmt_pct(k21b.get("valor")), "≥70%", "", k21b.get("estado","⚠️"),
                 nota=k21b.get("nota"))
    with col3:
        kpi_card("Tasa de Retorno (6 meses)", fmt_pct(k21c.get("valor")), "≥60%", "", k21c.get("estado","⚠️"))

    # Segmentación retorno
    if club:
        st.markdown("#### Segmentación de Socios")
        total = club.get("total_socios", 0)
        retorno = club.get("socios_retorno", 0)
        proceso = club.get("socios_en_proceso", 0)
        sin_act = club.get("socios_sin_actividad", 0)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""<div style="background:#1a3a1a;border:1px solid #28a745;padding:16px;border-radius:8px;text-align:center">
                <div style="color:#28a745;font-size:28px;font-weight:700">{retorno}</div>
                <div style="color:#aaa;font-size:12px">✅ Con retorno (≥2 tratamientos)</div>
                <div style="color:#28a745;font-size:16px">{(retorno/total*100):.1f}%</div></div>""",
                unsafe_allow_html=True)
        with col2:
            st.markdown(f"""<div style="background:#3a2a00;border:1px solid #ffc107;padding:16px;border-radius:8px;text-align:center">
                <div style="color:#ffc107;font-size:28px;font-weight:700">{proceso}</div>
                <div style="color:#aaa;font-size:12px">🟡 En proceso (1 tratamiento)</div>
                <div style="color:#ffc107;font-size:16px">{(proceso/total*100):.1f}%</div></div>""",
                unsafe_allow_html=True)
        with col3:
            st.markdown(f"""<div style="background:#3a1a1a;border:1px solid #dc3545;padding:16px;border-radius:8px;text-align:center">
                <div style="color:#dc3545;font-size:28px;font-weight:700">{sin_act}</div>
                <div style="color:#aaa;font-size:12px">🔴 Sin actividad (0 tratamientos)</div>
                <div style="color:#dc3545;font-size:16px">{(sin_act/total*100):.1f}%</div></div>""",
                unsafe_allow_html=True)

        # Ingresos separados
        st.markdown("#### Ingresos Club Sonrisa — Ortodoncia vs Otros")
        col1, col2 = st.columns(2)
        with col1:
            ing_otros = club.get("ingresos_otros", 0)
            estado_otros = "✅" if ing_otros >= 12754839 else "🔴"
            kpi_card("Otros Tratamientos (efecto real)", fmt_clp(ing_otros), "≥$12.754.839", "", estado_otros,
                     nota="Mide el impacto real del programa de fidelización")
        with col2:
            ing_orto = club.get("ingresos_ortodoncia", 0)
            estado_orto = "✅" if ing_orto >= 5094270 else "🔴"
            kpi_card("Ortodoncia (referencial)", fmt_clp(ing_orto), "≥$5.094.270", "", estado_orto,
                     nota="Atenciones recurrentes por tratamiento activo")

    seccion_header("🤝 Recomienda CEO", "#006064")
    col1, col2 = st.columns(2)
    with col1:
        kpi_card("Pacientes Referidos", str(int(k22.get("valor",0) or 0)), "≥3", "pacientes/mes", k22.get("estado","⚠️"),
                 nota="Programa lanzado junio 2026")
    with col2:
        kpi_card("Ingresos Atribuidos", fmt_clp(k23.get("valor")), "≥$600.000/mes", "", k23.get("estado","⚠️"),
                 nota=f"Objetivo anual: $7.500.000")

# Footer
st.markdown("---")
st.markdown(f"""
<div style="color:#444;font-size:11px;text-align:center">
    CMI CEO Clínica Dental Santiago SpA | Actualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}
</div>
""", unsafe_allow_html=True)
