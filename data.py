
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


def build(page):

    if page == 'scc_main':
        return build_scc_main()

    if page == 'scc_agencies':
        return {}

    if page == 'scc_costs':
        return {}

    if page == 'scc_vendors':
        return build_scc_vendors()

    if page == 'scc_descs':
        return {}


def build_scc_main():

    top_vendors_sql = """
    select v1.pk as vendorPk, v1.name as vendor_name,
    sum(y1.contract_value) as total_value
    from contracts c1, contract_years y1, vendors v1
    where c1.pk = y1.contract_pk
    and c1.vendor_pk = v1.pk
    and c1.month_pk = __MONTH_PK__ and y1.year = __YEAR__
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

    sql = top_vendors_sql
    sql = sql.replace('__MONTH_PK__', str(month_pk))
    sql = sql.replace('__YEAR__', month.split('-')[0])

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

    vendors_by_letter = """
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

    non_alpha_vendors = """
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

    all_vendors = """
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

    agencies_by_vendor = """
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
        sql = non_alpha_vendors
    elif first_letter == 'All':
        sql = all_vendors
    else:
        sql = vendors_by_letter

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

    sql = agencies_by_vendor
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
