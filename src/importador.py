"""
IMPORTADOR CMI — CEO CLÍNICA DENTAL SANTIAGO
Versión: 2.0 | Julio 2026
- Soporta CSV y XLSX
- Búsqueda flexible de archivos por patrón
- Calcula los 26 KPIs y guarda en Supabase
"""

import os
import csv
import re
import glob
from datetime import datetime
from collections import defaultdict
import sys

# Supabase
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# ============================================================
# CONFIGURACIÓN
# ============================================================

DOCTORES_ACTIVOS = [
    "ANDREI IVANOV ALARCON LOPEZ",
    "BIANCA MADELEINE CERCADO AGUILAR",
    "DIANA CONSUELO BARRERA BALLESTEROS",
    "ALEXIS VICTOR HERNANDEZ FIGUEROA",
    "CARLOS OROZCO",
    "DOMINIQUE COLLAO",
    "ANDREA CHAUX FLOREZ",
    "CRISTINA ANDREA RAMOS ZAMORA",
    "ALVARO ANDRES SIERRA FUENTES",
    "ALINE BELEN VENEGAS CATRILEO",
    "JUAN CARLOS QUIROGA",
    "CAMILO ANDRES VICTORIA SEPULVEDA",
]

ESPECIALIDAD_DOCTOR = {
    "ANDREI IVANOV ALARCON LOPEZ": "Implantología",
    "BIANCA MADELEINE CERCADO AGUILAR": "General",
    "DIANA CONSUELO BARRERA BALLESTEROS": "Ortodoncia",
    "ALEXIS VICTOR HERNANDEZ FIGUEROA": "General",
    "CARLOS OROZCO": "Ortodoncia",
    "DOMINIQUE COLLAO": "General",
    "ANDREA CHAUX FLOREZ": "Ortodoncia",
    "CRISTINA ANDREA RAMOS ZAMORA": "Endodoncia",
    "ALVARO ANDRES SIERRA FUENTES": "Implantología",
    "ALINE BELEN VENEGAS CATRILEO": "General",
    "JUAN CARLOS QUIROGA": "Periodoncia",
    "CAMILO ANDRES VICTORIA SEPULVEDA": "Ortodoncia",
}

PCT_HISTORICO_DOCTOR = {
    "ANDREI IVANOV ALARCON LOPEZ": 20.5,
    "BIANCA MADELEINE CERCADO AGUILAR": 12.8,
    "DIANA CONSUELO BARRERA BALLESTEROS": 12.4,
    "ALEXIS VICTOR HERNANDEZ FIGUEROA": 12.3,
    "CARLOS OROZCO": 11.9,
    "DOMINIQUE COLLAO": 8.6,
    "ANDREA CHAUX FLOREZ": 5.8,
    "CRISTINA ANDREA RAMOS ZAMORA": 5.4,
    "ALVARO ANDRES SIERRA FUENTES": 2.9,
    "ALINE BELEN VENEGAS CATRILEO": 2.7,
    "JUAN CARLOS QUIROGA": 1.7,
    "CAMILO ANDRES VICTORIA SEPULVEDA": 1.6,
}

OBJETIVO_TASA_CIERRE = {
    "General": 70.0,
    "Ortodoncia": 70.0,
    "Implantología": 30.0,
    "Periodoncia": 50.0,
    "Endodoncia": 70.0,
}

CONVENIOS_SANTIAGO = [
    "BUSES VULE", "CLINICA CDS", "CLUB SONRISA CEO",
    "COLEGIO LORD TOMAS COCHRANE", "ESCUELA LENGUAJE EDUCCERE",
    "PRECIOS SANTIAGO", "PROMARCO SPA", "TARJETA TU PUENTE"
]

ORDEN_MESES = {
    "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4,
    "Mayo": 5, "Junio": 6, "Julio": 7, "Agosto": 8,
    "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12
}

NOMBRES_MESES = {v: k for k, v in ORDEN_MESES.items()}

# ============================================================
# LECTURA DE ARCHIVOS (CSV + XLSX)
# ============================================================

def leer_xlsx(ruta):
    try:
        import openpyxl
        wb = openpyxl.load_workbook(ruta, data_only=True)
        ws = wb.active
        rows = []
        headers = None
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if all(v is None for v in row):
                continue
            if headers is None:
                headers = [str(h).strip() if h is not None else f"col_{i}" for i, h in enumerate(row)]
                continue
            row_dict = {}
            for h, v in zip(headers, row):
                row_dict[h] = str(v).strip() if v is not None else ""
            rows.append(row_dict)
        return rows
    except Exception as e:
        print(f"  ⚠️  Error leyendo XLSX {ruta}: {e}")
        return []

def leer_csv(ruta, delimiter=";", skip_first=False):
    rows = []
    for delim in [delimiter, "," if delimiter == ";" else ";"]:
        try:
            with open(ruta, encoding="utf-8-sig") as f:
                if skip_first:
                    next(f)
                reader = csv.DictReader(f, delimiter=delim)
                filas = list(reader)
                if filas and len(filas[0]) > 1:
                    return filas
                elif filas:
                    rows = filas
        except:
            pass
    return rows

