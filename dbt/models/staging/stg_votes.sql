select
    r.roll_call_id,
    (v.vote->>'people_id')::int  as people_id,
    (v.vote->>'vote_id')::int    as vote_id,
    v.vote->>'vote_text'         as vote_text
from {{ source('raw', 'roll_calls') }} as r
cross join lateral jsonb_array_elements(r.data->'roll_call'->'votes') as v(vote)