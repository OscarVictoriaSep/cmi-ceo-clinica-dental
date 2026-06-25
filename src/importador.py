"""
IMPORTADOR CMI — CEO CLÍNICA DENTAL SANTIAGO
Versión: 1.0 | Julio 2026
Calcula los 26 KPIs del CMI y los guarda en Supabase
"""

import os
import csv
import re
import json
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

# ============================================================
# UTILIDADES
# ============================================================

def limpiar_monto(valor):
    if not valor:
        return 0.0
    try:
        return float(str(valor).replace("$","").replace(".","").replace(",",".").strip())
    except:
        return 0.0

def leer_csv(ruta, delimiter=";", skip_first=False):
    rows = []
    try:
        with open(ruta, encoding="utf-8-sig") as f:
            if skip_first:
                next(f)
            reader = csv.DictReader(f, delimiter=delimiter)
            for row in reader:
                rows.append(row)
    except Exception as e:
        print(f"  ⚠️  Error leyendo {ruta}: {e}")
    return rows

def normalizar_nombre_doctor(nombre, apellido):
    return f"{nombre} {apellido}".strip().upper()

def estado_kpi(valor, objetivo, mayor_mejor=True, umbral_amarillo=None):
    if valor is None or objetivo is None:
        return "⚠️"
    if mayor_mejor:
        if valor >= objetivo:
            return "✅"
        elif umbral_amarillo and valor >= umbral_amarillo:
            return "🟡"
        return "🔴"
    else:
        if valor <= objetivo:
            return "✅"
        return "🔴"

# ============================================================
# CÁLCULO DE KPIs
# ============================================================

