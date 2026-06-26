"""
IMPORTADOR CMI — CEO CLÍNICA DENTAL SANTIAGO
Versión: 3.0 | Julio 2026
- Delimitador coma para CSV Dentalink
- Lectura XLSX con openpyxl
- Búsqueda flexible de archivos
"""

import os, csv, re, glob
from datetime import datetime
from collections import defaultdict
import sys

from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

DOCTORES_ACTIVOS = [
    "ANDREI IVANOV ALARCON LOPEZ","BIANCA MADELEINE CERCADO AGUILAR",
    "DIANA CONSUELO BARRERA BALLESTEROS","ALEXIS VICTOR HERNANDEZ FIGUEROA",
    "CARLOS OROZCO","DOMINIQUE COLLAO","ANDREA CHAUX FLOREZ",
    "CRISTINA ANDREA RAMOS ZAMORA","ALVARO ANDRES SIERRA FUENTES",
    "ALINE BELEN VENEGAS CATRILEO","JUAN CARLOS QUIROGA",
    "CAMILO ANDRES VICTORIA SEPULVEDA",
]

ESPECIALIDAD_DOCTOR = {
    "ANDREI IVANOV ALARCON LOPEZ":"Implantología","BIANCA MADELEINE CERCADO AGUILAR":"General",
    "DIANA CONSUELO BARRERA BALLESTEROS":"Ortodoncia","ALEXIS VICTOR HERNANDEZ FIGUEROA":"General",
    "CARLOS OROZCO":"Ortodoncia","DOMINIQUE COLLAO":"General","ANDREA CHAUX FLOREZ":"Ortodoncia",
    "CRISTINA ANDREA RAMOS ZAMORA":"Endodoncia","ALVARO ANDRES SIERRA FUENTES":"Implantología",
    "ALINE BELEN VENEGAS CATRILEO":"General","JUAN CARLOS QUIROGA":"Periodoncia",
    "CAMILO ANDRES VICTORIA SEPULVEDA":"Ortodoncia",
}

PCT_HISTORICO_DOCTOR = {
    "ANDREI IVANOV ALARCON LOPEZ":20.5,"BIANCA MADELEINE CERCADO AGUILAR":12.8,
    "DIANA CONSUELO BARRERA BALLESTEROS":12.4,"ALEXIS VICTOR HERNANDEZ FIGUEROA":12.3,
    "CARLOS OROZCO":11.9,"DOMINIQUE COLLAO":8.6,"ANDREA CHAUX FLOREZ":5.8,
    "CRISTINA ANDREA RAMOS ZAMORA":5.4,"ALVARO ANDRES SIERRA FUENTES":2.9,
    "ALINE BELEN VENEGAS CATRILEO":2.7,"JUAN CARLOS QUIROGA":1.7,
    "CAMILO ANDRES VICTORIA SEPULVEDA":1.6,
}

OBJETIVO_TASA_CIERRE = {"General":70.0,"Ortodoncia":70.0,"Implantología":30.0,"Periodoncia":50.0,"Endodoncia":70.0}

CONVENIOS_SANTIAGO = ["BUSES VULE","CLINICA CDS","CLUB SONRISA CEO",
    "COLEGIO LORD TOMAS COCHRANE","ESCUELA LENGUAJE EDUCCERE",
    "PRECIOS SANTIAGO","PROMARCO SPA","TARJETA TU PUENTE"]

ORDEN_MESES = {"Enero":1,"Febrero":2,"Marzo":3,"Abril":4,"Mayo":5,"Junio":6,
    "Julio":7,"Agosto":8,"Septiembre":9,"Octubre":10,"Noviembre":11,"Diciembre":12}
NOMBRES_MESES = {v:k for k,v in ORDEN_MESES.items()}

# ============================================================
# LECTURA DE ARCHIVOS
# ============================================================

def detectar_delimitador(ruta):
    with open(ruta, encoding='utf-8-sig') as f:
        primera = f.readline()
    n_coma = primera.count(',')
    n_punto = primera.count(';')
    return ',' if n_coma >= n_punto else ';'

def leer_xlsx(ruta):
    try:
        import openpyxl
        wb = openpyxl.load_workbook(ruta, data_only=True)
        ws = wb.active
        rows = []
        headers = None
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if all(v is None for v in row): continue
            if headers is None:
                headers = [str(h).strip() if h else f"col_{i}" for i,h in enumerate(row)]
                continue
            row_dict = {h: str(v).strip() if v is not None else "" for h,v in zip(headers,row)}
            rows.append(row_dict)
        return rows
    except Exception as e:
        print(f"  ⚠️  Error XLSX {ruta}: {e}")
        return []

