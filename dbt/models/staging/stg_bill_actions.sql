-- One row per official action in each bill's LegiScan history, in order.
select
    b.bill_id,
    h.seq::int                                  as action_seq,
    nullif(h.item->>'date', '')::date           as action_date,
    h.item->>'chamber'                          as chamber_code,
    h.item->>'action'                           as action,
    coalesce((h.item->>'importance')::int, 0) = 1 as is_major
from {{ source('raw', 'bills') }} as b
cross join lateral jsonb_array_elements(b.data->'bill'->'history')
    with ordinality as h(item, seq)