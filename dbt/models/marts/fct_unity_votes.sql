with unity as (
    select roll_call_id, session_id, republican_position, democrat_position
    from {{ ref('int_party_positions') }}
    where is_party_unity_vote
),

votes as (
    select
        u.session_id,
        v.roll_call_id,
        v.people_id,
        r.vote_date,
        r.bill_id,
        b.bill_number,
        b.title,
        b.state_url,
        p.party,
        v.vote_text,
        case p.party
            when 'R' then u.republican_position
            when 'D' then u.democrat_position
        end as party_position
    from {{ ref('stg_votes') }} as v
    join unity as u
        on u.roll_call_id = v.roll_call_id
    join {{ ref('stg_people') }} as p
        on p.people_id = v.people_id
    join {{ ref('stg_roll_calls') }} as r
        on r.roll_call_id = v.roll_call_id
    join {{ ref('stg_bills') }} as b
        on b.bill_id = r.bill_id
    where v.vote_text in ('Yea', 'Nay')
)

select
    *,
    vote_text = party_position as voted_with_party
from votes