def leer_csv(ruta):
    try:
        delim = detectar_delimitador(ruta)
        with open(ruta, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=delim)
            return list(reader)
    except Exception as e:
        print(f"  ⚠️  Error CSV {ruta}: {e}")
        return []

def leer_archivo(ruta):
    if not ruta or not os.path.exists(ruta): return []
    if ruta.lower().endswith(('.xlsx','.xls')): return leer_xlsx(ruta)
    return leer_csv(ruta)

def buscar(carpeta, *patrones):
    for pat in patrones:
        for ext in ['.csv','.xlsx','.xls']:
            matches = glob.glob(os.path.join(carpeta, f"*{pat}*{ext}"))
            if matches:
                print(f"    → {os.path.basename(matches[0])}")
                return matches[0]
    return None

def limpiar_monto(v):
    if not v: return 0.0
    try:
        s = str(v).replace("$","").replace(" ","")
        # Formato chileno: puntos como miles, coma como decimal
        if ',' in s and '.' in s:
            s = s.replace('.','').replace(',','.')
        elif ',' in s:
            # Solo coma: puede ser decimal o miles
            partes = s.split(',')
            if len(partes)==2 and len(partes[1])<=2:
                s = s.replace(',','.')
            else:
                s = s.replace(',','')
        elif s.count('.')>1:
            s = s.replace('.','')
        return float(s)
    except: return 0.0

def limpiar_pct(v):
    if not v: return None
    try: return float(str(v).replace('%','').replace(',','.').strip())
    except: return None

def norm_doctor(nombre, apellido):
    return f"{nombre} {apellido}".strip().upper()

def estado(valor, objetivo, mayor=True):
    if valor is None or objetivo is None: return "⚠️"
    return "✅" if (valor>=objetivo if mayor else valor<=objetivo) else "🔴"

# ============================================================
# CÁLCULO DE KPIs
# ============================================================

