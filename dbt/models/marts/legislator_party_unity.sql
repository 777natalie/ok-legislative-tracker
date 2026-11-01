select
    f.session_id,
    f.people_id,
    d.name,
    d.party,
    d.chamber,
    d.district_code,
    count(*) as unity_votes_cast,
    sum(case when f.voted_with_party then 1 else 0 end) as votes_with_party,
    round(
        100.0 * sum(case when f.voted_with_party then 1 else 0 end) / count(*),
        1
    ) as party_unity_pct
from {{ ref('fct_unity_votes') }} as f
join {{ ref('dim_legislators') }} as d
    on d.people_id = f.people_id
group by f.session_id, f.people_id, d.name, d.party, d.chamber, d.district_code