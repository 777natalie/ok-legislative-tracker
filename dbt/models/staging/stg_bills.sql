select
    bill_id,
    session_id,
    data->'bill'->'session'->>'session_name'             as session_name,
    change_hash,
    data->'bill'->>'bill_number'                         as bill_number,
    data->'bill'->>'title'                               as title,
    case data->'bill'->>'body'
        when 'H' then 'House'
        when 'S' then 'Senate'
    end                                                  as origin_chamber,
    (data->'bill'->>'status')::int                       as status_code,
    case (data->'bill'->>'status')::int
        when 1 then 'Introduced'
        when 2 then 'Engrossed'
        when 3 then 'Enrolled'
        when 4 then 'Passed'
        when 5 then 'Vetoed'
        when 6 then 'Failed'
    end                                                  as status,
    nullif(data->'bill'->>'status_date', '')::date       as status_date,
    (data->'bill'->>'completed')::int = 1                as completed,
    (data->'bill'->'progress'->0->>'date')::date         as introduced_date,
    exists (
        select 1
        from jsonb_array_elements(coalesce(data->'bill'->'sasts', '[]'::jsonb)) as s
        where s->>'type' = 'Carry Over'
    )                                                    as is_carryover,
    jsonb_array_length(coalesce(data->'bill'->'subjects', '[]'::jsonb))
                                                         as subject_count
from {{ source('raw', 'bills') }}