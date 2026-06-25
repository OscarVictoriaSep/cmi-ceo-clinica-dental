-- ============================================================
-- ESQUEMA BASE DE DATOS — CMI CEO CLÍNICA DENTAL
-- Ejecutar en Supabase SQL Editor
-- ============================================================

-- Tabla de períodos procesados
CREATE TABLE IF NOT EXISTS periodos (
    id SERIAL PRIMARY KEY,
    anio INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    mes_nombre VARCHAR(20) NOT NULL,
    fecha_procesado TIMESTAMP DEFAULT NOW(),
    archivos_procesados JSONB,
    UNIQUE(anio, mes)
);

-- Tabla de KPIs (resultados por período)
CREATE TABLE IF NOT EXISTS kpis (
    id SERIAL PRIMARY KEY,
    anio INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    seccion VARCHAR(50) NOT NULL,
    kpi_id VARCHAR(20) NOT NULL,
    kpi_nombre VARCHAR(100) NOT NULL,
    valor NUMERIC(15,2),
    valor_texto VARCHAR(200),
    objetivo NUMERIC(15,2),
    objetivo_texto VARCHAR(200),
    unidad VARCHAR(20),
    estado VARCHAR(10),
    es_valido BOOLEAN DEFAULT TRUE,
    nota VARCHAR(500),
    fecha_calculo TIMESTAMP DEFAULT NOW(),
    UNIQUE(anio, mes, kpi_id)
);

-- Tabla de productividad por doctor
CREATE TABLE IF NOT EXISTS kpi_doctores (
    id SERIAL PRIMARY KEY,
    anio INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    doctor VARCHAR(100) NOT NULL,
    especialidad VARCHAR(50),
    presupuestos_generados INTEGER,
    presupuestos_capturados INTEGER,
    tasa_cierre NUMERIC(5,2),
    objetivo_tasa_cierre NUMERIC(5,2),
    ingresos NUMERIC(15,2),
    objetivo_ingresos NUMERIC(15,2),
    pct_historico NUMERIC(5,2),
    UNIQUE(anio, mes, doctor)
);

-- Tabla de mix de servicios por categoría
CREATE TABLE IF NOT EXISTS kpi_mix_categorias (
    id SERIAL PRIMARY KEY,
    anio INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    categoria VARCHAR(100) NOT NULL,
    ingresos NUMERIC(15,2),
    pct_real NUMERIC(5,2),
    pct_historico NUMERIC(5,2),
    objetivo_ingresos NUMERIC(15,2),
    UNIQUE(anio, mes, categoria)
);

-- Tabla de Club Sonrisa CEO segmentación retorno
CREATE TABLE IF NOT EXISTS kpi_club_sonrisa (
    id SERIAL PRIMARY KEY,
    anio INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    total_socios INTEGER,
    socios_retorno INTEGER,
    socios_en_proceso INTEGER,
    socios_sin_actividad INTEGER,
    ingresos_ortodoncia NUMERIC(15,2),
    ingresos_otros NUMERIC(15,2),
    ingresos_total NUMERIC(15,2),
    atenciones_ortodoncia INTEGER,
    atenciones_otros INTEGER,
    UNIQUE(anio, mes)
);

-- Tabla de trazabilidad por canal
CREATE TABLE IF NOT EXISTS kpi_trazabilidad (
    id SERIAL PRIMARY KEY,
    anio INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    canal VARCHAR(50) NOT NULL,
    pacientes INTEGER,
    ingresos NUMERIC(15,2),
    inversion NUMERIC(15,2),
    cpa NUMERIC(15,2),
    roas NUMERIC(8,2),
    UNIQUE(anio, mes, canal)
);

-- Tabla de presupuesto anual (referencia fija)
CREATE TABLE IF NOT EXISTS presupuesto_anual (
    id SERIAL PRIMARY KEY,
    anio INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    ventas NUMERIC(15,2),
    resultado_operacional NUMERIC(15,2),
    margen_pct NUMERIC(5,2),
    UNIQUE(anio, mes)
);

-- Insertar presupuesto 2026
INSERT INTO presupuesto_anual (anio, mes, ventas, resultado_operacional, margen_pct) VALUES
(2026, 1,  30300271, 2635954,  8.70),
(2026, 2,  27954701, 1612017,  5.77),
(2026, 3,  28241040, 1262175,  4.47),
(2026, 4,  33738515, 4001485, 11.86),
(2026, 5,  26507441, 1344541,  5.07),
(2026, 6,  33417380, 3914828, 11.72),
(2026, 7,  39506180, 6237152, 15.79),
(2026, 8,  33244942, 3936545, 11.84),
(2026, 9,  27648623, 1601157,  5.79),
(2026, 10, 30391509, 2750170,  9.05),
(2026, 11, 27259932, 1516712,  5.56),
(2026, 12, 30723718, 2973928,  9.68)
ON CONFLICT (anio, mes) DO NOTHING;

-- Tabla histórico de productividad por doctor (para calcular % base)
CREATE TABLE IF NOT EXISTS historico_doctores (
    id SERIAL PRIMARY KEY,
    anio INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    doctor VARCHAR(100) NOT NULL,
    ingresos NUMERIC(15,2),
    atenciones INTEGER,
    UNIQUE(anio, mes, doctor)
);

-- Habilitar Row Level Security (RLS) básico
ALTER TABLE kpis ENABLE ROW LEVEL SECURITY;
ALTER TABLE kpi_doctores ENABLE ROW LEVEL SECURITY;
ALTER TABLE kpi_mix_categorias ENABLE ROW LEVEL SECURITY;
ALTER TABLE kpi_club_sonrisa ENABLE ROW LEVEL SECURITY;
ALTER TABLE kpi_trazabilidad ENABLE ROW LEVEL SECURITY;
ALTER TABLE presupuesto_anual ENABLE ROW LEVEL SECURITY;
ALTER TABLE periodos ENABLE ROW LEVEL SECURITY;
ALTER TABLE historico_doctores ENABLE ROW LEVEL SECURITY;

-- Políticas de acceso (lectura pública para dashboard, escritura solo con service_role)
CREATE POLICY "Lectura pública" ON kpis FOR SELECT USING (true);
CREATE POLICY "Lectura pública" ON kpi_doctores FOR SELECT USING (true);
CREATE POLICY "Lectura pública" ON kpi_mix_categorias FOR SELECT USING (true);
CREATE POLICY "Lectura pública" ON kpi_club_sonrisa FOR SELECT USING (true);
CREATE POLICY "Lectura pública" ON kpi_trazabilidad FOR SELECT USING (true);
CREATE POLICY "Lectura pública" ON presupuesto_anual FOR SELECT USING (true);
CREATE POLICY "Lectura pública" ON periodos FOR SELECT USING (true);
CREATE POLICY "Lectura pública" ON historico_doctores FOR SELECT USING (true);

