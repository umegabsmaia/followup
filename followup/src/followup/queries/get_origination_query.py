def get_origination_query(
        project: str,
        database:str,
        table:str
) -> str:
    '''
    Query to retrieve the origination data.

    Args:
        project (str): The bigquery project.
        database (str): The bigquery database.
        table (str): The table where are the origination data to retrieve.
    
    Returns:
        query (str): A query to retrieve the origination data  


    '''

    # check for empty strings
    if project == '' or database == '' or table == '':
        raise ValueError("project, database, and table must be non-empty strings.")
    
    query = f"""
    select *, 
    CASE 
        WHEN orig_month = conv_month THEN "New"
        ELSE "Recurrent"
    END as tipo_cliente,
    
    CASE 
        WHEN retailerId = app_retailer THEN 0
        ELSE 1
    END as cross_sell,
    
    CASE 
        WHEN orig_month = conv_month AND conv_date = app_date THEN "Same Day"
        WHEN orig_month = conv_month AND conv_date <> app_date THEN "Late Conversion" 
        ELSE NULL
    END as conv_type,
    
    CASE 
        WHEN orig_date = conv_date THEN DATE_DIFF(conv_date, app_date, DAY)
        ELSE NULL
    END as conv_days_since_app,
    
    ROW_NUMBER() OVER (PARTITION BY borrowerId ORDER BY originationTimestamp) as n_compra,
    ROW_NUMBER() OVER (PARTITION BY borrowerId ORDER BY originationTimestamp) - 1 as n_ultima_compra,
    ROW_NUMBER() OVER (PARTITION BY borrowerId ORDER BY originationTimestamp) - 2 as n_penultima_compra
    
    from (
        select `prd_datastore_public.origination_summaries`.borrowerId,
        `prd_datastore_public.origination_summaries`.originationTimestamp,
        `prd_datastore_public.origination_summaries`.financedValue,
        `prd_datastore_public.origination_summaries`.retailerId,
        `prd_datastore_public.origination_summaries`.storeId,
        `prd_datastore_public.origination_summaries`.contractId,
        `prd_datastore_public.origination_summaries`.installmentValue,
        `prd_datastore_public.origination_summaries`.numberOfInstallments,
        `prd_datastore_public.stores`.name as storeName, `prd_datastore_public.retailers`.fantasyName as retailer_name, 
        CASE
            WHEN `prd_datastore_public.origination_summaries`.storeId in (772,812,897) THEN app_city
            ELSE `prd_datastore_public.address`.city
        END as city,
        CASE
            WHEN `prd_datastore_public.origination_summaries`.storeId in (772,812,897) THEN app_state
            ELSE `prd_datastore_public.address`.federativeUnit
        END as state,
        CASE
            WHEN `prd_datastore_public.origination_summaries`.storeId in (772,812,897) THEN app_address
            ELSE `prd_datastore_public.address`.id
        END as addressId,
        app_date,
        app_retailer,
        app_retailer_name,
        app_city,
        app_state,
        DATE(`prd_datastore_public.origination_summaries`.originationTimestamp, '-04:00') as orig_date, 
        DATE_TRUNC(DATE(`prd_datastore_public.origination_summaries`.originationTimestamp, '-04:00'), MONTH) as orig_month,
        MIN(DATE(`prd_datastore_public.origination_summaries`.originationTimestamp, '-04:00')) OVER (PARTITION BY `prd_datastore_public.origination_summaries`.borrowerId) as conv_date, 
        MIN(DATE_TRUNC(DATE(`prd_datastore_public.origination_summaries`.originationTimestamp, '-04:00'), MONTH)) OVER (PARTITION BY `prd_datastore_public.origination_summaries`.borrowerId) as conv_month,
        CASE 
            WHEN `prd_datastore_public.origination_summaries`.storeId in (812,897) THEN "PL"
            WHEN `prd_datastore_public.origination_summaries`.storeId = 772 THEN "Pix"
            WHEN `prd_datastore_public.contracts`.sourceProduct = "HIGH_RECURRENCE" THEN "Ume Leve"
            ELSE "Conventional"
        END as product,
        
        from `{project}.{database}.{table}`
        left join `prd_datastore_public.stores` on `prd_datastore_public.stores`.id = `prd_datastore_public.origination_summaries`.storeId
        left join `prd_datastore_public.retailers` on `prd_datastore_public.retailers`.id = `prd_datastore_public.stores`.retailerId
        left join `prd_datastore_public.address` on `prd_datastore_public.address`.id = `prd_datastore_public.stores`.addressId
        LEFT JOIN `prd_datastore_public.contracts` ON `prd_datastore_public.contracts`.id = `prd_datastore_public.origination_summaries`.contractId
        left join (
        select distinct 
        `prd_datastore_public.applications`.borrowerId as id_cliente,
        DATE(`prd_datastore_public.applications`.createdOn, "-4:00") as app_date,
        `prd_datastore_public.stores`.retailerId as app_retailer,
        `prd_datastore_public.retailers`.fantasyName as app_retailer_name,
        `prd_datastore_public.address`.city as app_city,
        `prd_datastore_public.address`.federativeUnit as app_state,
        `prd_datastore_public.address`.id as app_address,
        ROW_NUMBER() OVER (PARTITION BY `prd_datastore_public.applications`.borrowerId ORDER BY `prd_datastore_public.applications`.createdOn asc) as app_rn
        
        from `prd_datastore_public.applications`
        left join `prd_datastore_public.stores` on `prd_datastore_public.stores`.id = `prd_datastore_public.applications`.storeId
        left join `prd_datastore_public.address` on `prd_datastore_public.stores`.addressId = `prd_datastore_public.address`.id
        left join `prd_datastore_public.retailers` on `prd_datastore_public.stores`.retailerId = `prd_datastore_public.retailers`.id
        where `prd_datastore_public.applications`.status = "APPROVED" 
        ) on id_cliente = `prd_datastore_public.origination_summaries`.borrowerId AND app_rn = 1
        WHERE `prd_datastore_public.origination_summaries`.canceledOn is null
    ) WHERE 1=1
"""
    return query