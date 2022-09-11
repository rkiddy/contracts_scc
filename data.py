
from flask import request
from sqlalchemy import create_engine, inspect

engine = create_engine('mysql+pymysql://ray:alexna11@localhost/ca_scc_contracts')
conn = engine.connect()
inspector = inspect(engine)

def latest_month():
    sql = 'select pk, month from months where approved is not NULL order by month desc limit 1;'
    row = conn.execute(sql).fetchone()
    return [row['pk'], row['month']]


def money(cents):
    cents = int(cents) / 100
    cents = str(cents)
    return "$ {:,.2f}".format(float(cents))


# rows is a result cursor, columns is a dictionary or key -> column number in rows.
def fill_in_table(rows, columns):
    result = list()
    for row in rows:
        found = dict()
        for key in columns.keys():
            if key == 'amount':
                found[key] = money(row[columns[key]])
            else:
                found[key] = row[columns[key]]
        result.append(found)
    return result


def order_dicts_by_key(data, key, make_keys_unique=False):
    results = list()
    values = sorted(list(set([ d[key] for d in data ])))
    for value in values:
        for data_dict in data:
            if data_dict[key] == value:
                results.append(data_dict)
    return results


def build(page):

    if page == 'scc_main':
        return build_scc_main()

    if page == 'scc_agencies':
        return build_scc_agencies()

    if page == 'scc_costs':
        return {}

    if page == 'scc_vendors':
        return build_scc_vendors()

    if page == 'scc_descs':
        return build_scc_descs()


def build_scc_main():

    top_vendors_sql = """
    select v1.pk as vendorPk, v1.name as vendor_name,
    sum(y1.contract_value) as total_value
    from contracts c1, contract_years y1, vendors v1
    where c1.pk = y1.contract_pk
    and c1.vendor_pk = v1.pk
    and c1.month_pk = __MONTH_PK__ and y1.year = __LATEST_YEAR__
    group by v1.pk order by total_value desc limit 5
    """

    top_agencies_sql = """
    select unit_pk as agency_pk,
    (select unit_name from budget_units where pk = agency_pk) as agency_name,
    (select sum(y1.contract_value) from contracts c1,
    budget_unit_joins j1, contract_years y1
    where c1.pk = j1.contract_pk and
    y1.contract_pk = c1.pk and
    y1.year = __LATEST_YEAR__ and
    j1.unit_pk = agency_pk and
    c1.month_pk = __MONTH_PK__) as total_value
    from budget_unit_joins group by unit_pk
    order by total_value desc limit 5
    """

    top_descs_sql = """
    select commodity_desc as description,
    sum(contract_value) as total_value
    from contracts where month_pk = __MONTH_PK__
    group by commodity_desc order by total_value desc limit 5
    """

    costs_sql = """
    select c1.pk, y1.contract_value from contracts c1, contract_years y1
    where c1.pk = y1.contract_pk
    and y1.year = __LATEST_YEAR__
    and c1.month_pk = __MONTH_PK__
    and y1.contract_value >= __MIN__
    and y1.contract_value < __MAX__
    """

    context = dict()

    [month_pk, month] = latest_month()
    context['current_month'] = month
    context['current_year'] = month.split('-')[0]

    sql = top_vendors_sql
    sql = sql.replace('__MONTH_PK__', str(month_pk))
    sql = sql.replace('__LATEST_YEAR__', month.split('-')[0])

    rows = conn.execute(sql).fetchall()
    context['top_vendors'] = fill_in_table(rows, {'pk':0, 'name': 1, 'amount': 2})

    sql = top_agencies_sql;
    sql = sql.replace('__MONTH_PK__', str(month_pk))
    sql = sql.replace('__LATEST_YEAR__', month.split('-')[0])

    rows = conn.execute(sql).fetchall()
    context['top_agencies'] = fill_in_table(rows, {'pk':0, 'name': 1, 'amount': 2})

    sql = top_descs_sql;
    sql = sql.replace('__MONTH_PK__', str(month_pk))
    sql = sql.replace('__LATEST_YEAR__', month.split('-')[0])

    rows = conn.execute(sql).fetchall()
    context['top_descs'] = fill_in_table(rows, {'name': 0, 'amount': 1})

    costs_tables = list()
    min = 0
    max = 1

    for idx in range(8):
        sql = costs_sql
        sql = sql.replace('__MONTH_PK__', str(month_pk))
        sql = sql.replace('__LATEST_YEAR__', month.split('-')[0])
        sql = sql.replace('__MIN__', str(min * 100))
        sql = sql.replace('__MAX__', str(max * 100))

        rows = conn.execute(sql).fetchall()
        contracts_count = len(rows)
        contracts_sum = sum([r['contract_value'] for r in rows])
        costs_tables.append(
            {'min': f"{min}.00",
             'max': f"{max}.00",
             'sum': money(contracts_sum),
             'count': int(contracts_count)})

        min = max
        max = max * 10

    context['costs'] = costs_tables

    context['sources'] = dict()
    sql = f"select source_url from sources where month_pk = {month_pk} and source_url like '%%document/Contract%%'"
    context['sources']['contract_rpt'] = conn.execute(sql).fetchone()['source_url']

    sql = f"select source_url from sources where month_pk = {month_pk} and source_url like '%%document/Contract%%'"
    context['sources']['sabc_rpt'] = conn.execute(sql).fetchone()['source_url']

    return context


