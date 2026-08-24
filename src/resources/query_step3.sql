select 
	a.account_id
	,a.name
	,a.address		
	,ds.changed_datetime as latest_update_datetime
	,ds.queue
	,ds.status			
from "Daily_Status" ds
inner join "Accounts" a
	on ds.account = a.account_id
where ds.changed_datetime::date >= DATE '2025-01-01';