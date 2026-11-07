select bill_id, change_hash
from {{ ref('fct_bill_changes') }}
group by 1, 2
having count(*) > 1