def leer_archivo(ruta, delimiter=";", skip_first=False):
    if not ruta:
        return []
    if ruta.endswith(".xlsx") or ruta.endswith(".xls"):
        return leer_xlsx(ruta)
    return leer_csv(ruta, delimiter, skip_first)

def buscar_archivo(carpeta, *patrones):
    """Busca archivo en carpeta que contenga alguno de los patrones"""
    for patron in patrones:
        for ext in [".csv", ".xlsx", ".xls"]:
            matches = glob.glob(os.path.join(carpeta, f"*{patron}*{ext}"))
            if matches:
                print(f"    → Encontrado: {os.path.basename(matches[0])}")
                return matches[0]
    return None

# ============================================================
# UTILIDADES
# ============================================================

def limpiar_monto(valor):
    if not valor:
        return 0.0
    try:
        v = str(valor).replace("$","").replace(" ","")
        # Formato chileno: punto miles, coma decimal
        if "," in v and "." in v:
            v = v.replace(".","").replace(",",".")
        elif "," in v:
            v = v.replace(",",".")
        elif v.count(".") > 1:
            v = v.replace(".","")
        return float(v)
    except:
        return 0.0

def normalizar_doctor(nombre, apellido):
    return f"{nombre} {apellido}".strip().upper()

def estado_kpi(valor, objetivo, mayor_mejor=True):
    if valor is None or objetivo is None:
        return "⚠️"
    if mayor_mejor:
        return "✅" if valor >= objetivo else "🔴"
    return "✅" if valor <= objetivo else "🔴"

# ============================================================
# CÁLCULO DE KPIs
# ============================================================

