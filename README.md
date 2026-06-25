# CMI CEO Clínica Dental Santiago

## Estructura del repositorio

```
/
├── src/
│   ├── importador.py      ← Calcula los 26 KPIs y guarda en Supabase
│   └── dashboard.py       ← Dashboard Streamlit
├── datos/
│   ├── input/
│   │   └── 2026/
│   │       └── 7/         ← Depositar CSVs aquí cada mes
│   ├── historico/
│   │   └── historico_acciones_realizadas.csv
│   └── referencia/
│       └── presupuesto_2026.csv
├── .github/workflows/
│   └── importar_mes.yml   ← Automatización GitHub Actions
├── .streamlit/
│   └── secrets.toml       ← Credenciales Supabase (NO subir a GitHub)
└── requirements.txt
```

## Cómo usar cada mes

### 1. Subir archivos CSV
Sube los archivos del mes a `datos/input/2026/MM/` con esta nomenclatura:
- `1.1_Tratamientos_Generados_Estados_M.AA.csv`
- `1.2_Sistema_Seguimiento_Presupuestos_M.AA.csv`
- `1.3_Pacientes_Nuevos_M.AA.csv`
- `1.4_Acciones_Realizadas_M.AA.csv`
- `2.1_Agenda_Citas_M.AA.csv`
- `2.2_Presupuestos_Capturados_M.AA.csv`
- `5.1_Resultado_Operacional_M.AA.csv`
- `6.1_Pacientes_Todos_M.AA.csv`
- `Meta_Ads_1_M.AA.csv`
- `Meta_Ads_2_M.AA.csv`
- `Google_Ads_M.AA.csv`

### 2. Ejecutar importador
Ir a GitHub → Actions → "Importar mes CMI" → Run workflow → ingresar año y mes.

### 3. Ver dashboard
Abrir la URL de Streamlit Cloud desde cualquier dispositivo.

## Dashboard
URL: [configurar después de deploy en Streamlit Cloud]
