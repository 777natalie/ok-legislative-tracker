with counted as (
    select roll_call_id, count(*) as vote_rows
    from {{ ref('stg_votes') }}
    group by roll_call_id
)
select r.roll_call_id, r.total, c.vote_rows
from {{ ref('stg_roll_calls') }} as r
left join counted as c using (roll_call_id)
where r.total <> coalesce(c.vote_rows, 0)