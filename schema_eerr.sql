-- ============================================================
-- ESTADO DE RESULTADOS (export de Chipax) — pestaña "Resultados"
-- Ejecutar una vez en Supabase → SQL Editor
-- ============================================================
create table if not exists public.cmi_eerr (
  id bigint generated always as identity primary key,
  periodo text not null,             -- 'AAAA-MM'
  cuenta text not null,              -- nombre de la cuenta en Chipax ('__RESULTADO_CHIPAX__' = control)
  grupo text,                        -- grupo en que Chipax muestra la cuenta
  valor numeric not null default 0,  -- costos negativos, como en Chipax
  creado timestamptz default now()
);
create index if not exists cmi_eerr_periodo_idx on public.cmi_eerr (periodo);

alter table public.cmi_eerr enable row level security;

-- Solo el administrador puede leer, cargar y borrar (datos financieros sensibles)
create policy "eerr admin select" on public.cmi_eerr for select to authenticated
  using ((auth.jwt() ->> 'email') = 'ovictoria.sepulveda@gmail.com');
create policy "eerr admin insert" on public.cmi_eerr for insert to authenticated
  with check ((auth.jwt() ->> 'email') = 'ovictoria.sepulveda@gmail.com');
create policy "eerr admin delete" on public.cmi_eerr for delete to authenticated
  using ((auth.jwt() ->> 'email') = 'ovictoria.sepulveda@gmail.com');
