select distinct on (account_id)
    account_id,
    name,
    address,
    latest_update_datetime,
    queue,
    status
from "Recent_Accounts"
--where latest_update_datetime::date <= DATE '2025-11-27'
where latest_update_datetime < '2025-11-28'
  and queue in ('COLLECTIONS', 'LEGAL')
order by account_id, latest_update_datetime desc;