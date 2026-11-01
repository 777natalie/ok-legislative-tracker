select session_id, people_id, count(*) as n
from {{ ref('legislator_party_unity') }}
group by session_id, people_id
having count(*) > 1