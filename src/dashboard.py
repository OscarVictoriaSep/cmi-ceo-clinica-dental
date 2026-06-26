"""
DASHBOARD CMI — CEO CLÍNICA DENTAL SANTIAGO
Versión: 2.0 | Julio 2026
"""

import os
import streamlit as st
import pandas as pd
from supabase import create_client, Client

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

@st.cache_resource
def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

@st.cache_data(ttl=300)
def cargar_periodos():
    sb = get_supabase()
    return sb.table("periodos").select("*").order("anio",desc=True).order("mes",desc=True).execute().data

@st.cache_data(ttl=300)
def cargar_kpis(anio, mes):
    sb = get_supabase()
    return sb.table("kpis").select("*").eq("anio",anio).eq("mes",mes).execute().data

@st.cache_data(ttl=300)
def cargar_kpis_anterior(anio, mes):
    m = mes-1 if mes>1 else 12; a = anio if mes>1 else anio-1
    sb = get_supabase()
    return sb.table("kpis").select("*").eq("anio",a).eq("mes",m).execute().data

@st.cache_data(ttl=300)
def cargar_doctores(anio, mes):
    sb = get_supabase()
    return sb.table("kpi_doctores").select("*").eq("anio",anio).eq("mes",mes).execute().data

@st.cache_data(ttl=300)
def cargar_mix(anio, mes):
    sb = get_supabase()
    return sb.table("kpi_mix_categorias").select("*").eq("anio",anio).eq("mes",mes).execute().data

@st.cache_data(ttl=300)
def cargar_club(anio, mes):
    sb = get_supabase()
    d = sb.table("kpi_club_sonrisa").select("*").eq("anio",anio).eq("mes",mes).execute().data
    return d[0] if d else {}

@st.cache_data(ttl=300)
def cargar_trazabilidad(anio, mes):
    sb = get_supabase()
    return sb.table("kpi_trazabilidad").select("*").eq("anio",anio).eq("mes",mes).execute().data

@st.cache_data(ttl=300)
def cargar_presupuesto(anio, mes):
    sb = get_supabase()
    d = sb.table("presupuesto_anual").select("*").eq("anio",anio).eq("mes",mes).execute().data
    return d[0] if d else {}

def fmt_clp(v):
    if v is None: return "N/D"
    return f"${v:,.0f}".replace(",",".")

def fmt_pct(v):
    if v is None: return "N/D"
    return f"{v:.1f}%"

def get_kpi(kpis, kpi_id):
    for k in kpis:
        if k["kpi_id"] == kpi_id: return k
    return {}

def color_estado(estado):
    if estado == "✅": return "normal"
    if estado == "🟡": return "off"
    if estado == "🔴": return "inverse"
    return "off"

def mostrar_metrica(col, titulo, valor, objetivo, unidad="", estado="⚠️", delta=None, nota=None):
    with col:
        if estado == "✅":
            st.success(f"**{titulo}**")
        elif estado == "🔴":
            st.error(f"**{titulo}**")
        elif estado == "🟡":
            st.warning(f"**{titulo}**")
        else:
            st.info(f"**{titulo}**")

        st.metric(
            label=titulo,
            value=f"{valor} {unidad}".strip(),
            delta=f"vs objetivo: {objetivo}" if objetivo else None,
            label_visibility="collapsed"
        )
        if nota:
            st.caption(nota)

