select
    people_id,
    person_hash,
    data->'person'->>'name'                                   as name,
    data->'person'->>'first_name'                             as first_name,
    data->'person'->>'last_name'                              as last_name,
    data->'person'->>'party'                                  as party,
    case data->'person'->>'role'
        when 'Rep' then 'House'
        when 'Sen' then 'Senate'
    end                                                       as chamber,
    data->'person'->>'district'                               as district_code,
    nullif(regexp_replace(data->'person'->>'district', '\D', '', 'g'), '')::int
                                                              as district_number,
    data->'person'->'bio'->'social'->>'capitol_phone'         as capitol_phone,
    data->'person'->'bio'->'social'->>'image'                 as photo_url,
    nullif(data->'person'->>'ballotpedia', '')                as ballotpedia_slug
from {{ source('raw', 'people') }}