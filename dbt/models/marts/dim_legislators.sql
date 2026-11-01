select
    people_id,
    name,
    first_name,
    last_name,
    party,
    chamber,
    district_code,
    district_number,
    capitol_phone,
    photo_url,
    ballotpedia_slug
from {{ ref('stg_people') }}