def calcular_kpis(anio, mes, carpeta_datos, carpeta_historico):
    resultados = []
    resultados_doctores = []
    resultados_mix = []
    resultado_club = {}
    resultados_trazabilidad = []

    mes_nombre = NOMBRES_MESES.get(mes, "")

    print(f"\n{'='*60}")
    print(f"  CMI CEO CLÍNICA DENTAL — {mes_nombre} {anio}")
    print(f"{'='*60}")

    # --------------------------------------------------------
    # LOCALIZAR ARCHIVOS
    # --------------------------------------------------------
    print("\n  [Localizando archivos...]")

    f_acciones = buscar_archivo(carpeta_datos, "acciones_realizadas", "Acciones_Realizadas", "acciones realizadas")
    f_citas = buscar_archivo(carpeta_datos, "agenda_citas", "Agenda_Citas", "agenda citas")
    f_seguimiento = buscar_archivo(carpeta_datos, "Seguimiento_Presupuestos", "seguimiento_presupuestos", "Sistema_Seguimiento")
    f_pacientes_nuevos = buscar_archivo(carpeta_datos, "pacientes_nuevos", "Pacientes_Nuevos", "pacientes nuevos")
    f_trat_generados = buscar_archivo(carpeta_datos, "tratamientos_generados", "Tratamientos_Generados", "tratamientos generados")
    f_presupuestos_cap = buscar_archivo(carpeta_datos, "Presupuestos_Capturados", "presupuestos_capturados")
    f_chipax = buscar_archivo(carpeta_datos, "Resultado_Operacional", "resultado_operacional", "Chipax", "chipax")
    f_pacientes_todos = buscar_archivo(carpeta_datos, "pacientes_todos", "Pacientes_Todos", "pacientes todos")
    f_meta1 = buscar_archivo(carpeta_datos, "meta_ads_1", "Meta_Ads_1", "Campanas_1", "campanas_1", "Campañas_1", "Reporte-Campan")
    f_meta2 = buscar_archivo(carpeta_datos, "meta_ads_2", "Meta_Ads_2", "Campanas_2", "campanas_2", "Campañas_2")
    f_google = buscar_archivo(carpeta_datos, "google_ads", "Google_Ads", "Informe_de_campana", "Informe_campana", "Informe de campana")
    f_historico = buscar_archivo(carpeta_historico, "historico", "acciones_realizadas", "tratamientos_acciones")

    # --------------------------------------------------------
    # LEER ARCHIVOS
    # --------------------------------------------------------
    acciones = leer_archivo(f_acciones, ";", True) if f_acciones else []
    citas = leer_archivo(f_citas, ";", True) if f_citas else []
    seguimiento = leer_archivo(f_seguimiento, ";", True) if f_seguimiento else []
    pacientes_nuevos = leer_archivo(f_pacientes_nuevos, ";", True) if f_pacientes_nuevos else []
    trat_generados = leer_archivo(f_trat_generados, ";", True) if f_trat_generados else []
    presupuestos_cap = leer_archivo(f_presupuestos_cap, ";", True) if f_presupuestos_cap else []
    chipax_rows = leer_archivo(f_chipax) if f_chipax else []
    pacientes_todos = leer_archivo(f_pacientes_todos, ";", True) if f_pacientes_todos else []
    historico = leer_archivo(f_historico, ";", True) if f_historico else []

    print(f"\n  Acciones realizadas: {len(acciones)} filas")
    print(f"  Agenda citas: {len(citas)} filas")
    print(f"  Pacientes nuevos: {len(pacientes_nuevos)} filas")
    print(f"  Histórico: {len(historico)} filas")
    print(f"  Chipax: {len(chipax_rows)} filas")

    # --------------------------------------------------------
    # PRECÁLCULOS
    # --------------------------------------------------------
    atenciones_unicas = set()
    pacientes_unicos = set()
    facturacion_total = 0.0
    facturacion_por_convenio = defaultdict(float)
    atenciones_por_convenio = defaultdict(set)
    facturacion_ortodoncia_club = 0.0
    atenciones_ortodoncia_club = set()
    facturacion_por_doctor = defaultdict(float)
    facturacion_por_categoria = defaultdict(float)

    for row in acciones:
        pid = row.get("# Paciente", "").strip()
        fecha = row.get("Fecha de realización", "").strip()
        convenio = row.get("Convenio Paciente", "").strip().upper()
        categoria = row.get("Nombre Categoria", "").strip().upper()
        prestacion = row.get("Nombre Prestación", "").strip()
        nombre_doc = row.get("Nombre Profesional Realizador", "").strip()
        apellido_doc = row.get("Apellidos Profesional Realizador", "").strip()
        monto = limpiar_monto(row.get("Pagado Paciente Prestación (Abonado)", "0"))

        if pid and fecha:
            atenciones_unicas.add((pid, fecha))
            pacientes_unicos.add(pid)

        facturacion_total += monto
        facturacion_por_convenio[convenio] += monto
        if pid and fecha:
            atenciones_por_convenio[convenio].add((pid, fecha))

        if convenio == "CLUB SONRISA CEO":
            es_orto = categoria in ["ORTODONCIA", "ACCIONES DE ORTODONCIA"]
            if categoria == "ESPECIALIDAD":
                p_lower = prestacion.lower()
                es_orto = any(x in p_lower for x in ["instalac", "control", "contencion", "ortodoncia", "pack ortodoncia"])
            if es_orto:
                facturacion_ortodoncia_club += monto
                if pid and fecha:
                    atenciones_ortodoncia_club.add((pid, fecha))

        if nombre_doc:
            dk = normalizar_doctor(nombre_doc, apellido_doc)
            facturacion_por_doctor[dk] += monto

        facturacion_por_categoria[categoria] += monto

    total_atenciones = len(atenciones_unicas)
    total_pacientes = len(pacientes_unicos)

    # --------------------------------------------------------
    # SECCIÓN COMERCIAL
    # --------------------------------------------------------
    print("\n  [COMERCIAL]")

    # KPI 1 — Tasa Cierre (desde presupuestos capturados)
    kpi1_valor = None
    for row in presupuestos_cap:
        for k, v in row.items():
            if k and mes_nombre[:3].lower() in str(k).lower() and str(anio) in str(k):
                try:
                    pct = float(str(v).replace("%","").replace(",",".").strip())
                    if 0 <= pct <= 100:
                        kpi1_valor = pct
                except:
                    pass

    if kpi1_valor is None and trat_generados:
        gen = cap = 0
        for row in trat_generados:
            total_ppto = limpiar_monto(row.get("Total Presupuesto","0"))
            if total_ppto > 0:
                gen += 1
                if row.get("Tratamiento Capturado","").strip() == "Capturado":
                    cap += 1
        kpi1_valor = (cap/gen*100) if gen > 0 else None

    e1 = estado_kpi(kpi1_valor, 70.0)
    print(f"    KPI 1 Tasa Cierre: {kpi1_valor:.1f}% {e1}" if kpi1_valor else "    KPI 1 Tasa Cierre: N/D")
    resultados.append({"kpi_id":"1","seccion":"COMERCIAL","kpi_nombre":"Tasa Cierre Presupuestos",
        "valor":round(kpi1_valor,2) if kpi1_valor else None,"objetivo":70.0,"unidad":"%","estado":e1})

    # KPI 2 — Presupuestos Generados
    kpi2_gen = sum(1 for r in trat_generados if limpiar_monto(r.get("Total Presupuesto","0")) > 0)
    e2 = estado_kpi(kpi2_gen, 230)
    print(f"    KPI 2 Presupuestos Generados: {kpi2_gen} {e2}")
    resultados.append({"kpi_id":"2","seccion":"COMERCIAL","kpi_nombre":"Presupuestos Generados",
        "valor":kpi2_gen,"objetivo":230.0,"unidad":"unidades","estado":e2})

    # KPI 3 — Captación por Seguimiento
    kpi3_valor = None
    for row in seguimiento:
        anio_s = str(row.get("Año","")).strip()
        mes_s = str(row.get("Mes","")).strip()
        if str(anio) in anio_s and mes_nombre.lower() in mes_s.lower():
            try:
                kpi3_valor = float(str(row.get("% de Recuperación","0")).replace("%","").replace(",",".").strip())
            except:
                pass

    e3 = estado_kpi(kpi3_valor, 20.0)
    print(f"    KPI 3 Captación Seguimiento: {kpi3_valor:.1f}%" if kpi3_valor else "    KPI 3: N/D")
    resultados.append({"kpi_id":"3","seccion":"COMERCIAL","kpi_nombre":"Captación por Seguimiento",
        "valor":round(kpi3_valor,2) if kpi3_valor else None,"objetivo":20.0,"unidad":"%","estado":e3})

    # KPI T — Trazabilidad
    total_pn = len(pacientes_nuevos)
    con_origen = 0
    canales = defaultdict(int)
    canales_ingresos = defaultdict(float)
    pacientes_meta = set()
    pacientes_google = set()
    pacientes_referidos = set()

    for row in pacientes_nuevos:
        ref = row.get("Referencia Paciente","").strip().upper()
        pid = row.get("# Paciente","").strip()
        if ref == "REDES SOCIALES":
            con_origen += 1; canales["Meta Ads"] += 1; pacientes_meta.add(pid)
        elif ref == "GOOGLE":
            con_origen += 1; canales["Google Ads"] += 1; pacientes_google.add(pid)
        elif ref.startswith("REFERIDO"):
            con_origen += 1; canales["Recomienda CEO"] += 1; pacientes_referidos.add(pid)
        elif ref in ["ORGÁNICO","ORGANICO"]:
            con_origen += 1; canales["Orgánico"] += 1
        elif ref:
            con_origen += 1

    kpiT = (con_origen/total_pn*100) if total_pn > 0 else 0
    eT = estado_kpi(kpiT, 90.0)
    es_valido = kpiT >= 90.0
    print(f"    KPI T Trazabilidad: {kpiT:.1f}% {eT}")
    resultados.append({"kpi_id":"T","seccion":"COMERCIAL","kpi_nombre":"Trazabilidad de Origen",
        "valor":round(kpiT,2),"objetivo":90.0,"unidad":"%","estado":eT,
        "nota":"Prerequisito para CPA y ROAS"})

    # Ingresos atribuidos por canal
    pid_acciones = defaultdict(float)
    for row in acciones:
        pid = row.get("# Paciente","").strip()
        monto = limpiar_monto(row.get("Pagado Paciente Prestación (Abonado)","0"))
        pid_acciones[pid] += monto

    for pid in pacientes_meta:
        canales_ingresos["Meta Ads"] += pid_acciones.get(pid, 0)
    for pid in pacientes_google:
        canales_ingresos["Google Ads"] += pid_acciones.get(pid, 0)
    for pid in pacientes_referidos:
        canales_ingresos["Recomienda CEO"] += pid_acciones.get(pid, 0)

    # Inversión Meta Ads
    inversion_meta = 0.0
    for f_meta in [f_meta1, f_meta2]:
        if f_meta:
            rows_meta = leer_archivo(f_meta, ",")
            for row in rows_meta:
                for k, v in row.items():
                    if k and "importe" in str(k).lower() and "gastado" in str(k).lower():
                        inversion_meta += limpiar_monto(v)

    # Inversión Google Ads
    inversion_google = 0.0
    if f_google:
        rows_google = leer_archivo(f_google, ",")
        for row in rows_google:
            concepto = str(row.get("Campaña", row.get("Campaign",""))).lower()
            if "total" in concepto:
                for k, v in row.items():
                    if k and "costo" in str(k).lower():
                        inversion_google += limpiar_monto(v)
                        break

    # KPI 4 — CPA Meta
    n_meta = len(pacientes_meta)
    cpa_meta = (inversion_meta/n_meta) if n_meta > 0 and inversion_meta > 0 else None
    nota_cpa = "" if es_valido else "⚠️ Trazabilidad <90% — dato referencial"
    print(f"    KPI 4 CPA Meta: ${cpa_meta:,.0f}" if cpa_meta else "    KPI 4 CPA Meta: N/D")
    resultados.append({"kpi_id":"4","seccion":"COMERCIAL","kpi_nombre":"CPA Meta Ads",
        "valor":round(cpa_meta,2) if cpa_meta else None,
        "valor_texto":f"${cpa_meta:,.0f}" if cpa_meta else "N/D",
        "objetivo":None,"objetivo_texto":"Por definir","unidad":"CLP",
        "estado":"⏳" if not es_valido else "ℹ️","es_valido":es_valido,"nota":nota_cpa})

    # KPI 5 — CPA Google
    n_google = len(pacientes_google)
    cpa_google = (inversion_google/n_google) if n_google > 0 and inversion_google > 0 else None
    print(f"    KPI 5 CPA Google: ${cpa_google:,.0f}" if cpa_google else "    KPI 5 CPA Google: N/D")
    resultados.append({"kpi_id":"5","seccion":"COMERCIAL","kpi_nombre":"CPA Google Ads",
        "valor":round(cpa_google,2) if cpa_google else None,
        "valor_texto":f"${cpa_google:,.0f}" if cpa_google else "N/D",
        "objetivo":None,"objetivo_texto":"Por definir","unidad":"CLP",
        "estado":"⏳" if not es_valido else "ℹ️","es_valido":es_valido,"nota":nota_cpa})

    # KPI 6 — ROAS Meta
    ing_meta = canales_ingresos["Meta Ads"]
    roas_meta = (ing_meta/inversion_meta) if inversion_meta > 0 else None
    e6 = estado_kpi(roas_meta, 3.5) if roas_meta and es_valido else "⚠️"
    print(f"    KPI 6 ROAS Meta: {roas_meta:.2f}x" if roas_meta else "    KPI 6 ROAS Meta: N/D")
    resultados.append({"kpi_id":"6","seccion":"COMERCIAL","kpi_nombre":"ROAS Meta Ads",
        "valor":round(roas_meta,2) if roas_meta else None,"objetivo":3.5,"unidad":"x",
        "estado":e6,"es_valido":es_valido,"nota":"ROAS = piso mensual. ROAS real considera LTV."})

    # KPI 7 — ROAS Google
    ing_google = canales_ingresos["Google Ads"]
    roas_google = (ing_google/inversion_google) if inversion_google > 0 else None
    e7 = estado_kpi(roas_google, 3.5) if roas_google and es_valido else "⚠️"
    print(f"    KPI 7 ROAS Google: {roas_google:.2f}x" if roas_google else "    KPI 7 ROAS Google: N/D")
    resultados.append({"kpi_id":"7","seccion":"COMERCIAL","kpi_nombre":"ROAS Google Ads",
        "valor":round(roas_google,2) if roas_google else None,"objetivo":3.5,"unidad":"x",
        "estado":e7,"es_valido":es_valido,"nota":"ROAS = piso mensual. ROAS real considera LTV."})

    for canal, n in canales.items():
        inv = inversion_meta if canal=="Meta Ads" else (inversion_google if canal=="Google Ads" else 0)
        ing = canales_ingresos.get(canal, 0)
        resultados_trazabilidad.append({
            "canal":canal,"pacientes":n,"ingresos":round(ing,2),
            "inversion":round(inv,2),
            "cpa":round(inv/n,2) if n>0 and inv>0 else None,
            "roas":round(ing/inv,2) if inv>0 else None,
        })

    # --------------------------------------------------------
    # SECCIÓN OPERACIÓN
    # --------------------------------------------------------
    print("\n  [OPERACIÓN]")

    kpi8 = (facturacion_total/total_atenciones) if total_atenciones > 0 else 0
    e8 = estado_kpi(kpi8, 45000)
    print(f"    KPI 8 Ingresos/Atención: ${kpi8:,.0f} {e8}")
    resultados.append({"kpi_id":"8","seccion":"OPERACIÓN","kpi_nombre":"Ingresos por Atención",
        "valor":round(kpi8,2),"objetivo":45000.0,"unidad":"CLP","estado":e8})

    total_citas = len(citas)
    cambio_fecha = sum(1 for r in citas if r.get("Estado Cita","").strip() == "Cambio de fecha")
    atendidos = sum(1 for r in citas if r.get("Estado Cita","").strip() == "Atendido")
    citas_validas = total_citas - cambio_fecha
    kpi9 = (atendidos/citas_validas*100) if citas_validas > 0 else 0
    e9 = estado_kpi(kpi9, 80.0)
    print(f"    KPI 9 Asistencia Citas: {kpi9:.1f}% {e9}")
    resultados.append({"kpi_id":"9","seccion":"OPERACIÓN","kpi_nombre":"Asistencia a Citas",
        "valor":round(kpi9,2),"objetivo":80.0,"unidad":"%","estado":e9})

    e10a = estado_kpi(total_atenciones, 487)
    print(f"    KPI 10a Atenciones: {total_atenciones} {e10a}")
    resultados.append({"kpi_id":"10a","seccion":"OPERACIÓN","kpi_nombre":"Atenciones Totales vs Meta",
        "valor":total_atenciones,"objetivo":487.0,"unidad":"atenciones","estado":e10a})

    e10b = estado_kpi(total_pacientes, 415)
    print(f"    KPI 10b Pacientes Únicos: {total_pacientes} {e10b}")
    resultados.append({"kpi_id":"10b","seccion":"OPERACIÓN","kpi_nombre":"Pacientes Únicos Atendidos",
        "valor":total_pacientes,"objetivo":415.0,"unidad":"pacientes","estado":e10b})

    kpi11 = facturacion_total/3
    e11 = estado_kpi(kpi11, 10986906)
    print(f"    KPI 11 Prod/Sillón: ${kpi11:,.0f} {e11}")
    resultados.append({"kpi_id":"11","seccion":"OPERACIÓN","kpi_nombre":"Producción por Sillón",
        "valor":round(kpi11,2),"objetivo":10986906.0,"unidad":"CLP","estado":e11})

    # --------------------------------------------------------
    # SECCIÓN MIX DE SERVICIOS
    # --------------------------------------------------------
    print("\n  [MIX DE SERVICIOS]")

    for cat, monto in sorted(facturacion_por_categoria.items(), key=lambda x: -x[1]):
        if not cat: continue
        pct = (monto/facturacion_total*100) if facturacion_total > 0 else 0
        resultados_mix.append({"categoria":cat,"ingresos":round(monto,2),
            "pct_real":round(pct,2),"pct_historico":0.0,"objetivo_ingresos":None})

    print(f"    KPI 12 Mix: {len(resultados_mix)} categorías, total ${facturacion_total:,.0f}")
    resultados.append({"kpi_id":"12","seccion":"MIX DE SERVICIOS","kpi_nombre":"Mix de Ingresos por Categoría",
        "valor":round(facturacion_total,2),"objetivo":None,"unidad":"CLP","estado":"ℹ️"})

    # KPI 13 — Casos Nuevos Ortodoncia
    pacs_orto = set()
    for row in acciones:
        pid = row.get("# Paciente","").strip()
        cat = row.get("Nombre Categoria","").strip().upper()
        prest = row.get("Nombre Prestación","").strip().lower()
        es_orto_cat = cat in ["ORTODONCIA","ACCIONES DE ORTODONCIA","ESPECIALIDAD"]
        if pid and ("pack ortodoncia" in prest or (es_orto_cat and (prest.startswith("instalación") or prest.startswith("instalacion")))):
            pacs_orto.add(pid)

    e13 = estado_kpi(len(pacs_orto), 12)
    print(f"    KPI 13 Casos Ortodoncia: {len(pacs_orto)} {e13}")
    resultados.append({"kpi_id":"13","seccion":"MIX DE SERVICIOS","kpi_nombre":"Volumen Casos Nuevos Ortodoncia",
        "valor":len(pacs_orto),"objetivo":12.0,"unidad":"casos","estado":e13})

    # KPI 14 — Casos Nuevos Implantes
    patron_pieza = re.compile(r"^\d+:[a-záéíóúA-Z,]+", re.IGNORECASE)
    primera_ap = {}
    hist_ord = sorted(historico, key=lambda x: (
        int(x.get("Año de realización","2025") or 2025),
        ORDEN_MESES.get(x.get("Mes de realización","").strip(), 0)
    ))
    for row in hist_ord:
        cat = row.get("Nombre Categoria","").strip().upper()
        if cat not in ["IMPLANTOLOGIA","IMPLANTOLOGÍA"]: continue
        pid = row.get("# Paciente","").strip()
        pieza = row.get("Pieza Tratada","").strip()
        anio_h = row.get("Año de realización","").strip()
        mes_h = row.get("Mes de realización","").strip()
        if not pieza or not patron_pieza.match(pieza): continue
        key = (pid, pieza)
        if key not in primera_ap:
            primera_ap[key] = (anio_h, mes_h)

    casos_impl = [k for k,(a,m) in primera_ap.items() if str(anio) in str(a) and mes_nombre.lower() in m.lower()]
    e14 = estado_kpi(len(casos_impl), 11)
    print(f"    KPI 14 Casos Implantes: {len(casos_impl)} {e14}")
    resultados.append({"kpi_id":"14","seccion":"MIX DE SERVICIOS","kpi_nombre":"Volumen Casos Nuevos Implantes",
        "valor":len(casos_impl),"objetivo":11.0,"unidad":"casos","estado":e14})

    # --------------------------------------------------------
    # SECCIÓN DOCTORES
    # --------------------------------------------------------
    print("\n  [DOCTORES]")

    doctor_data = defaultdict(lambda: {"gen":0,"cap":0})
    for row in trat_generados:
        if limpiar_monto(row.get("Total Presupuesto","0")) == 0: continue
        nombre = row.get("Nombre Profesional Tratamiento","").strip()
        apellido = row.get("Apellidos Profesional Tratamiento","").strip()
        dk = normalizar_doctor(nombre, apellido)
        doctor_data[dk]["gen"] += 1
        if row.get("Tratamiento Capturado","").strip() == "Capturado":
            doctor_data[dk]["cap"] += 1

    for doctor in DOCTORES_ACTIVOS:
        data = doctor_data.get(doctor, {"gen":0,"cap":0})
        gen = data["gen"]; cap = data["cap"]
        tasa = (cap/gen*100) if gen > 0 else None
        esp = ESPECIALIDAD_DOCTOR.get(doctor, "General")
        obj_tasa = OBJETIVO_TASA_CIERRE.get(esp, 70.0)
        resultados_doctores.append({
            "doctor":doctor,"especialidad":esp,
            "presupuestos_generados":gen,"presupuestos_capturados":cap,
            "tasa_cierre":round(tasa,2) if tasa is not None else None,
            "objetivo_tasa_cierre":obj_tasa,
            "ingresos":round(facturacion_por_doctor.get(doctor,0),2),
            "objetivo_ingresos":None,
            "pct_historico":PCT_HISTORICO_DOCTOR.get(doctor,0),
        })

    print(f"    KPI 15+16 Doctores: {len(resultados_doctores)}")
    resultados.append({"kpi_id":"15+16","seccion":"DOCTORES","kpi_nombre":"Presupuestos y Tasa Cierre por Doctor",
        "valor":None,"objetivo":None,"unidad":"%","estado":"ℹ️","nota":"Ver tabla por doctor"})
    resultados.append({"kpi_id":"17","seccion":"DOCTORES","kpi_nombre":"Productividad por Doctor",
        "valor":None,"objetivo":None,"unidad":"CLP","estado":"ℹ️","nota":"Ver tabla por doctor"})

    # --------------------------------------------------------
    # SECCIÓN FINANCIERO
    # --------------------------------------------------------
    print("\n  [FINANCIERO]")

    total_ing_chipax = 0.0
    total_otros_ing = 0.0
    total_costos_fijos = 0.0
    total_gastos_var = 0.0

    for row in chipax_rows:
        vals = list(row.values())
        if not vals: continue
        concepto = str(vals[0]).strip()
        try: val = limpiar_monto(vals[1]) if len(vals) > 1 else 0
        except: val = 0

        if "Total Ingresos" in concepto and "Otros" not in concepto:
            total_ing_chipax = val
        elif "Total Otros Ingresos" in concepto:
            total_otros_ing = val
        elif "Total Costos" in concepto:
            total_costos_fijos = abs(val)
        elif "Total Gastos" in concepto:
            total_gastos_var = abs(val)

    ingresos_chipax = total_ing_chipax + total_otros_ing
    resultado_op = ingresos_chipax - total_costos_fijos - total_gastos_var
    margen = (resultado_op/ingresos_chipax*100) if ingresos_chipax > 0 else None

    print(f"    Ingresos Chipax: ${ingresos_chipax:,.0f}")
    print(f"    Resultado Op: ${resultado_op:,.0f}")
    print(f"    Margen: {margen:.1f}%" if margen else "    Margen: N/D")

    resultados.append({"kpi_id":"18","seccion":"FINANCIERO","kpi_nombre":"Facturación Real vs Presupuesto",
        "valor":round(ingresos_chipax,2),"objetivo":None,"objetivo_texto":"Presupuesto mensual",
        "unidad":"CLP","estado":"ℹ️","nota":"Ver presupuesto_anual para objetivo del mes"})
    resultados.append({"kpi_id":"19","seccion":"FINANCIERO","kpi_nombre":"Margen Operacional",
        "valor":round(margen,2) if margen else None,"objetivo":None,
        "objetivo_texto":"Variable según presupuesto mensual","unidad":"%","estado":"ℹ️"})
    resultados.append({"kpi_id":"20","seccion":"FINANCIERO","kpi_nombre":"Comparativa vs Mes Anterior",
        "valor":None,"objetivo":None,"valor_texto":"Calculado vs mes anterior en dashboard",
        "unidad":"%","estado":"ℹ️","nota":"Verde ≥-5% | Amarillo -5% a -15% | Rojo <-15%"})

    # --------------------------------------------------------
    # SECCIÓN PROGRAMAS COMERCIALES
    # --------------------------------------------------------
    print("\n  [PROGRAMAS COMERCIALES]")

    ing_club = facturacion_por_convenio.get("CLUB SONRISA CEO", 0)
    ing_club_otros = ing_club - facturacion_ortodoncia_club
    at_club = len(atenciones_por_convenio.get("CLUB SONRISA CEO", set()))
    pct_otros = (ing_club_otros/ing_club*100) if ing_club > 0 else 0

    e21a = estado_kpi(ing_club, 17849110)
    print(f"    KPI 21a Club Sonrisa: ${ing_club:,.0f} {e21a}")
    resultados.append({"kpi_id":"21a","seccion":"PROGRAMAS COMERCIALES","kpi_nombre":"Ingresos Club Sonrisa CEO",
        "valor":round(ing_club,2),"objetivo":17849110.0,"unidad":"CLP","estado":e21a,
        "nota":f"Ortodoncia: ${facturacion_ortodoncia_club:,.0f} | Otros: ${ing_club_otros:,.0f} | %Otros: {pct_otros:.1f}%"})

    socios_ids = set()
    pids_activos_santiago = set()
    for row in pacientes_todos:
        conv = row.get("Convenio","").strip().upper()
        pid = row.get("# Paciente","").strip()
        if conv in [c.upper() for c in CONVENIOS_SANTIAGO]:
            pids_activos_santiago.add(pid)
        if conv == "CLUB SONRISA CEO":
            socios_ids.add(pid)

    pids_historico = set(r.get("# Paciente","").strip() for r in historico)
    pacs_activos_stgo = pids_activos_santiago & pids_historico
    kpi21b = (len(socios_ids)/len(pacs_activos_stgo)*100) if pacs_activos_stgo else 0
    e21b = estado_kpi(kpi21b, 70.0)
    print(f"    KPI 21b Afiliación: {kpi21b:.1f}% {e21b}")
    resultados.append({"kpi_id":"21b","seccion":"PROGRAMAS COMERCIALES","kpi_nombre":"Tasa de Afiliación Club Sonrisa CEO",
        "valor":round(kpi21b,2),"objetivo":70.0,"unidad":"%","estado":e21b,
        "nota":f"{len(socios_ids)} socios / {len(pacs_activos_stgo)} pacientes activos"})

    # KPI 21c — Retorno 6 meses
    meses_ventana = set()
    m_temp, a_temp = mes, anio
    for _ in range(6):
        meses_ventana.add(f"{a_temp}-{NOMBRES_MESES.get(m_temp,'')}")
        m_temp -= 1
        if m_temp == 0: m_temp = 12; a_temp -= 1

    tratos_socio = defaultdict(set)
    for row in historico:
        pid = row.get("# Paciente","").strip()
        trat = row.get("# Tratamiento","").strip()
        a_h = row.get("Año de realización","").strip()
        m_h = row.get("Mes de realización","").strip()
        if pid in socios_ids and f"{a_h}-{m_h}" in meses_ventana and trat:
            tratos_socio[pid].add(trat)

    retorno = sum(1 for p in socios_ids if len(tratos_socio.get(p,set())) >= 2)
    en_proceso = sum(1 for p in socios_ids if len(tratos_socio.get(p,set())) == 1)
    sin_act = len(socios_ids) - retorno - en_proceso
    kpi21c = (retorno/len(socios_ids)*100) if socios_ids else 0
    e21c = estado_kpi(kpi21c, 60.0)
    print(f"    KPI 21c Retorno: {kpi21c:.1f}% {e21c}")
    resultados.append({"kpi_id":"21c","seccion":"PROGRAMAS COMERCIALES","kpi_nombre":"Tasa de Retorno Club Sonrisa CEO",
        "valor":round(kpi21c,2),"objetivo":60.0,"unidad":"%","estado":e21c,
        "nota":f"Retorno: {retorno} | En proceso: {en_proceso} | Sin actividad: {sin_act}"})

    resultado_club = {
        "total_socios":len(socios_ids),"socios_retorno":retorno,
        "socios_en_proceso":en_proceso,"socios_sin_actividad":sin_act,
        "ingresos_ortodoncia":round(facturacion_ortodoncia_club,2),
        "ingresos_otros":round(ing_club_otros,2),"ingresos_total":round(ing_club,2),
        "atenciones_ortodoncia":len(atenciones_ortodoncia_club),
        "atenciones_otros":at_club - len(atenciones_ortodoncia_club),
    }

    # KPI 22 — Referidos
    e22 = estado_kpi(len(pacientes_referidos), 3)
    print(f"    KPI 22 Referidos: {len(pacientes_referidos)} {e22}")
    resultados.append({"kpi_id":"22","seccion":"PROGRAMAS COMERCIALES","kpi_nombre":"Pacientes Nuevos Referidos (Recomienda CEO)",
        "valor":len(pacientes_referidos),"objetivo":3.0,"unidad":"pacientes","estado":e22})

    # KPI 23 — Ingresos Referidos
    ing_ref = canales_ingresos.get("Recomienda CEO", 0)
    e23 = estado_kpi(ing_ref, 600000)
    print(f"    KPI 23 Ingresos Referidos: ${ing_ref:,.0f} {e23}")
    resultados.append({"kpi_id":"23","seccion":"PROGRAMAS COMERCIALES","kpi_nombre":"Ingresos Atribuidos Recomienda CEO",
        "valor":round(ing_ref,2),"objetivo":600000.0,"unidad":"CLP","estado":e23})

    return resultados, resultados_doctores, resultados_mix, resultado_club, resultados_trazabilidad


