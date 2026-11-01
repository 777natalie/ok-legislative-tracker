with unity_votes as (
    select roll_call_id, session_id, republican_position, democrat_position
    from {{ ref('int_party_positions') }}
    where is_party_unity_vote
),

legislator_votes as (
    select
        u.session_id,
        v.people_id,
        p.name,
        p.party,
        p.chamber,
        p.district_code,
        v.vote_text,
        case p.party
            when 'R' then u.republican_position
            when 'D' then u.democrat_position
        end as party_position
    from {{ ref('stg_votes') }} as v
    join unity_votes as u
        on u.roll_call_id = v.roll_call_id
    join {{ ref('stg_people') }} as p
        on p.people_id = v.people_id
    where v.vote_text in ('Yea', 'Nay')
)

select
    session_id,
    people_id,
    name,
    party,
    chamber,
    district_code,
    count(*) as unity_votes_cast,
    sum(case when vote_text = party_position then 1 else 0 end) as votes_with_party,
    round(
        100.0 * sum(case when vote_text = party_position then 1 else 0 end) / count(*),
        1
    ) as party_unity_pct
from legislator_votes
group by session_id, people_id, name, party, chamber, district_code