def build_scc_vendors():

    vendors_by_letter_sql = """
    select v1.name, v1.pk, min(c1.effective_date) as eff_date,
    max(c1.expir_date) as expir_date, sum(c1.contract_value) as sum_all,
    sum(y1.contract_value) as sum_year
    from vendors v1, contracts c1, contract_years y1
    where v1.pk = c1.vendor_pk and
    c1.pk = y1.contract_pk and
    v1.name like '__FIRST_LETTER__%%' and
    c1.month_pk = __MONTH_PK__ and
    y1.year = __LATEST_YEAR__
    group by v1.pk order by v1.name
    """

    non_alpha_vendors_sql = """
    select v1.name, v1.pk, min(c1.effective_date) as eff_date,
    max(c1.expir_date) as expir_date, sum(c1.contract_value) as sum_all,
    sum(y1.contract_value) as sum_year
    from vendors v1, contracts c1, contract_years y1
    where v1.pk = c1.vendor_pk and
    c1.pk = y1.contract_pk and
    c1.month_pk = __MONTH_PK__ and
    y1.year = __LATEST_YEAR__ and
    (v1.name < 'A' or v1.name > 'Z_')
    group by v1.pk order by v1.name
    """

    all_vendors_sql = """
    select v1.name, v1.pk, min(c1.effective_date) as eff_date,
    max(c1.expir_date) as expir_date, sum(c1.contract_value) as sum_all,
    sum(y1.contract_value) as sum_year
    from vendors v1, contracts c1, contract_years y1
    where v1.pk = c1.vendor_pk and
    c1.pk = y1.contract_pk and
    c1.month_pk = __MONTH_PK__ and
    y1.year = __LATEST_YEAR__
    group by v1.pk order by v1.name
    """

    agencies_for_vendor_sql = """
    select v1.pk as vendor_pk, b1.pk as unit_pk, b1.unit_name as name
    from vendors v1, contracts c1, budget_unit_joins j1, budget_units b1
    where v1.name like '__FIRST_LETTER__%%' and
    v1.pk = c1.vendor_pk and
    c1.month_pk = __MONTH_PK__ and
    c1.pk = j1.contract_pk and
    j1.unit_pk = b1.pk
    """

    p = request.path

    if p.endswith('vendors'):
        first_letter = 'A'
    else:
        first_letter = p.split('/')[-1].replace('/', '')

    context = dict()

    [month_pk, month] = latest_month()
    context['current_month'] = month
    context['current_year'] = month.split('-')[0]

    if first_letter == 'NA':
        sql = non_alpha_vendors_sql
    elif first_letter == 'All':
        sql = all_vendors_sql
    else:
        sql = vendors_by_letter_sql

    sql = sql.replace('__MONTH_PK__', str(month_pk))
    sql = sql.replace('__FIRST_LETTER__', first_letter)
    sql = sql.replace('__LATEST_YEAR__', month.split('-')[0])
    rows = conn.execute(sql).fetchall()
    cols = {'name': 0, 'vendor_pk': 1, 'eff_date': 2, 'exp_date': 3, 'sum_all': 4, 'sum_year': 5}
    context['vendors'] = fill_in_table(rows, cols)

    for vendor in context['vendors']:
        vendor['sum_all'] = money(vendor['sum_all'])
        vendor['sum_year'] = money(vendor['sum_year'])
        vendor['vendor_pk'] = int(vendor['vendor_pk'])
        vendor['agencies'] = dict()

    sql = agencies_for_vendor_sql
    sql = sql.replace('__MONTH_PK__', str(month_pk))
    sql = sql.replace('__FIRST_LETTER__', first_letter)
    rows = conn.execute(sql).fetchall()
    agencies = fill_in_table(rows, {'vendor_pk': 0, 'unit_pk': 1, 'unit_name': 2})

    for vendor in context['vendors']:
        for agency in agencies:
            if vendor['vendor_pk'] == agency['vendor_pk']:
                vendor['agencies'][agency['unit_pk']] = {'pk': agency['unit_pk'], 'name': agency['unit_name']}

        vendor['agencies'] = list(vendor['agencies'].values())

    return context