# ============================================================
# GUARDAR EN SUPABASE
# ============================================================

def guardar_en_supabase(anio, mes, resultados, doctores, mix, club, trazabilidad):
    print(f"\n  [SUPABASE] Guardando {len(resultados)} KPIs...")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    supabase.table("periodos").upsert({
        "anio":anio,"mes":mes,"mes_nombre":NOMBRES_MESES.get(mes,""),
        "fecha_procesado":datetime.now().isoformat()
    }).execute()

    for kpi in resultados:
        supabase.table("kpis").upsert({
            "anio":anio,"mes":mes,
            "seccion":kpi.get("seccion"),
            "kpi_id":kpi.get("kpi_id"),
            "kpi_nombre":kpi.get("kpi_nombre"),
            "valor":kpi.get("valor"),
            "valor_texto":kpi.get("valor_texto"),
            "objetivo":kpi.get("objetivo"),
            "objetivo_texto":kpi.get("objetivo_texto"),
            "unidad":kpi.get("unidad"),
            "estado":kpi.get("estado"),
            "es_valido":kpi.get("es_valido", True),
            "nota":kpi.get("nota"),
        }).execute()

    for doc in doctores:
        supabase.table("kpi_doctores").upsert({"anio":anio,"mes":mes,**doc}).execute()

    for cat in mix:
        supabase.table("kpi_mix_categorias").upsert({"anio":anio,"mes":mes,**cat}).execute()

    if club:
        supabase.table("kpi_club_sonrisa").upsert({"anio":anio,"mes":mes,**club}).execute()

    for t in trazabilidad:
        supabase.table("kpi_trazabilidad").upsert({"anio":anio,"mes":mes,**t}).execute()

    print(f"  ✅ Guardado correctamente")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Uso: python importador.py <anio> <mes> <carpeta_datos> [carpeta_historico]")
        sys.exit(1)

    anio = int(sys.argv[1])
    mes = int(sys.argv[2])
    carpeta_datos = sys.argv[3]
    carpeta_historico = sys.argv[4] if len(sys.argv) > 4 else "./datos/historico"

    print(f"\n🦷 IMPORTADOR CMI v2.0 — CEO CLÍNICA DENTAL")
    print(f"   Período: {NOMBRES_MESES.get(mes,'')} {anio}")

    res, docs, mix, club, traz = calcular_kpis(anio, mes, carpeta_datos, carpeta_historico)
    guardar_en_supabase(anio, mes, res, docs, mix, club, traz)

    print(f"\n✅ COMPLETADO — {NOMBRES_MESES.get(mes,'')} {anio}")
    print(f"   KPIs calculados: {len(res)}")
