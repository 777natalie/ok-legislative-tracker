-- One row per bill version, compared to the version before it.
-- Notifications will select rows where is_first_version = false
-- and (status_changed or new_actions > 0).
with versions as (
    select
        *,
        row_number()             over w as version_num,
        lag(change_hash)         over w as prev_change_hash,
        lag(status)              over w as prev_status,
        lag(action_count)        over w as prev_action_count
    from {{ ref('stg_bill_versions') }}
    window w as (partition by bill_id order by fetched_at, change_hash)
)

select
    bill_id,
    change_hash,
    version_num,
    fetched_at,
    source,
    status,
    prev_status,
    status_date,
    last_action,
    last_action_date,
    action_count - coalesce(prev_action_count, 0)           as new_actions,
    prev_change_hash is null                                as is_first_version,
    prev_change_hash is not null
        and status is distinct from prev_status             as status_changed
from versions