def calcular_kpis(anio, mes, carpeta_datos, carpeta_historico):
    resultados = []
    resultados_doctores = []
    resultados_mix = []
    resultado_club = {}
    resultados_trazabilidad = []

    mes_str = str(mes).zfill(2)
    anio_str = str(anio)[-2:]

    print(f"\n{'='*60}")
    print(f"  CMI CEO CLÍNICA DENTAL — {mes}/{anio}")
    print(f"{'='*60}")

    # Rutas de archivos
    def ruta(nombre):
        return os.path.join(carpeta_datos, nombre)

    hist_acciones = os.path.join(carpeta_historico, "historico_acciones_realizadas.csv")

    # --------------------------------------------------------
    # LEER ARCHIVOS PRINCIPALES
    # --------------------------------------------------------

    # Acciones realizadas del mes
    acciones = leer_csv(ruta(f"1.4_Acciones_Realizadas_{mes}.{anio_str}.csv"), delimiter=";", skip_first=True)
    if not acciones:
        acciones = leer_csv(ruta(f"1.4_Acciones_Realizadas_{mes}.{anio_str}.csv"), delimiter=",")
    print(f"  1.4 Acciones Realizadas: {len(acciones)} filas")

    # Agenda citas
    citas = leer_csv(ruta(f"2.1_Agenda_Citas_{mes}.{anio_str}.csv"), delimiter=";", skip_first=True)
    if not citas:
        citas = leer_csv(ruta(f"2.1_Agenda_Citas_{mes}.{anio_str}.csv"), delimiter=",")
    print(f"  2.1 Agenda Citas: {len(citas)} filas")

    # Sistema seguimiento
    seguimiento = leer_csv(ruta(f"1.2_Sistema_Seguimiento_Presupuestos_{mes}.{anio_str}.csv"), delimiter=";", skip_first=True)
    if not seguimiento:
        seguimiento = leer_csv(ruta(f"1.2_Sistema_Seguimiento_Presupuestos_{mes}.{anio_str}.csv"), delimiter=",")

    # Pacientes nuevos
    pacientes_nuevos = leer_csv(ruta(f"1.3_Pacientes_Nuevos_{mes}.{anio_str}.csv"), delimiter=";", skip_first=True)
    if not pacientes_nuevos:
        pacientes_nuevos = leer_csv(ruta(f"1.3_Pacientes_Nuevos_{mes}.{anio_str}.csv"), delimiter=",")
    print(f"  1.3 Pacientes Nuevos: {len(pacientes_nuevos)} filas")

    # Presupuestos capturados
    presupuestos = leer_csv(ruta(f"2.2_Presupuestos_Capturados_{mes}.{anio_str}.csv"), delimiter=";", skip_first=True)
    if not presupuestos:
        presupuestos = leer_csv(ruta(f"2.2_Presupuestos_Capturados_{mes}.{anio_str}.csv"), delimiter=",")

    # Resultado operacional Chipax
    chipax = leer_csv(ruta(f"5.1_Resultado_Operacional_{mes}.{anio_str}.csv"), delimiter=",")

    # Pacientes todos
    pacientes_todos = leer_csv(ruta(f"6.1_Pacientes_Todos_{mes}.{anio_str}.csv"), delimiter=";", skip_first=True)
    if not pacientes_todos:
        pacientes_todos = leer_csv(ruta(f"6.1_Pacientes_Todos_{mes}.{anio_str}.csv"), delimiter=",")

    # Histórico acciones
    historico = leer_csv(hist_acciones, delimiter=";", skip_first=True)
    if not historico:
        historico = leer_csv(hist_acciones, delimiter=",")
    print(f"  Histórico: {len(historico)} filas")

    # --------------------------------------------------------
    # PRECÁLCULOS COMUNES
    # --------------------------------------------------------

    # Atenciones únicas y facturación del mes
    atenciones_unicas = set()
    pacientes_unicos = set()
    facturacion_total = 0.0
    facturacion_por_convenio = defaultdict(float)
    atenciones_por_convenio = defaultdict(set)
    facturacion_ortodoncia_club = 0.0
    atenciones_ortodoncia_club = set()
    facturacion_por_doctor = defaultdict(float)
    facturacion_por_categoria = defaultdict(float)
    tratamientos_por_paciente_mes = defaultdict(set)

    nombres_mes = {v: k for k, v in ORDEN_MESES.items()}
    mes_nombre = nombres_mes.get(mes, "")

    for row in acciones:
        pid = row.get("# Paciente", "").strip()
        fecha = row.get("Fecha de realización", "").strip()
        convenio = row.get("Convenio Paciente", "").strip().upper()
        categoria = row.get("Nombre Categoria", "").strip().upper()
        prestacion = row.get("Nombre Prestación", "").strip()
        trat_id = row.get("# Tratamiento", "").strip()
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

        # Club Sonrisa separar ortodoncia
        if convenio == "CLUB SONRISA CEO":
            es_orto = categoria in ["ORTODONCIA", "ACCIONES DE ORTODONCIA"]
            if categoria == "ESPECIALIDAD":
                p_lower = prestacion.lower()
                es_orto = any(x in p_lower for x in ["instalac", "control", "aparato", "contencion", "ortodoncia", "pack ortodoncia"])
            if es_orto:
                facturacion_ortodoncia_club += monto
                if pid and fecha:
                    atenciones_ortodoncia_club.add((pid, fecha))

        # Por doctor
        if nombre_doc:
            doctor_key = normalizar_nombre_doctor(nombre_doc, apellido_doc)
            facturacion_por_doctor[doctor_key] += monto

        # Por categoría
        facturacion_por_categoria[categoria] += monto

        # Tratamientos por paciente
        if pid and trat_id:
            tratamientos_por_paciente_mes[pid].add(trat_id)

    total_atenciones = len(atenciones_unicas)
    total_pacientes = len(pacientes_unicos)

    # --------------------------------------------------------
    # SECCIÓN COMERCIAL
    # --------------------------------------------------------
    print("\n  [COMERCIAL]")

    # KPI 1 — Tasa Cierre Presupuestos
    kpi1_valor = None
    kpi1_gen = 0
    kpi1_cap = 0
    mes_key = f"{mes_nombre.lower()[:3]}/{anio}"
    for row in presupuestos:
        for k, v in row.items():
            if k and mes_nombre[:3].lower() in k.lower() and str(anio) in k:
                try:
                    pct = float(str(v).replace("%","").replace(",",".").strip())
                    kpi1_valor = pct
                except:
                    pass

    if kpi1_valor is not None:
        estado1 = estado_kpi(kpi1_valor, 70.0)
        print(f"    KPI 1 Tasa Cierre: {kpi1_valor:.1f}% {estado1}")
        resultados.append({
            "kpi_id": "1", "seccion": "COMERCIAL", "kpi_nombre": "Tasa Cierre Presupuestos",
            "valor": round(kpi1_valor, 2), "objetivo": 70.0, "unidad": "%", "estado": estado1
        })

    # KPI 2 — Presupuestos Generados (desde tratamientos generados)
    trat_generados = leer_csv(ruta(f"1.1_Tratamientos_Generados_Estados_{mes}.{anio_str}.csv"), delimiter=";", skip_first=True)
    if not trat_generados:
        trat_generados = leer_csv(ruta(f"1.1_Tratamientos_Generados_Estados_{mes}.{anio_str}.csv"), delimiter=",")

    kpi2_gen = 0
    kpi2_cap = 0
    for row in trat_generados:
        total_ppto = limpiar_monto(row.get("Total Presupuesto", "0"))
        if total_ppto > 0:
            kpi2_gen += 1
            if row.get("Tratamiento Capturado", "").strip() == "Capturado":
                kpi2_cap += 1

    estado2 = estado_kpi(kpi2_gen, 230)
    print(f"    KPI 2 Presupuestos Generados: {kpi2_gen} {estado2}")
    resultados.append({
        "kpi_id": "2", "seccion": "COMERCIAL", "kpi_nombre": "Presupuestos Generados",
        "valor": kpi2_gen, "objetivo": 230.0, "unidad": "unidades", "estado": estado2
    })

    # KPI 3 — Captación por Seguimiento
    kpi3_valor = None
    mes_nombre_seg = mes_nombre
    for row in seguimiento:
        anio_seg = row.get("Año", "").strip()
        mes_seg = row.get("Mes", "").strip()
        if str(anio) in str(anio_seg) and mes_nombre_seg.lower() in mes_seg.lower():
            pct_str = row.get("% de Recuperación", "0").replace("%","").replace(",",".").strip()
            try:
                kpi3_valor = float(pct_str)
            except:
                pass

    if kpi3_valor is not None:
        estado3 = estado_kpi(kpi3_valor, 20.0)
        print(f"    KPI 3 Captación Seguimiento: {kpi3_valor:.1f}% {estado3}")
        resultados.append({
            "kpi_id": "3", "seccion": "COMERCIAL", "kpi_nombre": "Captación por Seguimiento",
            "valor": round(kpi3_valor, 2), "objetivo": 20.0, "unidad": "%", "estado": estado3
        })

    # KPI T — Trazabilidad
    total_pn = len(pacientes_nuevos)
    con_origen = 0
    canales = defaultdict(int)
    canales_ingresos = defaultdict(float)
    pacientes_meta = set()
    pacientes_google = set()
    pacientes_referidos = set()

    for row in pacientes_nuevos:
        ref = row.get("Referencia Paciente", "").strip().upper()
        pid = row.get("# Paciente", "").strip()
        if ref in ["REDES SOCIALES"]:
            con_origen += 1
            canales["Meta Ads"] += 1
            pacientes_meta.add(pid)
        elif ref == "GOOGLE":
            con_origen += 1
            canales["Google Ads"] += 1
            pacientes_google.add(pid)
        elif ref.startswith("REFERIDO"):
            con_origen += 1
            canales["Recomienda CEO"] += 1
            pacientes_referidos.add(pid)
        elif ref == "ORGÁNICO" or ref == "ORGANICO":
            con_origen += 1
            canales["Orgánico"] += 1
        elif ref:
            con_origen += 1
            canales["Otro"] += 1

    kpiT_valor = (con_origen / total_pn * 100) if total_pn > 0 else 0
    estadoT = estado_kpi(kpiT_valor, 90.0)
    es_valido_trazabilidad = kpiT_valor >= 90.0
    print(f"    KPI T Trazabilidad: {kpiT_valor:.1f}% {estadoT}")
    resultados.append({
        "kpi_id": "T", "seccion": "COMERCIAL", "kpi_nombre": "Trazabilidad de Origen",
        "valor": round(kpiT_valor, 2), "objetivo": 90.0, "unidad": "%",
        "estado": estadoT, "nota": "Prerequisito para CPA y ROAS"
    })

    # Inversión Meta Ads
    inversion_meta = 0.0
    meta1 = leer_csv(ruta(f"Meta_Ads_1_{mes}.{anio_str}.csv"), delimiter=",")
    meta2 = leer_csv(ruta(f"Meta_Ads_2_{mes}.{anio_str}.csv"), delimiter=",")
    for row in meta1 + meta2:
        for k, v in row.items():
            if k and "importe" in k.lower() and "gastado" in k.lower():
                inversion_meta += limpiar_monto(v)

    # Inversión Google Ads
    inversion_google = 0.0
    google = leer_csv(ruta(f"Google_Ads_{mes}.{anio_str}.csv"), delimiter=",")
    for row in google:
        for k, v in row.items():
            if k and "total" in str(row.get("Campaña", row.get("Campaign",""))).lower():
                if k and "costo" in k.lower():
                    inversion_google += limpiar_monto(v)
                    break

    # Ingresos atribuidos por canal
    for pid in pacientes_meta:
        for row in acciones:
            if row.get("# Paciente","").strip() == pid:
                canales_ingresos["Meta Ads"] += limpiar_monto(row.get("Pagado Paciente Prestación (Abonado)","0"))
    for pid in pacientes_google:
        for row in acciones:
            if row.get("# Paciente","").strip() == pid:
                canales_ingresos["Google Ads"] += limpiar_monto(row.get("Pagado Paciente Prestación (Abonado)","0"))
    for pid in pacientes_referidos:
        for row in acciones:
            if row.get("# Paciente","").strip() == pid:
                canales_ingresos["Recomienda CEO"] += limpiar_monto(row.get("Pagado Paciente Prestación (Abonado)","0"))

    # KPI 4 — CPA Meta
    n_meta = len(pacientes_meta)
    cpa_meta = (inversion_meta / n_meta) if n_meta > 0 and inversion_meta > 0 else None
    nota_cpa = "" if es_valido_trazabilidad else "⚠️ Trazabilidad <90% — dato referencial"
    print(f"    KPI 4 CPA Meta: ${cpa_meta:,.0f}" if cpa_meta else "    KPI 4 CPA Meta: N/D")
    resultados.append({
        "kpi_id": "4", "seccion": "COMERCIAL", "kpi_nombre": "CPA Meta Ads",
        "valor": round(cpa_meta, 2) if cpa_meta else None,
        "valor_texto": f"${cpa_meta:,.0f}" if cpa_meta else "N/D",
        "objetivo": None, "objetivo_texto": "Por definir",
        "unidad": "CLP", "estado": "⏳" if not es_valido_trazabilidad else "ℹ️",
        "es_valido": es_valido_trazabilidad, "nota": nota_cpa
    })

    # KPI 5 — CPA Google
    n_google = len(pacientes_google)
    cpa_google = (inversion_google / n_google) if n_google > 0 and inversion_google > 0 else None
    print(f"    KPI 5 CPA Google: ${cpa_google:,.0f}" if cpa_google else "    KPI 5 CPA Google: N/D")
    resultados.append({
        "kpi_id": "5", "seccion": "COMERCIAL", "kpi_nombre": "CPA Google Ads",
        "valor": round(cpa_google, 2) if cpa_google else None,
        "valor_texto": f"${cpa_google:,.0f}" if cpa_google else "N/D",
        "objetivo": None, "objetivo_texto": "Por definir",
        "unidad": "CLP", "estado": "⏳" if not es_valido_trazabilidad else "ℹ️",
        "es_valido": es_valido_trazabilidad, "nota": nota_cpa
    })

    # KPI 6 — ROAS Meta
    ing_meta = canales_ingresos["Meta Ads"]
    roas_meta = (ing_meta / inversion_meta) if inversion_meta > 0 else None
    estado6 = estado_kpi(roas_meta, 3.5) if roas_meta and es_valido_trazabilidad else "⚠️"
    print(f"    KPI 6 ROAS Meta: {roas_meta:.2f}x" if roas_meta else "    KPI 6 ROAS Meta: N/D")
    resultados.append({
        "kpi_id": "6", "seccion": "COMERCIAL", "kpi_nombre": "ROAS Meta Ads",
        "valor": round(roas_meta, 2) if roas_meta else None,
        "objetivo": 3.5, "unidad": "x",
        "estado": estado6, "es_valido": es_valido_trazabilidad,
        "nota": "ROAS = piso mensual. ROAS real considera LTV."
    })

    # KPI 7 — ROAS Google
    ing_google = canales_ingresos["Google Ads"]
    roas_google = (ing_google / inversion_google) if inversion_google > 0 else None
    estado7 = estado_kpi(roas_google, 3.5) if roas_google and es_valido_trazabilidad else "⚠️"
    print(f"    KPI 7 ROAS Google: {roas_google:.2f}x" if roas_google else "    KPI 7 ROAS Google: N/D")
    resultados.append({
        "kpi_id": "7", "seccion": "COMERCIAL", "kpi_nombre": "ROAS Google Ads",
        "valor": round(roas_google, 2) if roas_google else None,
        "objetivo": 3.5, "unidad": "x",
        "estado": estado7, "es_valido": es_valido_trazabilidad,
        "nota": "ROAS = piso mensual. ROAS real considera LTV."
    })

    # Guardar trazabilidad
    for canal, n in canales.items():
        inversion = inversion_meta if canal == "Meta Ads" else (inversion_google if canal == "Google Ads" else 0)
        ing = canales_ingresos.get(canal, 0)
        cpa = (inversion / n) if n > 0 and inversion > 0 else None
        roas = (ing / inversion) if inversion > 0 else None
        resultados_trazabilidad.append({
            "canal": canal, "pacientes": n,
            "ingresos": round(ing, 2),
            "inversion": round(inversion, 2),
            "cpa": round(cpa, 2) if cpa else None,
            "roas": round(roas, 2) if roas else None,
        })

    # --------------------------------------------------------
    # SECCIÓN OPERACIÓN
    # --------------------------------------------------------
    print("\n  [OPERACIÓN]")

    # KPI 8 — Ingresos por Atención
    kpi8_valor = (facturacion_total / total_atenciones) if total_atenciones > 0 else 0
    estado8 = estado_kpi(kpi8_valor, 45000)
    print(f"    KPI 8 Ingresos/Atención: ${kpi8_valor:,.0f} {estado8}")
    resultados.append({
        "kpi_id": "8", "seccion": "OPERACIÓN", "kpi_nombre": "Ingresos por Atención",
        "valor": round(kpi8_valor, 2), "objetivo": 45000.0, "unidad": "CLP", "estado": estado8
    })

    # KPI 9 — Asistencia a Citas
    total_citas = len(citas)
    cambio_fecha = sum(1 for r in citas if r.get("Estado Cita","").strip() == "Cambio de fecha")
    atendidos = sum(1 for r in citas if r.get("Estado Cita","").strip() == "Atendido")
    citas_validas = total_citas - cambio_fecha
    kpi9_valor = (atendidos / citas_validas * 100) if citas_validas > 0 else 0
    estado9 = estado_kpi(kpi9_valor, 80.0)
    print(f"    KPI 9 Asistencia Citas: {kpi9_valor:.1f}% {estado9}")
    resultados.append({
        "kpi_id": "9", "seccion": "OPERACIÓN", "kpi_nombre": "Asistencia a Citas",
        "valor": round(kpi9_valor, 2), "objetivo": 80.0, "unidad": "%", "estado": estado9
    })

    # KPI 10a — Atenciones Totales
    estado10a = estado_kpi(total_atenciones, 487)
    print(f"    KPI 10a Atenciones Totales: {total_atenciones} {estado10a}")
    resultados.append({
        "kpi_id": "10a", "seccion": "OPERACIÓN", "kpi_nombre": "Atenciones Totales vs Meta",
        "valor": total_atenciones, "objetivo": 487.0, "unidad": "atenciones", "estado": estado10a
    })

    # KPI 10b — Pacientes Únicos
    estado10b = estado_kpi(total_pacientes, 415)
    print(f"    KPI 10b Pacientes Únicos: {total_pacientes} {estado10b}")
    resultados.append({
        "kpi_id": "10b", "seccion": "OPERACIÓN", "kpi_nombre": "Pacientes Únicos Atendidos",
        "valor": total_pacientes, "objetivo": 415.0, "unidad": "pacientes", "estado": estado10b
    })

    # KPI 11 — Producción por Sillón
    kpi11_valor = facturacion_total / 3
    estado11 = estado_kpi(kpi11_valor, 10986906)
    print(f"    KPI 11 Producción/Sillón: ${kpi11_valor:,.0f} {estado11}")
    resultados.append({
        "kpi_id": "11", "seccion": "OPERACIÓN", "kpi_nombre": "Producción por Sillón",
        "valor": round(kpi11_valor, 2), "objetivo": 10986906.0, "unidad": "CLP", "estado": estado11
    })

    # --------------------------------------------------------
    # SECCIÓN MIX DE SERVICIOS
    # --------------------------------------------------------
    print("\n  [MIX DE SERVICIOS]")

    # Presupuesto del mes para calcular objetivo por categoría
    pct_historico_cat = {
        "ORTODONCIA": 26.8, "ODONTOLOGÍA GENERAL": 21.2, "Laboratorios": 12.9,
        "IMPLANTOLOGÍA": 10.5, "REHABILITACIÓN ORAL": 7.8, "ENDODONCIA": 5.3,
        "PRODUCTOS VENTAS": 2.8, "CIRUGIA ORAL": 1.8, "ALINEADORES": 0.5,
        "ODONTOLOGIA ESTETICA": 0.9, "ESTETICA FACIAL": 0.5,
    }

    for cat, monto in sorted(facturacion_por_categoria.items(), key=lambda x: -x[1]):
        if not cat:
            continue
        pct_real = (monto / facturacion_total * 100) if facturacion_total > 0 else 0
        pct_hist = pct_historico_cat.get(cat, 0)
        resultados_mix.append({
            "categoria": cat,
            "ingresos": round(monto, 2),
            "pct_real": round(pct_real, 2),
            "pct_historico": pct_hist,
            "objetivo_ingresos": None
        })

    print(f"    KPI 12 Mix categorías: {len(resultados_mix)} categorías")
    resultados.append({
        "kpi_id": "12", "seccion": "MIX DE SERVICIOS", "kpi_nombre": "Mix de Ingresos por Categoría",
        "valor": round(facturacion_total, 2), "objetivo": None,
        "unidad": "CLP", "estado": "ℹ️", "nota": "Ver tabla detalle por categoría"
    })

    # KPI 13 — Casos Nuevos Ortodoncia
    pacientes_orto_nuevos = set()
    for row in acciones:
        pid = row.get("# Paciente","").strip()
        cat = row.get("Nombre Categoria","").strip().upper()
        prestacion = row.get("Nombre Prestación","").strip().lower()
        es_orto_cat = cat in ["ORTODONCIA", "ACCIONES DE ORTODONCIA", "ESPECIALIDAD"]
        es_instalacion = prestacion.startswith("instalación") or prestacion.startswith("instalacion")
        es_pack = "pack ortodoncia" in prestacion
        if pid and (es_pack or (es_orto_cat and es_instalacion)):
            pacientes_orto_nuevos.add(pid)

    kpi13_valor = len(pacientes_orto_nuevos)
    estado13 = estado_kpi(kpi13_valor, 12)
    print(f"    KPI 13 Casos Ortodoncia: {kpi13_valor} {estado13}")
    resultados.append({
        "kpi_id": "13", "seccion": "MIX DE SERVICIOS", "kpi_nombre": "Volumen Casos Nuevos Ortodoncia",
        "valor": kpi13_valor, "objetivo": 12.0, "unidad": "casos", "estado": estado13
    })

    # KPI 14 — Casos Nuevos Implantes
    patron_pieza = re.compile(r"^\d+:[a-záéíóúüñA-Z,]+", re.IGNORECASE)
    primera_aparicion = {}

    hist_ordenado = sorted(historico, key=lambda x: (
        int(x.get("Año de realización", "2025") or 2025),
        ORDEN_MESES.get(x.get("Mes de realización","").strip(), 0)
    ))

    for row in hist_ordenado:
        cat = row.get("Nombre Categoria","").strip().upper()
        if cat not in ["IMPLANTOLOGIA", "IMPLANTOLOGÍA"]:
            continue
        pid = row.get("# Paciente","").strip()
        pieza = row.get("Pieza Tratada","").strip()
        anio_h = row.get("Año de realización","").strip()
        mes_h = row.get("Mes de realización","").strip()
        if not pieza or not patron_pieza.match(pieza):
            continue
        key = (pid, pieza)
        if key not in primera_aparicion:
            primera_aparicion[key] = (anio_h, mes_h)

    nombres_mes_map = {v: k for k, v in ORDEN_MESES.items()}
    mes_nombre_actual = nombres_mes_map.get(mes, "")

    casos_implantes_mes = [
        key for key, (a, m) in primera_aparicion.items()
        if str(anio) in str(a) and mes_nombre_actual.lower() in m.lower()
    ]
    kpi14_valor = len(casos_implantes_mes)
    estado14 = estado_kpi(kpi14_valor, 11)
    print(f"    KPI 14 Casos Implantes: {kpi14_valor} {estado14}")
    resultados.append({
        "kpi_id": "14", "seccion": "MIX DE SERVICIOS", "kpi_nombre": "Volumen Casos Nuevos Implantes",
        "valor": kpi14_valor, "objetivo": 11.0, "unidad": "casos", "estado": estado14
    })

    # --------------------------------------------------------
    # SECCIÓN DOCTORES
    # --------------------------------------------------------
    print("\n  [DOCTORES]")

    # KPI 15+16 — Tasa Cierre por Doctor
    doctor_data = defaultdict(lambda: {"gen": 0, "cap": 0})
    for row in trat_generados:
        total_ppto = limpiar_monto(row.get("Total Presupuesto","0"))
        if total_ppto == 0:
            continue
        nombre = row.get("Nombre Profesional Tratamiento","").strip()
        apellido = row.get("Apellidos Profesional Tratamiento","").strip()
        doctor = normalizar_nombre_doctor(nombre, apellido)
        capturado = row.get("Tratamiento Capturado","").strip()
        doctor_data[doctor]["gen"] += 1
        if capturado == "Capturado":
            doctor_data[doctor]["cap"] += 1

    for doctor in DOCTORES_ACTIVOS:
        data = doctor_data.get(doctor, {"gen": 0, "cap": 0})
        gen = data["gen"]
        cap = data["cap"]
        tasa = (cap / gen * 100) if gen > 0 else None
        esp = ESPECIALIDAD_DOCTOR.get(doctor, "General")
        obj_tasa = OBJETIVO_TASA_CIERRE.get(esp, 70.0)
        pct_hist = PCT_HISTORICO_DOCTOR.get(doctor, 0)

        resultados_doctores.append({
            "doctor": doctor,
            "especialidad": esp,
            "presupuestos_generados": gen,
            "presupuestos_capturados": cap,
            "tasa_cierre": round(tasa, 2) if tasa is not None else None,
            "objetivo_tasa_cierre": obj_tasa,
            "ingresos": round(facturacion_por_doctor.get(doctor, 0), 2),
            "objetivo_ingresos": None,
            "pct_historico": pct_hist,
        })

    print(f"    KPI 15+16 Doctores procesados: {len(resultados_doctores)}")
    resultados.append({
        "kpi_id": "15+16", "seccion": "DOCTORES",
        "kpi_nombre": "Presupuestos y Tasa Cierre por Doctor",
        "valor": None, "objetivo": None,
        "unidad": "%", "estado": "ℹ️", "nota": "Ver tabla detalle por doctor"
    })

    # KPI 17 — Productividad por Doctor
    resultados.append({
        "kpi_id": "17", "seccion": "DOCTORES",
        "kpi_nombre": "Productividad por Doctor",
        "valor": None, "objetivo": None,
        "unidad": "CLP", "estado": "ℹ️", "nota": "Ver tabla detalle por doctor"
    })

    # --------------------------------------------------------
    # SECCIÓN FINANCIERO
    # --------------------------------------------------------
    print("\n  [FINANCIERO]")

    # Leer Chipax
    total_ing_chipax = 0.0
    total_otros_ing = 0.0
    resultado_op = 0.0
    total_costos_fijos = 0.0
    total_gastos_var = 0.0

    for row in chipax:
        linea = list(row.values())
        if not linea:
            continue
        concepto = str(linea[0]).strip() if linea else ""
        try:
            valor_chipax = limpiar_monto(linea[1]) if len(linea) > 1 else 0
        except:
            valor_chipax = 0

        if "Total Ingresos" in concepto and "Otros" not in concepto:
            total_ing_chipax = valor_chipax
        elif "Total Otros Ingresos" in concepto:
            total_otros_ing = valor_chipax
        elif "Total Costos" in concepto:
            total_costos_fijos = abs(valor_chipax)
        elif "Total Gastos" in concepto:
            total_gastos_var = abs(valor_chipax)

    ingresos_chipax = total_ing_chipax + total_otros_ing
    resultado_op = ingresos_chipax - total_costos_fijos - total_gastos_var

    # KPI 18 — Facturación vs Presupuesto
    kpi18_valor = (ingresos_chipax / None * 100) if ingresos_chipax else None
    resultados.append({
        "kpi_id": "18", "seccion": "FINANCIERO",
        "kpi_nombre": "Facturación Real vs Presupuesto",
        "valor": round(ingresos_chipax, 2),
        "valor_texto": f"${ingresos_chipax:,.0f}",
        "objetivo": None, "objetivo_texto": "Presupuesto mensual",
        "unidad": "CLP", "estado": "ℹ️",
        "nota": "Ver presupuesto_anual para objetivo del mes"
    })

    # KPI 19 — Margen Operacional
    margen_real = (resultado_op / ingresos_chipax * 100) if ingresos_chipax > 0 else None
    print(f"    KPI 19 Margen: {margen_real:.1f}%" if margen_real else "    KPI 19 Margen: N/D")
    resultados.append({
        "kpi_id": "19", "seccion": "FINANCIERO",
        "kpi_nombre": "Margen Operacional",
        "valor": round(margen_real, 2) if margen_real else None,
        "objetivo": None, "objetivo_texto": "Variable según presupuesto mensual",
        "unidad": "%", "estado": "ℹ️",
        "nota": "Objetivo varía por mes según presupuesto anual"
    })

    # KPI 20 — Comparativa vs Mes Anterior
    resultados.append({
        "kpi_id": "20", "seccion": "FINANCIERO",
        "kpi_nombre": "Comparativa vs Mes Anterior",
        "valor": None, "objetivo": None,
        "valor_texto": "Calculado en dashboard vs mes anterior",
        "unidad": "%", "estado": "ℹ️",
        "nota": "Verde ≥-5% | Amarillo -5% a -15% | Rojo <-15%"
    })

    # --------------------------------------------------------
    # SECCIÓN PROGRAMAS COMERCIALES
    # --------------------------------------------------------
    print("\n  [PROGRAMAS COMERCIALES]")

    # KPI 21a — Ingresos Club Sonrisa
    ing_club_total = facturacion_por_convenio.get("CLUB SONRISA CEO", 0)
    ing_club_otros = ing_club_total - facturacion_ortodoncia_club
    at_club_total = len(atenciones_por_convenio.get("CLUB SONRISA CEO", set()))
    at_club_otros = at_club_total - len(atenciones_ortodoncia_club)
    pct_otros_club = (ing_club_otros / ing_club_total * 100) if ing_club_total > 0 else 0

    estado21a_otros = estado_kpi(ing_club_otros, 12754839)
    estado21a_orto = estado_kpi(facturacion_ortodoncia_club, 5094270)
    estado21a_total = estado_kpi(ing_club_total, 17849110)
    estado21a_pct = estado_kpi(pct_otros_club, 70.0)

    print(f"    KPI 21a Club Sonrisa Total: ${ing_club_total:,.0f}")
    print(f"    KPI 21a Otros: ${ing_club_otros:,.0f} {estado21a_otros}")

    resultados.append({
        "kpi_id": "21a", "seccion": "PROGRAMAS COMERCIALES",
        "kpi_nombre": "Ingresos Club Sonrisa CEO",
        "valor": round(ing_club_total, 2),
        "objetivo": 17849110.0, "unidad": "CLP", "estado": estado21a_total,
        "nota": f"Ortodoncia: ${facturacion_ortodoncia_club:,.0f} | Otros: ${ing_club_otros:,.0f} | %Otros: {pct_otros_club:.1f}%"
    })

    resultado_club = {
        "total_socios": 0,
        "socios_retorno": 0,
        "socios_en_proceso": 0,
        "socios_sin_actividad": 0,
        "ingresos_ortodoncia": round(facturacion_ortodoncia_club, 2),
        "ingresos_otros": round(ing_club_otros, 2),
        "ingresos_total": round(ing_club_total, 2),
        "atenciones_ortodoncia": len(atenciones_ortodoncia_club),
        "atenciones_otros": at_club_otros,
    }

    # KPI 21b — Tasa Afiliación
    socios_ids = set()
    pacientes_activos_ids = set()

    for row in pacientes_todos:
        conv = row.get("Convenio","").strip().upper()
        pid = row.get("# Paciente","").strip()
        if conv in [c.upper() for c in CONVENIOS_SANTIAGO]:
            pacientes_activos_ids.add(pid)
        if conv == "CLUB SONRISA CEO":
            socios_ids.add(pid)

    # Socios activos = en histórico últimos 12 meses
    pids_historico = set(r.get("# Paciente","").strip() for r in historico)
    pacientes_activos_santiago = pacientes_activos_ids & pids_historico
    socios_activos = socios_ids

    kpi21b_valor = (len(socios_activos) / len(pacientes_activos_santiago) * 100) if pacientes_activos_santiago else 0
    estado21b = estado_kpi(kpi21b_valor, 70.0)
    print(f"    KPI 21b Afiliación Club: {kpi21b_valor:.1f}% {estado21b}")
    resultados.append({
        "kpi_id": "21b", "seccion": "PROGRAMAS COMERCIALES",
        "kpi_nombre": "Tasa de Afiliación Club Sonrisa CEO",
        "valor": round(kpi21b_valor, 2),
        "objetivo": 70.0, "unidad": "%", "estado": estado21b,
        "nota": f"{len(socios_activos)} socios / {len(pacientes_activos_santiago)} pacientes activos"
    })
    resultado_club["total_socios"] = len(socios_activos)

    # KPI 21c — Tasa de Retorno (ventana 6 meses)
    meses_ventana = set()
    mes_actual = mes
    anio_actual = anio
    for _ in range(6):
        nombre_m = nombres_mes_map.get(mes_actual, "")
        meses_ventana.add(f"{anio_actual}-{nombre_m}")
        mes_actual -= 1
        if mes_actual == 0:
            mes_actual = 12
            anio_actual -= 1

    tratamientos_socio_ventana = defaultdict(set)
    for row in historico:
        pid = row.get("# Paciente","").strip()
        trat = row.get("# Tratamiento","").strip()
        anio_h = row.get("Año de realización","").strip()
        mes_h = row.get("Mes de realización","").strip()
        mes_key_h = f"{anio_h}-{mes_h}"
        if pid in socios_activos and mes_key_h in meses_ventana and trat:
            tratamientos_socio_ventana[pid].add(trat)

    socios_retorno = sum(1 for pid in socios_activos if len(tratamientos_socio_ventana.get(pid, set())) >= 2)
    socios_en_proceso = sum(1 for pid in socios_activos if len(tratamientos_socio_ventana.get(pid, set())) == 1)
    socios_sin_act = len(socios_activos) - socios_retorno - socios_en_proceso

    kpi21c_valor = (socios_retorno / len(socios_activos) * 100) if socios_activos else 0
    estado21c = estado_kpi(kpi21c_valor, 60.0)
    print(f"    KPI 21c Retorno Club: {kpi21c_valor:.1f}% {estado21c}")
    resultados.append({
        "kpi_id": "21c", "seccion": "PROGRAMAS COMERCIALES",
        "kpi_nombre": "Tasa de Retorno Club Sonrisa CEO",
        "valor": round(kpi21c_valor, 2),
        "objetivo": 60.0, "unidad": "%", "estado": estado21c,
        "nota": f"Retorno: {socios_retorno} | En proceso: {socios_en_proceso} | Sin actividad: {socios_sin_act}"
    })
    resultado_club.update({
        "socios_retorno": socios_retorno,
        "socios_en_proceso": socios_en_proceso,
        "socios_sin_actividad": socios_sin_act
    })

    # KPI 22 — Referidos Recomienda CEO
    kpi22_valor = len(pacientes_referidos)
    estado22 = estado_kpi(kpi22_valor, 3)
    print(f"    KPI 22 Referidos: {kpi22_valor} {estado22}")
    resultados.append({
        "kpi_id": "22", "seccion": "PROGRAMAS COMERCIALES",
        "kpi_nombre": "Pacientes Nuevos Referidos (Recomienda CEO)",
        "valor": kpi22_valor, "objetivo": 3.0, "unidad": "pacientes", "estado": estado22
    })

    # KPI 23 — Ingresos Referidos
    ing_referidos = canales_ingresos.get("Recomienda CEO", 0)
    estado23 = estado_kpi(ing_referidos, 600000)
    print(f"    KPI 23 Ingresos Referidos: ${ing_referidos:,.0f} {estado23}")
    resultados.append({
        "kpi_id": "23", "seccion": "PROGRAMAS COMERCIALES",
        "kpi_nombre": "Ingresos Atribuidos Recomienda CEO",
        "valor": round(ing_referidos, 2), "objetivo": 600000.0,
        "unidad": "CLP", "estado": estado23
    })

    return resultados, resultados_doctores, resultados_mix, resultado_club, resultados_trazabilidad


