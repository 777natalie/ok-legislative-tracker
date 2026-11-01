with final_votes as (
    select
        v.roll_call_id,
        p.party,
        v.vote_text
    from {{ ref('stg_votes') }} as v
    join {{ ref('stg_people') }} as p
        on p.people_id = v.people_id
    join {{ ref('stg_roll_calls') }} as r
        on r.roll_call_id = v.roll_call_id
    where r.vote_category = 'final_passage'
      and v.vote_text in ('Yea', 'Nay')
),

party_counts as (
    select
        roll_call_id,
        party,
        sum(case when vote_text = 'Yea' then 1 else 0 end) as yeas,
        sum(case when vote_text = 'Nay' then 1 else 0 end) as nays
    from final_votes
    group by roll_call_id, party
),

party_positions as (
    select
        roll_call_id,
        party,
        case
            when yeas > nays then 'Yea'
            when nays > yeas then 'Nay'
            else 'Tie'
        end as majority_position
    from party_counts
)

select
    rc.roll_call_id,
    rep.majority_position as republican_position,
    dem.majority_position as democrat_position,
    coalesce(
        rep.majority_position in ('Yea', 'Nay')
        and dem.majority_position in ('Yea', 'Nay')
        and rep.majority_position <> dem.majority_position,
        false
    ) as is_party_unity_vote
from (select distinct roll_call_id from party_positions) as rc
left join party_positions as rep
    on rep.roll_call_id = rc.roll_call_id and rep.party = 'R'
left join party_positions as dem
    on dem.roll_call_id = rc.roll_call_id and dem.party = 'D'