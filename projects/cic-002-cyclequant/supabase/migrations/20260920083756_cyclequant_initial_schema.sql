-- CycleQuant's hosted store is append-only for research/audit records and
-- exposes only explicitly published projections to browser clients.

create table public.cq_market_snapshots (
    id text primary key,
    as_of timestamptz not null,
    captured_at timestamptz not null default now(),
    symbol text not null check (symbol = 'BTC/USD'),
    spot_price numeric not null check (spot_price > 0),
    private_payload jsonb not null,
    integrity_hash text not null unique check (length(integrity_hash) = 64)
);

create index cq_market_snapshots_as_of_idx
    on public.cq_market_snapshots (as_of desc);

create table public.cq_decisions (
    id text primary key,
    decision_date date not null unique,
    created_at timestamptz not null,
    strategy_version text not null,
    market_snapshot_id text not null references public.cq_market_snapshots(id),
    current_exposure integer not null check (current_exposure in (0, 25, 50, 75, 100)),
    target_exposure integer not null check (target_exposure in (0, 25, 50, 75, 100)),
    action text not null check (action in ('BUY', 'SELL', 'HOLD')),
    total_score numeric not null check (total_score between 0 and 100),
    confidence text not null check (confidence in ('Low', 'Medium', 'High')),
    public_payload jsonb not null,
    private_payload jsonb not null,
    integrity_hash text not null unique check (length(integrity_hash) = 64),
    is_published boolean not null default true
);

create index cq_decisions_created_at_idx
    on public.cq_decisions (created_at desc);

create table public.cq_order_events (
    id text primary key,
    decision_id text not null references public.cq_decisions(id),
    order_id text,
    event_type text not null,
    status text not null,
    occurred_at timestamptz not null,
    public_payload jsonb not null,
    private_payload jsonb not null,
    integrity_hash text not null unique check (length(integrity_hash) = 64),
    is_published boolean not null default true
);

create index cq_order_events_decision_idx
    on public.cq_order_events (decision_id, occurred_at);

create table public.cq_idempotency_keys (
    key text primary key,
    decision_date date not null,
    created_at timestamptz not null default now()
);

create table public.cq_performance_daily (
    as_of date primary key,
    cyclequant_value numeric not null check (cyclequant_value >= 0),
    btc_buy_hold_value numeric not null check (btc_buy_hold_value >= 0),
    cash_value numeric not null check (cash_value >= 0),
    ma200_value numeric check (ma200_value >= 0),
    btc_price numeric not null check (btc_price > 0),
    btc_exposure integer not null check (btc_exposure in (0, 25, 50, 75, 100)),
    created_at timestamptz not null default now(),
    is_published boolean not null default true
);

create or replace function public.cq_reject_audit_mutation()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    raise exception 'CycleQuant audit rows are immutable';
end;
$$;

create trigger cq_market_snapshots_immutable
before update or delete on public.cq_market_snapshots
for each row execute function public.cq_reject_audit_mutation();

create trigger cq_decisions_immutable
before update or delete on public.cq_decisions
for each row execute function public.cq_reject_audit_mutation();

create trigger cq_order_events_immutable
before update or delete on public.cq_order_events
for each row execute function public.cq_reject_audit_mutation();

alter table public.cq_market_snapshots enable row level security;
alter table public.cq_decisions enable row level security;
alter table public.cq_order_events enable row level security;
alter table public.cq_idempotency_keys enable row level security;
alter table public.cq_performance_daily enable row level security;

create policy "published decisions are publicly readable"
on public.cq_decisions for select
to anon, authenticated
using (is_published = true);

create policy "published order events are publicly readable"
on public.cq_order_events for select
to anon, authenticated
using (is_published = true);

create policy "published performance is publicly readable"
on public.cq_performance_daily for select
to anon, authenticated
using (is_published = true);

revoke all on public.cq_market_snapshots from anon, authenticated;
revoke all on public.cq_decisions from anon, authenticated;
revoke all on public.cq_order_events from anon, authenticated;
revoke all on public.cq_idempotency_keys from anon, authenticated;
revoke all on public.cq_performance_daily from anon, authenticated;

grant select (
    id,
    decision_date,
    created_at,
    strategy_version,
    current_exposure,
    target_exposure,
    action,
    total_score,
    confidence,
    public_payload,
    integrity_hash,
    is_published
) on public.cq_decisions to anon, authenticated;

grant select (
    id,
    decision_id,
    order_id,
    event_type,
    status,
    occurred_at,
    public_payload,
    integrity_hash,
    is_published
) on public.cq_order_events to anon, authenticated;

grant select on public.cq_performance_daily to anon, authenticated;

grant all on public.cq_market_snapshots to service_role;
grant all on public.cq_decisions to service_role;
grant all on public.cq_order_events to service_role;
grant all on public.cq_idempotency_keys to service_role;
grant all on public.cq_performance_daily to service_role;

create view public.cq_public_decisions
with (security_invoker = true)
as
select
    id,
    decision_date,
    created_at,
    strategy_version,
    current_exposure,
    target_exposure,
    action,
    total_score,
    confidence,
    public_payload as payload,
    integrity_hash
from public.cq_decisions
where is_published = true;

create view public.cq_public_order_events
with (security_invoker = true)
as
select
    id,
    decision_id,
    order_id,
    event_type,
    status,
    occurred_at,
    public_payload as payload,
    integrity_hash
from public.cq_order_events
where is_published = true;

create view public.cq_public_performance
with (security_invoker = true)
as
select
    as_of,
    cyclequant_value,
    btc_buy_hold_value,
    cash_value,
    ma200_value,
    btc_price,
    btc_exposure,
    created_at
from public.cq_performance_daily
where is_published = true;

revoke all on public.cq_public_decisions from anon, authenticated;
revoke all on public.cq_public_order_events from anon, authenticated;
revoke all on public.cq_public_performance from anon, authenticated;
grant select on public.cq_public_decisions to anon, authenticated;
grant select on public.cq_public_order_events to anon, authenticated;
grant select on public.cq_public_performance to anon, authenticated;