# ============================================================
# CSS
# ============================================================
st.markdown("""
<style>
    .stApp { background-color: #0a0a0a; }
    [data-testid="stSidebar"] { background-color: #111111; }
    .stMetric { background: #1a1a1a; padding: 12px; border-radius: 8px; }
    h1,h2,h3 { color: #ffffff; }
    .stDataFrame { background: #1a1a1a; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# HEADER
# ============================================================
st.title("🦷 CEO Clínica Dental — Cuadro de Mando Integral")
st.caption("Centro de Especialidades Odontológicas Santiago SpA")
st.divider()

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("### 📅 Período")
    periodos = cargar_periodos()

    if not periodos:
        st.error("No hay datos. Ejecuta el importador primero.")
        st.stop()

    opciones = [f"{MESES.get(p['mes'],p['mes'])} {p['anio']}" for p in periodos]
    seleccion = st.selectbox("Seleccionar mes:", opciones)
    idx = opciones.index(seleccion)
    periodo_sel = periodos[idx]
    anio_sel = periodo_sel["anio"]
    mes_sel = periodo_sel["mes"]
    st.caption(f"Procesado: {periodo_sel.get('fecha_procesado','')[:10]}")
    st.divider()

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

def get_k(kid): return get_kpi(kpis, kid)
def get_kant(kid): return get_kpi(kpis_ant, kid)

def delta_pct(kid):
    a = get_k(kid); b = get_kant(kid)
    if a.get("valor") and b.get("valor") and b["valor"]!=0:
        return round(((a["valor"]-b["valor"])/abs(b["valor"]))*100,1)
    return None

# ============================================================
# RESUMEN GENERAL
# ============================================================
if vista == "📊 Resumen General":
    st.header(f"Resumen — {MESES.get(mes_sel,'')} {anio_sel}")

    verdes = sum(1 for k in kpis if k.get("estado")=="✅")
    rojos  = sum(1 for k in kpis if k.get("estado")=="🔴")
    amari  = sum(1 for k in kpis if k.get("estado")=="🟡")
    total  = len(kpis)

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("✅ KPIs Verde", verdes)
    c2.metric("🔴 KPIs Rojo", rojos)
    c3.metric("🟡 KPIs Alerta", amari)
    c4.metric("📊 Total KPIs", total)

    st.divider()
    st.subheader("KPIs Críticos")

    ppto = presupuesto.get("ventas",0)
    k18 = get_k("18"); ing_real = k18.get("valor",0) or 0
    cumpl = (ing_real/ppto*100) if ppto>0 else 0
    e18 = "✅" if cumpl>=100 else ("🟡" if cumpl>=90 else "🔴")

    k19 = get_k("19"); margen = k19.get("valor")
    obj_m = presupuesto.get("margen_pct")
    e19 = "✅" if (margen and obj_m and margen>=obj_m) else "🔴"

    k1 = get_k("1"); k10a = get_k("10a"); k8 = get_k("8"); kT = get_k("T")

    c1,c2,c3 = st.columns(3)
    with c1:
        st.metric("💰 Facturación vs Presupuesto", fmt_pct(cumpl), f"Real: {fmt_clp(ing_real)}")
        st.caption(f"Objetivo: {fmt_clp(ppto)} | Estado: {e18}")
    with c2:
        st.metric("📈 Margen Operacional", fmt_pct(margen), f"Objetivo: {fmt_pct(obj_m)}")
        st.caption(f"Estado: {e19}")
    with c3:
        st.metric("✅ Tasa Cierre Presupuestos", fmt_pct(k1.get("valor")), f"Objetivo: ≥70%")
        st.caption(f"Estado: {k1.get('estado','⚠️')}")

    c1,c2,c3 = st.columns(3)
    with c1:
        st.metric("🏥 Atenciones Totales", f"{int(k10a.get('valor',0) or 0)}", f"Objetivo: ≥487")
        st.caption(f"Estado: {k10a.get('estado','⚠️')}")
    with c2:
        st.metric("💵 Ingresos por Atención", fmt_clp(k8.get("valor")), f"Objetivo: ≥$45.000")
        st.caption(f"Estado: {k8.get('estado','⚠️')}")
    with c3:
        st.metric("📍 Trazabilidad Origen", fmt_pct(kT.get("valor")), f"Objetivo: ≥90%")
        st.caption(f"Estado: {kT.get('estado','⚠️')} | Prerequisito CPA y ROAS")

    st.divider()
    st.subheader("Tabla Completa de KPIs")
    filas = []
    for k in kpis:
        if k.get("valor") is not None:
            u = k.get("unidad","")
            if u=="CLP": val = fmt_clp(k["valor"])
            elif u=="%": val = fmt_pct(k["valor"])
            else: val = str(int(k["valor"])) if k["valor"] else "0"
        else:
            val = k.get("valor_texto","N/D")
        obj = k.get("objetivo_texto") or (fmt_clp(k["objetivo"]) if k.get("unidad")=="CLP" and k.get("objetivo") else fmt_pct(k["objetivo"]) if k.get("unidad")=="%" and k.get("objetivo") else str(k.get("objetivo","—")))
        filas.append({"Estado":k.get("estado","—"),"KPI":k.get("kpi_nombre",""),"Sección":k.get("seccion",""),"Resultado":val,"Objetivo":obj})

    if filas:
        st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)

# ============================================================
# COMERCIAL
# ============================================================
elif vista == "💼 Comercial":
    st.header(f"Comercial — {MESES.get(mes_sel,'')} {anio_sel}")

    st.subheader("📋 Presupuestos")
    k1=get_k("1"); k2=get_k("2"); k3=get_k("3")
    c1,c2,c3 = st.columns(3)
    with c1:
        st.metric("Tasa Cierre", fmt_pct(k1.get("valor")), f"Obj: ≥70%")
        st.caption(f"Estado: {k1.get('estado','⚠️')}")
    with c2:
        st.metric("Presupuestos Generados", str(int(k2.get("valor",0) or 0)), f"Obj: ≥230")
        st.caption(f"Estado: {k2.get('estado','⚠️')}")
    with c3:
        st.metric("Captación Seguimiento", fmt_pct(k3.get("valor")), f"Obj: ≥20%")
        st.caption(f"Estado: {k3.get('estado','⚠️')}")

    st.divider()
    st.subheader("📡 Publicidad Digital")
    kT=get_k("T")
    traz_val = kT.get("valor",0) or 0
    if traz_val >= 90:
        st.success(f"✅ Trazabilidad de Origen: {fmt_pct(traz_val)} — CPA y ROAS válidos")
    else:
        st.warning(f"⚠️ Trazabilidad de Origen: {fmt_pct(traz_val)} — objetivo ≥90% para validar CPA y ROAS")

    k4=get_k("4"); k5=get_k("5"); k6=get_k("6"); k7=get_k("7")
    c1,c2 = st.columns(2)
    with c1:
        st.markdown("**Meta Ads**")
        v4 = k4.get("valor_texto") or fmt_clp(k4.get("valor"))
        st.metric("CPA Meta Ads", v4, "Obj: Por definir")
        st.caption(k4.get("nota",""))
        roas_m = k6.get("valor")
        st.metric("ROAS Meta Ads", f"{roas_m:.2f}x" if roas_m else "N/D", "Obj: ≥3,5x")
        st.caption("Piso mensual — ROAS real considera LTV")
    with c2:
        st.markdown("**Google Ads**")
        v5 = k5.get("valor_texto") or fmt_clp(k5.get("valor"))
        st.metric("CPA Google Ads", v5, "Obj: Por definir")
        st.caption(k5.get("nota",""))
        roas_g = k7.get("valor")
        st.metric("ROAS Google Ads", f"{roas_g:.2f}x" if roas_g else "N/D", "Obj: ≥3,5x")
        st.caption("Piso mensual — ROAS real considera LTV")

    traz = cargar_trazabilidad(anio_sel, mes_sel)
    if traz:
        st.divider()
        st.subheader("Detalle por Canal")
        st.dataframe(pd.DataFrame(traz), use_container_width=True, hide_index=True)

# ============================================================
# OPERACIÓN
# ============================================================
elif vista == "⚙️ Operación":
    st.header(f"Operación — {MESES.get(mes_sel,'')} {anio_sel}")
    k8=get_k("8"); k9=get_k("9"); k10a=get_k("10a"); k10b=get_k("10b"); k11=get_k("11")

    c1,c2,c3 = st.columns(3)
    with c1:
        st.metric("Ingresos por Atención", fmt_clp(k8.get("valor")), f"Obj: ≥$45.000")
        st.caption(f"Estado: {k8.get('estado','⚠️')}")
    with c2:
        st.metric("Asistencia a Citas", fmt_pct(k9.get("valor")), f"Obj: ≥80%")
        st.caption(f"Estado: {k9.get('estado','⚠️')}")
    with c3:
        st.metric("Producción por Sillón", fmt_clp(k11.get("valor")), f"Obj: ≥$10.986.906")
        st.caption(f"Estado: {k11.get('estado','⚠️')}")

    c1,c2 = st.columns(2)
    with c1:
        st.metric("Atenciones Totales", str(int(k10a.get("valor",0) or 0)), f"Obj: ≥487")
        st.caption(f"Estado: {k10a.get('estado','⚠️')}")
    with c2:
        st.metric("Pacientes Únicos", str(int(k10b.get("valor",0) or 0)), f"Obj: ≥415")
        st.caption(f"Estado: {k10b.get('estado','⚠️')}")

# ============================================================
# MIX DE SERVICIOS
# ============================================================
elif vista == "📋 Mix de Servicios":
    st.header(f"Mix de Servicios — {MESES.get(mes_sel,'')} {anio_sel}")
    k13=get_k("13"); k14=get_k("14")

    c1,c2 = st.columns(2)
    with c1:
        st.metric("Casos Nuevos Ortodoncia", str(int(k13.get("valor",0) or 0)), "Obj: ≥12 casos/mes")
        st.caption(f"Estado: {k13.get('estado','⚠️')}")
    with c2:
        st.metric("Casos Nuevos Implantes", str(int(k14.get("valor",0) or 0)), "Obj: ≥11 casos/mes")
        st.caption(f"Estado: {k14.get('estado','⚠️')}")

    mix = cargar_mix(anio_sel, mes_sel)
    if mix:
        st.divider()
        st.subheader("Facturación por Categoría")
        df = pd.DataFrame(mix).sort_values("ingresos",ascending=False)
        if "categoria" in df.columns:
            df_show = df[["categoria","ingresos","pct_real"]].copy()
            df_show.columns = ["Categoría","Ingresos ($)","% Real"]
            st.dataframe(df_show, use_container_width=True, hide_index=True,
                column_config={"Ingresos ($)":st.column_config.NumberColumn(format="$%d"),
                               "% Real":st.column_config.NumberColumn(format="%.1f%%")})
            if len(df)>0:
                st.bar_chart(df.set_index("categoria")["ingresos"])

# ============================================================
# DOCTORES
# ============================================================
elif vista == "👨‍⚕️ Doctores":
    st.header(f"Doctores — {MESES.get(mes_sel,'')} {anio_sel}")
    doctores = cargar_doctores(anio_sel, mes_sel)
    ppto_mes = presupuesto.get("ventas",0)

    if doctores:
        st.subheader("Tasa de Cierre")
        filas_tc = []
        for d in sorted(doctores, key=lambda x: -(x.get("presupuestos_generados") or 0)):
            tasa = d.get("tasa_cierre"); obj = d.get("objetivo_tasa_cierre",70)
            estado_tc = "✅" if (tasa and tasa>=obj) else "🔴" if tasa is not None else "—"
            filas_tc.append({"Estado":estado_tc,"Doctor":d["doctor"].title(),
                "Especialidad":d.get("especialidad",""),
                "Generados":d.get("presupuestos_generados",0),
                "Capturados":d.get("presupuestos_capturados",0),
                "Tasa":f"{tasa:.1f}%" if tasa else "N/D",
                "Objetivo":f"{obj:.0f}%"})
        st.dataframe(pd.DataFrame(filas_tc), use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Productividad")
        filas_p = []
        for d in sorted(doctores, key=lambda x: -(x.get("ingresos") or 0)):
            ing = d.get("ingresos",0) or 0
            pct = d.get("pct_historico",0) or 0
            obj_ing = ppto_mes*pct/100 if ppto_mes and pct else None
            cumpl = (ing/obj_ing*100) if obj_ing and obj_ing>0 else None
            estado_p = "✅" if (cumpl and cumpl>=90) else "🔴" if cumpl is not None else "—"
            filas_p.append({"Estado":estado_p,"Doctor":d["doctor"].title(),
                "Especialidad":d.get("especialidad",""),
                "Ingresos":ing,"Objetivo":obj_ing,
                "Cumplimiento":f"{cumpl:.1f}%" if cumpl else "N/D"})
        st.dataframe(pd.DataFrame(filas_p), use_container_width=True, hide_index=True,
            column_config={"Ingresos":st.column_config.NumberColumn(format="$%d"),
                          "Objetivo":st.column_config.NumberColumn(format="$%d")})
    else:
        st.info("No hay datos de doctores para este período.")

# ============================================================
# FINANCIERO
# ============================================================
elif vista == "💰 Financiero":
    st.header(f"Financiero — {MESES.get(mes_sel,'')} {anio_sel}")
    k18=get_k("18"); k19=get_k("19")
    ppto = presupuesto.get("ventas",0); obj_m = presupuesto.get("margen_pct")
    ing_real = k18.get("valor",0) or 0
    cumpl = (ing_real/ppto*100) if ppto>0 else 0
    e18 = "✅" if cumpl>=100 else ("🟡" if cumpl>=90 else "🔴")
    margen = k19.get("valor")
    e19 = "✅" if (margen and obj_m and margen>=obj_m) else "🔴"

    c1,c2,c3 = st.columns(3)
    with c1:
        st.metric("Facturación Real", fmt_clp(ing_real), f"vs presupuesto {fmt_clp(ppto)}")
        st.caption(f"Cumplimiento: {cumpl:.1f}% | Estado: {e18}")
    with c2:
        st.metric("Margen Operacional", fmt_pct(margen), f"Obj: ≥{fmt_pct(obj_m)}")
        st.caption(f"Estado: {e19}")
    with c3:
        k18_ant = get_kant("18"); ing_ant = k18_ant.get("valor",0) or 0
        var = ((ing_real-ing_ant)/abs(ing_ant)*100) if ing_ant!=0 else None
        e20 = "✅" if (var and var>=-5) else ("🟡" if var and var>=-15 else "🔴")
        st.metric("Variación vs Mes Anterior", fmt_pct(var) if var else "N/D", f"Anterior: {fmt_clp(ing_ant)}")
        st.caption(f"Verde ≥-5% | Amarillo -5% a -15% | Rojo <-15% | Estado: {e20}")

    st.divider()
    st.subheader("Presupuesto 2026")
    sb = get_supabase()
    resp = sb.table("presupuesto_anual").select("*").eq("anio",anio_sel).order("mes").execute()
    if resp.data:
        df_p = pd.DataFrame(resp.data)
        df_p["Mes"] = df_p["mes"].map(MESES)
        df_p = df_p[["Mes","ventas","resultado_operacional","margen_pct"]]
        df_p.columns = ["Mes","Ventas ($)","Resultado ($)","Margen %"]
        st.dataframe(df_p, use_container_width=True, hide_index=True,
            column_config={"Ventas ($)":st.column_config.NumberColumn(format="$%d"),
                          "Resultado ($)":st.column_config.NumberColumn(format="$%d"),
                          "Margen %":st.column_config.NumberColumn(format="%.1f%%")})

# ============================================================
# PROGRAMAS COMERCIALES
# ============================================================
elif vista == "🌟 Programas Comerciales":
    st.header(f"Programas Comerciales — {MESES.get(mes_sel,'')} {anio_sel}")
    club = cargar_club(anio_sel, mes_sel)
    k21a=get_k("21a"); k21b=get_k("21b"); k21c=get_k("21c"); k22=get_k("22"); k23=get_k("23")

    st.subheader("🌟 Club Sonrisa CEO")
    c1,c2,c3 = st.columns(3)
    with c1:
        st.metric("Ingresos Club Sonrisa", fmt_clp(k21a.get("valor")), "Obj: ≥$17.849.110")
        st.caption(f"Estado: {k21a.get('estado','⚠️')} | {k21a.get('nota','')}")
    with c2:
        st.metric("Tasa de Afiliación", fmt_pct(k21b.get("valor")), "Obj: ≥70%")
        st.caption(f"Estado: {k21b.get('estado','⚠️')} | {k21b.get('nota','')}")
    with c3:
        st.metric("Tasa de Retorno (6 meses)", fmt_pct(k21c.get("valor")), "Obj: ≥60%")
        st.caption(f"Estado: {k21c.get('estado','⚠️')}")

    if club:
        st.divider()
        st.subheader("Segmentación de Socios")
        total = club.get("total_socios",0) or 1
        retorno = club.get("socios_retorno",0)
        proceso = club.get("socios_en_proceso",0)
        sin_act = club.get("socios_sin_actividad",0)
        c1,c2,c3 = st.columns(3)
        c1.metric("✅ Con Retorno (≥2 tratamientos)", retorno, f"{retorno/total*100:.1f}% del total")
        c2.metric("🟡 En Proceso (1 tratamiento)", proceso, f"{proceso/total*100:.1f}% del total")
        c3.metric("🔴 Sin Actividad (0 tratamientos)", sin_act, f"{sin_act/total*100:.1f}% del total")

        st.divider()
        st.subheader("Ingresos — Ortodoncia vs Otros")
        c1,c2 = st.columns(2)
        with c1:
            ing_otros = club.get("ingresos_otros",0)
            e = "✅" if ing_otros>=12754839 else "🔴"
            st.metric("Otros Tratamientos (efecto real)", fmt_clp(ing_otros), "Obj: ≥$12.754.839")
            st.caption(f"Estado: {e} | Mide impacto real del programa")
        with c2:
            ing_orto = club.get("ingresos_ortodoncia",0)
            e = "✅" if ing_orto>=5094270 else "🔴"
            st.metric("Ortodoncia (referencial)", fmt_clp(ing_orto), "Obj: ≥$5.094.270")
            st.caption(f"Estado: {e} | Atenciones recurrentes")

    st.divider()
    st.subheader("🤝 Recomienda CEO")
    c1,c2 = st.columns(2)
    with c1:
        st.metric("Pacientes Referidos", str(int(k22.get("valor",0) or 0)), "Obj: ≥3 pacientes/mes")
        st.caption(f"Estado: {k22.get('estado','⚠️')} | Programa lanzado junio 2026")
    with c2:
        st.metric("Ingresos Atribuidos", fmt_clp(k23.get("valor")), "Obj: ≥$600.000/mes")
        st.caption(f"Estado: {k23.get('estado','⚠️')} | Anual: $7.500.000")

st.divider()
st.caption("CMI CEO Clínica Dental Santiago SpA")