def calcular_kpis(anio, mes, carpeta_datos, carpeta_historico):
    mes_nombre = NOMBRES_MESES.get(mes,"")
    resultados, doctores_res, mix_res, traz_res = [], [], [], []
    club_res = {}

    print(f"\n{'='*60}")
    print(f"  CMI — {mes_nombre} {anio}")
    print(f"{'='*60}\n  [Localizando archivos...]")

    f_acc = buscar(carpeta_datos, "acciones_realizadas","acciones realizadas","Acciones_Realizadas")
    f_cit = buscar(carpeta_datos, "agenda_citas","Agenda_Citas","agenda citas")
    f_seg = buscar(carpeta_datos, "Seguimiento_Presupuestos","seguimiento","Sistema_Seguimiento")
    f_pn  = buscar(carpeta_datos, "pacientes_nuevos","Pacientes_Nuevos","pacientes nuevos")
    f_tg  = buscar(carpeta_datos, "tratamientos_generados","Tratamientos_Generados","tratamientos generados")
    f_pc  = buscar(carpeta_datos, "Presupuestos_Capturados","presupuestos_capturados")
    f_chi = buscar(carpeta_datos, "Resultado_Operacional","resultado_operacional","Chipax","chipax","Operacional")
    f_pt  = buscar(carpeta_datos, "pacientes_todos","Pacientes_Todos","pacientes todos")
    f_m1  = buscar(carpeta_datos, "meta","Meta","Campanas","Campañas","Reporte")
    f_goo = buscar(carpeta_datos, "google","Google","Informe")
    f_his = buscar(carpeta_historico, "historico","acciones_realizadas","tratamientos_acciones")

    acciones   = leer_archivo(f_acc)
    citas      = leer_archivo(f_cit)
    seguimiento= leer_archivo(f_seg)
    pac_nuevos = leer_archivo(f_pn)
    trat_gen   = leer_archivo(f_tg)
    pres_cap   = leer_archivo(f_pc)
    chipax     = leer_archivo(f_chi)
    pac_todos  = leer_archivo(f_pt)
    historico  = leer_archivo(f_his)
    meta_rows  = leer_archivo(f_m1)
    google_rows= leer_archivo(f_goo)

    print(f"\n  Acciones: {len(acciones)} | Citas: {len(citas)} | Pac.Nuevos: {len(pac_nuevos)} | Histórico: {len(historico)} | Chipax: {len(chipax)}")

    # ---- PRECÁLCULOS ----
    atenciones_u = set()
    pacientes_u  = set()
    fact_total   = 0.0
    fact_conv    = defaultdict(float)
    at_conv      = defaultdict(set)
    fact_orto_club = 0.0
    at_orto_club   = set()
    fact_doctor  = defaultdict(float)
    fact_cat     = defaultdict(float)
    pid_monto    = defaultdict(float)

    for r in acciones:
        pid   = r.get("# Paciente","").strip()
        fecha = r.get("Fecha de realización","").strip()
        conv  = r.get("Convenio Paciente","").strip().upper()
        cat   = r.get("Nombre Categoria","").strip().upper()
        prest = r.get("Nombre Prestación","").strip()
        nom_d = r.get("Nombre Profesional Realizador","").strip()
        ape_d = r.get("Apellidos Profesional Realizador","").strip()
        monto = limpiar_monto(r.get("Pagado Paciente Prestación (Abonado)","0"))

        if pid and fecha: atenciones_u.add((pid,fecha)); pacientes_u.add(pid)
        fact_total += monto
        fact_conv[conv] += monto
        if pid and fecha: at_conv[conv].add((pid,fecha))
        pid_monto[pid] += monto

        if conv == "CLUB SONRISA CEO":
            es_orto = cat in ["ORTODONCIA","ACCIONES DE ORTODONCIA"]
            if cat == "ESPECIALIDAD":
                p = prest.lower()
                es_orto = any(x in p for x in ["instalac","control","contencion","ortodoncia","pack ortodoncia"])
            if es_orto: fact_orto_club += monto; at_orto_club.add((pid,fecha)) if pid and fecha else None

        if nom_d: fact_doctor[norm_doctor(nom_d,ape_d)] += monto
        fact_cat[cat] += monto

    n_at = len(atenciones_u); n_pac = len(pacientes_u)

    # ---- COMERCIAL ----
    print("\n  [COMERCIAL]")

    # KPI 1 — Tasa Cierre desde presupuestos capturados
    kpi1 = None
    mes_col = f"{mes_nombre.lower()[:3]}/{anio}" if mes_nombre else ""
    for r in pres_cap:
        for k,v in r.items():
            if k and mes_nombre[:3].lower() in str(k).lower() and str(anio) in str(k):
                kpi1 = limpiar_pct(v)
                if kpi1: break
        if kpi1: break
    # Fallback desde tratamientos generados
    if kpi1 is None and trat_gen:
        gen=cap=0
        for r in trat_gen:
            if limpiar_monto(r.get("Total Presupuesto","0")) > 0:
                gen+=1
                if r.get("Tratamiento Capturado","").strip()=="Capturado": cap+=1
        kpi1 = (cap/gen*100) if gen>0 else None

    e1 = estado(kpi1, 70.0)
    print(f"    KPI 1 Tasa Cierre: {kpi1:.1f}% {e1}" if kpi1 else "    KPI 1: N/D")
    resultados.append({"kpi_id":"1","seccion":"COMERCIAL","kpi_nombre":"Tasa Cierre Presupuestos",
        "valor":round(kpi1,2) if kpi1 else None,"objetivo":70.0,"unidad":"%","estado":e1})

    # KPI 2 — Presupuestos generados
    kpi2 = sum(1 for r in trat_gen if limpiar_monto(r.get("Total Presupuesto","0"))>0)
    e2 = estado(kpi2, 230)
    print(f"    KPI 2 Presupuestos: {kpi2} {e2}")
    resultados.append({"kpi_id":"2","seccion":"COMERCIAL","kpi_nombre":"Presupuestos Generados",
        "valor":kpi2,"objetivo":230.0,"unidad":"unidades","estado":e2})

    # KPI 3 — Captación seguimiento
    kpi3 = None
    for r in seguimiento:
        a = str(r.get("Año","")).strip(); m = str(r.get("Mes","")).strip()
        if str(anio) in a and mes_nombre.lower() in m.lower():
            kpi3 = limpiar_pct(r.get("% de Recuperación",""))
    e3 = estado(kpi3, 20.0)
    print(f"    KPI 3 Seguimiento: {kpi3:.1f}%" if kpi3 else "    KPI 3: N/D")
    resultados.append({"kpi_id":"3","seccion":"COMERCIAL","kpi_nombre":"Captación por Seguimiento",
        "valor":round(kpi3,2) if kpi3 else None,"objetivo":20.0,"unidad":"%","estado":e3})

    # KPI T — Trazabilidad
    total_pn = len(pac_nuevos); con_orig=0
    canales = defaultdict(int); can_ing = defaultdict(float)
    p_meta=set(); p_google=set(); p_ref=set()

    for r in pac_nuevos:
        ref = r.get("Referencia Paciente","").strip().upper()
        pid = r.get("# Paciente","").strip()
        if ref=="REDES SOCIALES": con_orig+=1; canales["Meta Ads"]+=1; p_meta.add(pid)
        elif ref=="GOOGLE": con_orig+=1; canales["Google Ads"]+=1; p_google.add(pid)
        elif ref.startswith("REFERIDO"): con_orig+=1; canales["Recomienda CEO"]+=1; p_ref.add(pid)
        elif ref in ["ORGÁNICO","ORGANICO"]: con_orig+=1; canales["Orgánico"]+=1
        elif ref: con_orig+=1

    kpiT = (con_orig/total_pn*100) if total_pn>0 else 0
    eT = estado(kpiT, 90.0); es_valido = kpiT>=90.0
    print(f"    KPI T Trazabilidad: {kpiT:.1f}% {eT}")
    resultados.append({"kpi_id":"T","seccion":"COMERCIAL","kpi_nombre":"Trazabilidad de Origen",
        "valor":round(kpiT,2),"objetivo":90.0,"unidad":"%","estado":eT,"nota":"Prerequisito para CPA y ROAS"})

    for pid in p_meta: can_ing["Meta Ads"] += pid_monto.get(pid,0)
    for pid in p_google: can_ing["Google Ads"] += pid_monto.get(pid,0)
    for pid in p_ref: can_ing["Recomienda CEO"] += pid_monto.get(pid,0)

    # Inversión Meta
    inv_meta = 0.0
    for r in meta_rows:
        for k,v in r.items():
            if not k: continue
            k_n = str(k).lower().replace("á","a").replace("é","e").replace("ó","o").replace("ú","u")
            if "importe" in k_n and "gastado" in k_n:
                inv_meta += limpiar_monto(v)

    # Inversión Google
    # Inversión Google — lectura directa del archivo por líneas
    inv_google = 0.0
    if f_goo and os.path.exists(f_goo):
        try:
            with open(f_goo, encoding='utf-8-sig') as fg:
                glines = fg.readlines()
            # Encontrar headers
            header_g = None
            for gl in glines:
                if "Costo" in gl and "Estado" in gl:
                    header_g = gl.strip().split(',')
                    break
            # Buscar fila Total: Campañas
            for gl in glines:
                if gl.startswith('Total: Campañas'):
                    parts = gl.strip().split(',')
                    if header_g and 'Costo' in header_g:
                        idx = header_g.index('Costo')
                        inv_google = limpiar_monto(parts[idx]) if idx < len(parts) else 0
                    else:
                        inv_google = limpiar_monto(parts[8]) if len(parts) > 8 else 0
                    break
        except Exception as eg:
            print(f"  ⚠️  Google Ads: {eg}")

    n_meta=len(p_meta); n_google=len(p_google)
    nota_cpa = "" if es_valido else "⚠️ Trazabilidad <90%"

    cpa_meta = inv_meta/n_meta if n_meta>0 and inv_meta>0 else None
    e4 = "⏳" if not es_valido else "ℹ️"
    resultados.append({"kpi_id":"4","seccion":"COMERCIAL","kpi_nombre":"CPA Meta Ads",
        "valor":round(cpa_meta,2) if cpa_meta else None,
        "valor_texto":f"${cpa_meta:,.0f}" if cpa_meta else "N/D",
        "objetivo":None,"objetivo_texto":"Por definir","unidad":"CLP","estado":e4,"es_valido":es_valido,"nota":nota_cpa})

    cpa_google = inv_google/n_google if n_google>0 and inv_google>0 else None
    resultados.append({"kpi_id":"5","seccion":"COMERCIAL","kpi_nombre":"CPA Google Ads",
        "valor":round(cpa_google,2) if cpa_google else None,
        "valor_texto":f"${cpa_google:,.0f}" if cpa_google else "N/D",
        "objetivo":None,"objetivo_texto":"Por definir","unidad":"CLP","estado":e4,"es_valido":es_valido,"nota":nota_cpa})

    ing_meta=can_ing["Meta Ads"]; roas_meta=ing_meta/inv_meta if inv_meta>0 else None
    e6 = estado(roas_meta,3.5) if roas_meta and es_valido else "⚠️"
    resultados.append({"kpi_id":"6","seccion":"COMERCIAL","kpi_nombre":"ROAS Meta Ads",
        "valor":round(roas_meta,2) if roas_meta else None,"objetivo":3.5,"unidad":"x",
        "estado":e6,"es_valido":es_valido,"nota":"ROAS = piso mensual. ROAS real considera LTV."})

    ing_google=can_ing["Google Ads"]; roas_google=ing_google/inv_google if inv_google>0 else None
    e7 = estado(roas_google,3.5) if roas_google and es_valido else "⚠️"
    resultados.append({"kpi_id":"7","seccion":"COMERCIAL","kpi_nombre":"ROAS Google Ads",
        "valor":round(roas_google,2) if roas_google else None,"objetivo":3.5,"unidad":"x",
        "estado":e7,"es_valido":es_valido,"nota":"ROAS = piso mensual. ROAS real considera LTV."})

    for canal,n in canales.items():
        inv = inv_meta if canal=="Meta Ads" else (inv_google if canal=="Google Ads" else 0)
        ing = can_ing.get(canal,0)
        traz_res.append({"canal":canal,"pacientes":n,"ingresos":round(ing,2),
            "inversion":round(inv,2),"cpa":round(inv/n,2) if n>0 and inv>0 else None,
            "roas":round(ing/inv,2) if inv>0 else None})

    # ---- OPERACIÓN ----
    print("\n  [OPERACIÓN]")
    kpi8 = fact_total/n_at if n_at>0 else 0
    e8=estado(kpi8,45000)
    print(f"    KPI 8 Ing/At: ${kpi8:,.0f} {e8}")
    resultados.append({"kpi_id":"8","seccion":"OPERACIÓN","kpi_nombre":"Ingresos por Atención","valor":round(kpi8,2),"objetivo":45000.0,"unidad":"CLP","estado":e8})

    tot_cit=len(citas); cambio=sum(1 for r in citas if r.get("Estado Cita","").strip()=="Cambio de fecha")
    atend=sum(1 for r in citas if r.get("Estado Cita","").strip()=="Atendido")
    val_cit=tot_cit-cambio; kpi9=(atend/val_cit*100) if val_cit>0 else 0
    e9=estado(kpi9,80.0)
    print(f"    KPI 9 Asistencia: {kpi9:.1f}% {e9}")
    resultados.append({"kpi_id":"9","seccion":"OPERACIÓN","kpi_nombre":"Asistencia a Citas","valor":round(kpi9,2),"objetivo":80.0,"unidad":"%","estado":e9})

    e10a=estado(n_at,487); e10b=estado(n_pac,415)
    print(f"    KPI 10a Atenciones: {n_at} {e10a} | 10b Pacientes: {n_pac} {e10b}")
    resultados.append({"kpi_id":"10a","seccion":"OPERACIÓN","kpi_nombre":"Atenciones Totales vs Meta","valor":n_at,"objetivo":487.0,"unidad":"atenciones","estado":e10a})
    resultados.append({"kpi_id":"10b","seccion":"OPERACIÓN","kpi_nombre":"Pacientes Únicos Atendidos","valor":n_pac,"objetivo":415.0,"unidad":"pacientes","estado":e10b})

    kpi11=fact_total/3; e11=estado(kpi11,10986906)
    print(f"    KPI 11 Prod/Sillón: ${kpi11:,.0f} {e11}")
    resultados.append({"kpi_id":"11","seccion":"OPERACIÓN","kpi_nombre":"Producción por Sillón","valor":round(kpi11,2),"objetivo":10986906.0,"unidad":"CLP","estado":e11})

    # ---- MIX SERVICIOS ----
    print("\n  [MIX SERVICIOS]")
    for cat,monto in sorted(fact_cat.items(),key=lambda x:-x[1]):
        if not cat: continue
        pct=(monto/fact_total*100) if fact_total>0 else 0
        mix_res.append({"categoria":cat,"ingresos":round(monto,2),"pct_real":round(pct,2),"pct_historico":0.0,"objetivo_ingresos":None})

    print(f"    KPI 12 Mix: {len(mix_res)} categorías, ${fact_total:,.0f}")
    resultados.append({"kpi_id":"12","seccion":"MIX DE SERVICIOS","kpi_nombre":"Mix de Ingresos por Categoría","valor":round(fact_total,2),"objetivo":None,"unidad":"CLP","estado":"ℹ️"})

    # KPI 13 — Ortodoncia nuevos
    pacs_orto=set()
    for r in acciones:
        pid=r.get("# Paciente","").strip(); cat=r.get("Nombre Categoria","").strip().upper()
        prest=r.get("Nombre Prestación","").strip().lower()
        if pid and ("pack ortodoncia" in prest or (cat in ["ORTODONCIA","ACCIONES DE ORTODONCIA","ESPECIALIDAD"] and (prest.startswith("instalación") or prest.startswith("instalacion")))):
            pacs_orto.add(pid)
    e13=estado(len(pacs_orto),12)
    print(f"    KPI 13 Ortodoncia: {len(pacs_orto)} {e13}")
    resultados.append({"kpi_id":"13","seccion":"MIX DE SERVICIOS","kpi_nombre":"Volumen Casos Nuevos Ortodoncia","valor":len(pacs_orto),"objetivo":12.0,"unidad":"casos","estado":e13})

    # KPI 14 — Implantes nuevos
    patron=re.compile(r"^\d+:[a-záéíóúA-Z,]+",re.IGNORECASE)
    primera_ap={}
    hist_ord=sorted(historico,key=lambda x:(int(x.get("Año de realización","2025") or 2025),ORDEN_MESES.get(x.get("Mes de realización","").strip(),0)))
    for r in hist_ord:
        cat=r.get("Nombre Categoria","").strip().upper()
        if cat not in ["IMPLANTOLOGIA","IMPLANTOLOGÍA"]: continue
        pid=r.get("# Paciente","").strip(); pieza=r.get("Pieza Tratada","").strip()
        a=r.get("Año de realización","").strip(); m=r.get("Mes de realización","").strip()
        if not pieza or not patron.match(pieza): continue
        key=(pid,pieza)
        if key not in primera_ap: primera_ap[key]=(a,m)
    casos_impl=[k for k,(a,m) in primera_ap.items() if str(anio) in str(a) and mes_nombre.lower() in m.lower()]
    e14=estado(len(casos_impl),11)
    print(f"    KPI 14 Implantes: {len(casos_impl)} {e14}")
    resultados.append({"kpi_id":"14","seccion":"MIX DE SERVICIOS","kpi_nombre":"Volumen Casos Nuevos Implantes","valor":len(casos_impl),"objetivo":11.0,"unidad":"casos","estado":e14})

    # ---- DOCTORES ----
    print("\n  [DOCTORES]")
    doc_data=defaultdict(lambda:{"gen":0,"cap":0})
    for r in trat_gen:
        if limpiar_monto(r.get("Total Presupuesto","0"))==0: continue
        dk=norm_doctor(r.get("Nombre Profesional Tratamiento","").strip(),r.get("Apellidos Profesional Tratamiento","").strip())
        doc_data[dk]["gen"]+=1
        if r.get("Tratamiento Capturado","").strip()=="Capturado": doc_data[dk]["cap"]+=1

    for doc in DOCTORES_ACTIVOS:
        d=doc_data.get(doc,{"gen":0,"cap":0})
        gen=d["gen"]; cap=d["cap"]
        tasa=(cap/gen*100) if gen>0 else None
        esp=ESPECIALIDAD_DOCTOR.get(doc,"General")
        doctores_res.append({
            "doctor":doc,"especialidad":esp,
            "presupuestos_generados":gen,"presupuestos_capturados":cap,
            "tasa_cierre":round(tasa,2) if tasa is not None else None,
            "objetivo_tasa_cierre":OBJETIVO_TASA_CIERRE.get(esp,70.0),
            "ingresos":round(fact_doctor.get(doc,0),2),
            "objetivo_ingresos":None,"pct_historico":PCT_HISTORICO_DOCTOR.get(doc,0),
        })
    print(f"    KPI 15+16 Doctores: {len(doctores_res)}")
    resultados.append({"kpi_id":"15+16","seccion":"DOCTORES","kpi_nombre":"Presupuestos y Tasa Cierre por Doctor","valor":None,"objetivo":None,"unidad":"%","estado":"ℹ️","nota":"Ver tabla por doctor"})
    resultados.append({"kpi_id":"17","seccion":"DOCTORES","kpi_nombre":"Productividad por Doctor","valor":None,"objetivo":None,"unidad":"CLP","estado":"ℹ️","nota":"Ver tabla por doctor"})

    # ---- FINANCIERO ----
    print("\n  [FINANCIERO]")
    ing_tot=0.0; otros_ing=0.0; costos_fij=0.0; gastos_var=0.0
    for r in chipax:
        vals=list(r.values())
        if not vals: continue
        concepto=str(vals[0]).strip()
        try: val=limpiar_monto(vals[1]) if len(vals)>1 else 0
        except: val=0
        if "Total Ingresos" in concepto and "Otros" not in concepto: ing_tot=val
        elif "Total Otros Ingresos" in concepto: otros_ing=val
        elif "Total Costos" in concepto: costos_fij=abs(val)
        elif "Total Gastos" in concepto: gastos_var=abs(val)

    ing_chipax=ing_tot+otros_ing; res_op=ing_chipax-costos_fij-gastos_var
    margen=(res_op/ing_chipax*100) if ing_chipax>0 else None
    print(f"    Ingresos Chipax: ${ing_chipax:,.0f} | Margen: {margen:.1f}%" if margen else f"    Ingresos Chipax: ${ing_chipax:,.0f}")
    resultados.append({"kpi_id":"18","seccion":"FINANCIERO","kpi_nombre":"Facturación Real vs Presupuesto","valor":round(ing_chipax,2),"objetivo":None,"objetivo_texto":"Presupuesto mensual","unidad":"CLP","estado":"ℹ️"})
    resultados.append({"kpi_id":"19","seccion":"FINANCIERO","kpi_nombre":"Margen Operacional","valor":round(margen,2) if margen else None,"objetivo":None,"objetivo_texto":"Variable según presupuesto","unidad":"%","estado":"ℹ️"})
    resultados.append({"kpi_id":"20","seccion":"FINANCIERO","kpi_nombre":"Comparativa vs Mes Anterior","valor":None,"objetivo":None,"valor_texto":"Calculado vs mes anterior","unidad":"%","estado":"ℹ️","nota":"Verde ≥-5% | Amarillo -5% a -15% | Rojo <-15%"})

    # ---- PROGRAMAS COMERCIALES ----
    print("\n  [PROGRAMAS COMERCIALES]")
    ing_club=fact_conv.get("CLUB SONRISA CEO",0); ing_club_otros=ing_club-fact_orto_club
    at_club=len(at_conv.get("CLUB SONRISA CEO",set())); pct_otros=(ing_club_otros/ing_club*100) if ing_club>0 else 0
    e21a=estado(ing_club,17849110)
    print(f"    KPI 21a Club: ${ing_club:,.0f} {e21a}")
    resultados.append({"kpi_id":"21a","seccion":"PROGRAMAS COMERCIALES","kpi_nombre":"Ingresos Club Sonrisa CEO",
        "valor":round(ing_club,2),"objetivo":17849110.0,"unidad":"CLP","estado":e21a,
        "nota":f"Ortodoncia: ${fact_orto_club:,.0f} | Otros: ${ing_club_otros:,.0f} | %Otros: {pct_otros:.1f}%"})

    socios=set(); pids_activos_stgo=set()
    for r in pac_todos:
        conv=r.get("Convenio","").strip().upper(); pid=r.get("# Paciente","").strip()
        if conv in [c.upper() for c in CONVENIOS_SANTIAGO]: pids_activos_stgo.add(pid)
        if conv=="CLUB SONRISA CEO": socios.add(pid)

    pids_hist=set(r.get("# Paciente","").strip() for r in historico)
    pacs_act=pids_activos_stgo & pids_hist
    kpi21b=(len(socios)/len(pacs_act)*100) if pacs_act else 0
    e21b=estado(kpi21b,70.0)
    print(f"    KPI 21b Afiliación: {kpi21b:.1f}% {e21b}")
    resultados.append({"kpi_id":"21b","seccion":"PROGRAMAS COMERCIALES","kpi_nombre":"Tasa de Afiliación Club Sonrisa CEO",
        "valor":round(kpi21b,2),"objetivo":70.0,"unidad":"%","estado":e21b,
        "nota":f"{len(socios)} socios / {len(pacs_act)} pacientes activos"})

    meses_ven=set(); m_t,a_t=mes,anio
    for _ in range(6):
        meses_ven.add(f"{a_t}-{NOMBRES_MESES.get(m_t,'')}"); m_t-=1
        if m_t==0: m_t=12; a_t-=1

    tratos_socio=defaultdict(set)
    for r in historico:
        pid=r.get("# Paciente","").strip(); trat=r.get("# Tratamiento","").strip()
        a=r.get("Año de realización","").strip(); m=r.get("Mes de realización","").strip()
        if pid in socios and f"{a}-{m}" in meses_ven and trat: tratos_socio[pid].add(trat)

    retorno=sum(1 for p in socios if len(tratos_socio.get(p,set()))>=2)
    en_proc=sum(1 for p in socios if len(tratos_socio.get(p,set()))==1)
    sin_act=len(socios)-retorno-en_proc
    kpi21c=(retorno/len(socios)*100) if socios else 0
    e21c=estado(kpi21c,60.0)
    print(f"    KPI 21c Retorno: {kpi21c:.1f}% {e21c}")
    resultados.append({"kpi_id":"21c","seccion":"PROGRAMAS COMERCIALES","kpi_nombre":"Tasa de Retorno Club Sonrisa CEO",
        "valor":round(kpi21c,2),"objetivo":60.0,"unidad":"%","estado":e21c,
        "nota":f"Retorno: {retorno} | En proceso: {en_proc} | Sin actividad: {sin_act}"})

    club_res={"total_socios":len(socios),"socios_retorno":retorno,"socios_en_proceso":en_proc,
        "socios_sin_actividad":sin_act,"ingresos_ortodoncia":round(fact_orto_club,2),
        "ingresos_otros":round(ing_club_otros,2),"ingresos_total":round(ing_club,2),
        "atenciones_ortodoncia":len(at_orto_club),"atenciones_otros":at_club-len(at_orto_club)}

    e22=estado(len(p_ref),3)
    print(f"    KPI 22 Referidos: {len(p_ref)} {e22}")
    resultados.append({"kpi_id":"22","seccion":"PROGRAMAS COMERCIALES","kpi_nombre":"Pacientes Nuevos Referidos (Recomienda CEO)","valor":len(p_ref),"objetivo":3.0,"unidad":"pacientes","estado":e22})

    ing_ref=can_ing.get("Recomienda CEO",0); e23=estado(ing_ref,600000)
    print(f"    KPI 23 Ingresos Ref: ${ing_ref:,.0f} {e23}")
    resultados.append({"kpi_id":"23","seccion":"PROGRAMAS COMERCIALES","kpi_nombre":"Ingresos Atribuidos Recomienda CEO","valor":round(ing_ref,2),"objetivo":600000.0,"unidad":"CLP","estado":e23})

    return resultados, doctores_res, mix_res, club_res, traz_res