def build_scc_agencies():

    agencies_sql = """
    select b1.unit_name, b1.pk,
    min(c1.effective_date), max(c1.expir_date),
    sum(c1.contract_value), sum(y1.contract_value)
    from budget_units b1, budget_unit_joins j1, contracts c1, contract_years y1
    where b1.pk = j1.unit_pk and
    j1.contract_pk = c1.pk and
    c1.pk = y1.contract_pk and
    y1.year = __LATEST_YEAR__ and
    c1.month_pk = __MONTH_PK__ group by b1.pk
    order by b1.unit_name
    """

    vendors_for_agencies_sql = """
    select b1.pk, v1.pk, v1.name
    from budget_units b1, budget_unit_joins j1, contracts c1, vendors v1
    where b1.pk = j1.unit_pk and
    j1.contract_pk = c1.pk and
    c1.vendor_pk = v1.pk and
    c1.month_pk = __MONTH_PK__
    """

    context = dict()

    [month_pk, month] = latest_month()
    context['current_month'] = month
    context['current_year'] = month.split('-')[0]

    sql = agencies_sql
    sql = sql.replace('__MONTH_PK__', str(month_pk))
    sql = sql.replace('__LATEST_YEAR__', month.split('-')[0])
    rows = conn.execute(sql).fetchall()
    cols = {'name': 0, 'agency_pk': 1, 'eff_date': 2, 'exp_date': 3, 'sum_all': 4, 'sum_year': 5}
    context['agencies'] = fill_in_table(rows, cols)

    for agency in context['agencies']:
        agency['sum_all'] = money(agency['sum_all'])
        agency['sum_year'] = money(agency['sum_year'])
        agency['vendors'] = dict()

    sql = vendors_for_agencies_sql
    sql = sql.replace('__MONTH_PK__', str(month_pk))
    rows = conn.execute(sql).fetchall()
    vendors = fill_in_table(rows, {'agency_pk': 0, 'vendor_pk': 1, 'vendor_name': 2})

    for agency in context['agencies']:
        for vendor in vendors:
            if agency['agency_pk'] == vendor['agency_pk']:
                pk = vendor['vendor_pk']
                agency['vendors'][pk] = {'pk': pk, 'name': vendor['vendor_name']}

        agency['vendors'] = list(agency['vendors'].values())

    return context


def build_scc_descs():

    descs_sql = """
    select c1.commodity_desc,
    sum(c1.contract_value), sum(y1.contract_value),
    min(c1.effective_date), max(c1.expir_date)
    from contracts c1, contract_years y1
    where c1.pk = y1.contract_pk and 
    c1.month_pk = __MONTH_PK__ and
    y1.year = __LATEST_YEAR__
    group by c1.commodity_desc
    order by c1.commodity_desc;
    """

    agencies_for_descs_sql = """
    select c1.commodity_desc, b1.pk, b1.unit_name
    from contracts c1, budget_unit_joins j1, budget_units b1
    where c1.pk = j1.contract_pk and j1.unit_pk = b1.pk and
    c1.month_pk = __MONTH_PK__
    """

    vendors_fpr_descs_sql = """
    select c1.commodity_desc, v1.pk, v1.name
    from contracts c1, vendors v1
    where c1.month_pk = __MONTH_PK__ and c1.vendor_pk = v1.pk
    """

    context = dict()

    [month_pk, month] = latest_month()
    context['current_month'] = month
    context['current_year'] = month.split('-')[0]

    context = dict()

    sql = descs_sql
    sql = sql.replace('__MONTH_PK__', str(month_pk))
    sql = sql.replace('__LATEST_YEAR__', month.split('-')[0])
    rows = conn.execute(sql).fetchall()
    cols = {'description': 0, 'sum_all': 1, 'sum_year': 2, 'eff_date': 3, 'exp_date': 4}
    context['descs'] = fill_in_table(rows, cols)

    for desc in context['descs']:
        desc['sum_all'] = money(desc['sum_all'])
        desc['sum_year'] = money(desc['sum_year'])
        desc['vendors'] = dict()
        desc['agencies'] = dict()

    sql = vendors_fpr_descs_sql
    sql = sql.replace('__MONTH_PK__', str(month_pk))
    rows = conn.execute(sql).fetchall()
    vendors = fill_in_table(rows, {'description': 0, 'vendor_pk': 1, 'vendor_name': 2})

    for desc in context['descs']:
        for vendor in vendors:
            if desc['description'] == vendor['description']:
                pk = vendor['vendor_pk']
                desc['vendors'][pk] = {'pk': pk, 'name': vendor['vendor_name']}

        desc['vendors'] = list(desc['vendors'].values())

    sql = agencies_for_descs_sql
    sql = sql.replace('__MONTH_PK__', str(month_pk))
    rows = conn.execute(sql).fetchall()
    agencies = fill_in_table(rows, {'description': 0, 'agency_pk': 1, 'agency_name': 2})

    for desc in context['descs']:
        for agency in agencies:
            if desc['description'] == agency['description']:
                pk = agency['agency_pk']
                desc['agencies'][pk] = {'pk': pk, 'name': agency['agency_name']}

        desc['agencies'] = list(desc['agencies'].values())

    return context
