select bill_id, action_seq
from {{ ref('stg_bill_actions') }}
group by 1, 2
having count(*) > 1