# ============================================================
# GUARDAR EN SUPABASE
# ============================================================

def guardar_en_supabase(anio, mes, resultados, doctores, mix, club, trazabilidad):
    print(f"\n  [SUPABASE] Guardando {len(resultados)} KPIs...")
    sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    try:
        sb.table("periodos").upsert({"anio":anio,"mes":mes,"mes_nombre":NOMBRES_MESES.get(mes,""),
            "fecha_procesado":datetime.now().isoformat()},on_conflict="anio,mes").execute()
    except Exception as e:
        print(f"  ⚠️  Período: {e}")

    for kpi in resultados:
        try:
            sb.table("kpis").upsert({
                "anio":anio,"mes":mes,"seccion":kpi.get("seccion"),
                "kpi_id":kpi.get("kpi_id"),"kpi_nombre":kpi.get("kpi_nombre"),
                "valor":kpi.get("valor"),"valor_texto":kpi.get("valor_texto"),
                "objetivo":kpi.get("objetivo"),"objetivo_texto":kpi.get("objetivo_texto"),
                "unidad":kpi.get("unidad"),"estado":kpi.get("estado"),
                "es_valido":kpi.get("es_valido",True),"nota":kpi.get("nota"),
            },on_conflict="anio,mes,kpi_id").execute()
        except Exception as e:
            print(f"  ⚠️  KPI {kpi.get('kpi_id')}: {e}")

    for doc in doctores:
        try: sb.table("kpi_doctores").upsert({"anio":anio,"mes":mes,**doc},on_conflict="anio,mes,doctor").execute()
        except Exception as e: print(f"  ⚠️  Doctor {doc.get('doctor')}: {e}")

    for cat in mix:
        try: sb.table("kpi_mix_categorias").upsert({"anio":anio,"mes":mes,**cat},on_conflict="anio,mes,categoria").execute()
        except Exception as e: print(f"  ⚠️  Cat {cat.get('categoria')}: {e}")

    if club:
        try: sb.table("kpi_club_sonrisa").upsert({"anio":anio,"mes":mes,**club},on_conflict="anio,mes").execute()
        except Exception as e: print(f"  ⚠️  Club: {e}")

    for t in trazabilidad:
        try: sb.table("kpi_trazabilidad").upsert({"anio":anio,"mes":mes,**t},on_conflict="anio,mes,canal").execute()
        except Exception as e: print(f"  ⚠️  Traz {t.get('canal')}: {e}")

    print("  ✅ Guardado correctamente")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    if len(sys.argv)<4:
        print("Uso: python importador.py <anio> <mes> <carpeta_datos> [carpeta_historico]")
        sys.exit(1)

    anio=int(sys.argv[1]); mes=int(sys.argv[2])
    carpeta_datos=sys.argv[3]
    carpeta_historico=sys.argv[4] if len(sys.argv)>4 else "./datos/historico"

    print(f"\n🦷 IMPORTADOR CMI v3.0 — CEO CLÍNICA DENTAL")
    print(f"   Período: {NOMBRES_MESES.get(mes,'')} {anio}")

    res,docs,mix,club,traz = calcular_kpis(anio,mes,carpeta_datos,carpeta_historico)
    guardar_en_supabase(anio,mes,res,docs,mix,club,traz)

    print(f"\n✅ COMPLETADO — {NOMBRES_MESES.get(mes,'')} {anio} | KPIs: {len(res)}")
