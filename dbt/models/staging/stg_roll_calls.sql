select
    roll_call_id,
    bill_id,
    (data->'roll_call'->>'date')::date        as vote_date,
    data->'roll_call'->>'desc'                as description,
    case data->'roll_call'->>'chamber'
        when 'H' then 'House'
        when 'S' then 'Senate'
    end                                       as chamber,
    (data->'roll_call'->>'yea')::int          as yea,
    (data->'roll_call'->>'nay')::int          as nay,
    (data->'roll_call'->>'nv')::int           as not_voting,
    (data->'roll_call'->>'absent')::int       as absent,
    (data->'roll_call'->>'total')::int        as total,
    (data->'roll_call'->>'passed')::int = 1   as passed,
    case
        when data->'roll_call'->>'desc' ilike '%committee%'      then 'committee'
        when data->'roll_call'->>'desc' ilike '%third reading%'
          or data->'roll_call'->>'desc' ilike '%fourth reading%' then 'final_passage'
        when data->'roll_call'->>'desc' ilike '%veto override%'  then 'veto_override'
        when data->'roll_call'->>'desc' ilike '%emergency%'      then 'emergency'
        else 'procedural'
    end                                       as vote_category
from {{ source('raw', 'roll_calls') }}