# ============================================================
# GUARDAR EN SUPABASE
# ============================================================

def guardar_en_supabase(anio, mes, resultados, doctores, mix, club, trazabilidad):
    print(f"\n  [SUPABASE] Guardando datos...")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    mes_nombres = {1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",
                   7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"}

    # Registrar período
    supabase.table("periodos").upsert({
        "anio": anio, "mes": mes,
        "mes_nombre": mes_nombres.get(mes,""),
        "fecha_procesado": datetime.now().isoformat()
    }).execute()

    # Guardar KPIs principales
    for kpi in resultados:
        registro = {
            "anio": anio, "mes": mes,
            "seccion": kpi.get("seccion"),
            "kpi_id": kpi.get("kpi_id"),
            "kpi_nombre": kpi.get("kpi_nombre"),
            "valor": kpi.get("valor"),
            "valor_texto": kpi.get("valor_texto"),
            "objetivo": kpi.get("objetivo"),
            "objetivo_texto": kpi.get("objetivo_texto"),
            "unidad": kpi.get("unidad"),
            "estado": kpi.get("estado"),
            "es_valido": kpi.get("es_valido", True),
            "nota": kpi.get("nota"),
        }
        supabase.table("kpis").upsert(registro).execute()

    # Guardar doctores
    for doc in doctores:
        supabase.table("kpi_doctores").upsert({"anio": anio, "mes": mes, **doc}).execute()

    # Guardar mix categorías
    for cat in mix:
        supabase.table("kpi_mix_categorias").upsert({"anio": anio, "mes": mes, **cat}).execute()

    # Guardar club sonrisa
    if club:
        supabase.table("kpi_club_sonrisa").upsert({"anio": anio, "mes": mes, **club}).execute()

    # Guardar trazabilidad
    for t in trazabilidad:
        supabase.table("kpi_trazabilidad").upsert({"anio": anio, "mes": mes, **t}).execute()

    print(f"  ✅ Datos guardados correctamente en Supabase")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Uso: python importador.py <anio> <mes> <carpeta_datos> [carpeta_historico]")
        print("Ejemplo: python importador.py 2026 6 ./datos/2026/06 ./datos/historico")
        sys.exit(1)

    anio = int(sys.argv[1])
    mes = int(sys.argv[2])
    carpeta_datos = sys.argv[3]
    carpeta_historico = sys.argv[4] if len(sys.argv) > 4 else "./datos/historico"

    print(f"\n🦷 IMPORTADOR CMI — CEO CLÍNICA DENTAL")
    print(f"   Período: {mes}/{anio}")
    print(f"   Datos: {carpeta_datos}")
    print(f"   Histórico: {carpeta_historico}")

    resultados, doctores, mix, club, trazabilidad = calcular_kpis(
        anio, mes, carpeta_datos, carpeta_historico
    )

    guardar_en_supabase(anio, mes, resultados, doctores, mix, club, trazabilidad)

    print(f"\n✅ IMPORTACIÓN COMPLETADA — {mes}/{anio}")
    print(f"   KPIs calculados: {len(resultados)}")
