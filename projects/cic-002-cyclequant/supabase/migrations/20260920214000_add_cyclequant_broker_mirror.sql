-- Public broker snapshots mirror only the isolated CycleQuant paper sleeve.
-- Alpaca account IDs, credentials, and unrelated account balances never enter
-- this table's public payload.

create table public.cq_broker_snapshots (
    id text primary key,
    captured_at timestamptz not null,
    broker_mode text not null check (broker_mode in ('simulated', 'alpaca-paper')),
    connected boolean not null,
    public_payload jsonb not null,
    private_payload jsonb not null,
    integrity_hash text not null unique check (length(integrity_hash) = 64),
    is_published boolean not null default true
);

create index cq_broker_snapshots_captured_at_idx
    on public.cq_broker_snapshots (captured_at desc);

create trigger cq_broker_snapshots_immutable
before update or delete on public.cq_broker_snapshots
for each row execute function public.cq_reject_audit_mutation();

alter table public.cq_broker_snapshots enable row level security;

create policy "published broker snapshots are publicly readable"
on public.cq_broker_snapshots for select
to anon, authenticated
using (is_published = true);

create policy "scoped writer inserts broker snapshots"
on public.cq_broker_snapshots for insert
to anon
with check ((select cyclequant_private.cq_request_is_writer()));

revoke all on public.cq_broker_snapshots from anon, authenticated;

grant select (
    id,
    captured_at,
    broker_mode,
    connected,
    public_payload,
    integrity_hash,
    is_published
) on public.cq_broker_snapshots to anon, authenticated;

grant insert on public.cq_broker_snapshots to anon;
grant all on public.cq_broker_snapshots to service_role;

create view public.cq_public_broker_snapshots
with (security_invoker = true)
as
select
    id,
    captured_at,
    broker_mode,
    connected,
    public_payload as payload,
    integrity_hash
from public.cq_broker_snapshots
where is_published = true;

revoke all on public.cq_public_broker_snapshots from anon, authenticated;
grant select on public.cq_public_broker_snapshots to anon, authenticated;
