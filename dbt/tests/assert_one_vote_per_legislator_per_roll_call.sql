select roll_call_id, people_id, count(*) as n
from {{ ref('stg_votes') }}
group by roll_call_id, people_id
having count(*) > 1