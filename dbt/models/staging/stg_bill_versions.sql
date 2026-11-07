-- One row per stored version of a bill, with the fields we compare between versions.
select
    bill_id,
    change_hash,
    fetched_at,
    source,
    (data->'bill'->>'status')::int                        as status,
    nullif(data->'bill'->>'status_date', '')::date        as status_date,
    data->'bill'->'history'->-1->>'action'                as last_action,
    nullif(data->'bill'->'history'->-1->>'date', '')::date as last_action_date,
    jsonb_array_length(data->'bill'->'history')           as action_count
from {{ source('raw', 'bill_versions') }}