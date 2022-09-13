
import re
from flask import request
from sqlalchemy import create_engine, inspect

engine = create_engine('mysql+pymysql://ray:alexna11@localhost/ca_scc_contracts')
conn = engine.connect()
inspector = inspect(engine)

cost_buckets = {
    'B0': [0, 1],
    'B1': [1, 10],
    'B2': [10, 100],
    'B3': [100, 1000],
    'B4': [1000, 10000],
    'B5': [10000, 100000],
    'B6': [100000, 1000000],
    'B7': [1000000, 10000000],
    'B8': [10000000, 100000000]}

cost_labels = dict()
for key in cost_buckets:
    cost_labels[cost_buckets[key][0]] = key


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


def order_dicts_by_key(data, key):
    results = list()
    values = sorted(list(set([d[key] for d in data])))
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

    if page == 'scc_vendors':
        return build_scc_vendors()

    if page == 'scc_descs':
        return build_scc_descs()

    if page == 'scc_contracts':
        return build_contracts()

    if page == 'scc_contract':
        return build_contract()


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
    context['top_vendors'] = fill_in_table(rows, {'pk': 0, 'name': 1, 'amount': 2})

    sql = top_agencies_sql
    sql = sql.replace('__MONTH_PK__', str(month_pk))
    sql = sql.replace('__LATEST_YEAR__', month.split('-')[0])

    rows = conn.execute(sql).fetchall()
    context['top_agencies'] = fill_in_table(rows, {'pk': 0, 'name': 1, 'amount': 2})

    sql = top_descs_sql
    sql = sql.replace('__MONTH_PK__', str(month_pk))
    sql = sql.replace('__LATEST_YEAR__', month.split('-')[0])

    rows = conn.execute(sql).fetchall()
    context['top_descs'] = fill_in_table(rows, {'name': 0, 'amount': 1})

    costs_tables = list()
    min = 0
    max = 1

    for idx in range(len(cost_buckets.keys())):
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
             'label': cost_labels[min],
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

    try:
        if request.path.endswith('vendors'):
            first_letter = 'A'
        else:
            first_letter = request.path.split('/')[-1].replace('/', '')
    except:
        first_letter = 'A'

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
    cols = {'name': 0, 'pk': 1, 'eff_date': 2, 'exp_date': 3, 'sum_all': 4, 'sum_year': 5}
    context['vendors'] = fill_in_table(rows, cols)

    for vendor in context['vendors']:
        vendor['sum_all'] = money(vendor['sum_all'])
        vendor['sum_year'] = money(vendor['sum_year'])
        vendor['pk'] = int(vendor['pk'])
        vendor['agencies'] = dict()

    sql = agencies_for_vendor_sql
    sql = sql.replace('__MONTH_PK__', str(month_pk))
    sql = sql.replace('__FIRST_LETTER__', first_letter)
    rows = conn.execute(sql).fetchall()
    agencies = fill_in_table(rows, {'vendor_pk': 0, 'unit_pk': 1, 'unit_name': 2})

    for vendor in context['vendors']:
        for agency in agencies:
            if vendor['pk'] == agency['vendor_pk']:
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
    cols = {'name': 0, 'pk': 1, 'eff_date': 2, 'exp_date': 3, 'sum_all': 4, 'sum_year': 5}
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
            if agency['pk'] == vendor['agency_pk']:
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

    vendors_for_descs_sql = """
    select c1.commodity_desc, v1.pk, v1.name
    from contracts c1, vendors v1
    where c1.month_pk = __MONTH_PK__ and c1.vendor_pk = v1.pk
    """

    agencies_for_descs_sql = """
    select c1.commodity_desc, b1.pk, b1.unit_name
    from contracts c1, budget_unit_joins j1, budget_units b1
    where c1.pk = j1.contract_pk and j1.unit_pk = b1.pk and
    c1.month_pk = __MONTH_PK__
    """

    context = dict()

    [month_pk, month] = latest_month()
    context['current_month'] = month
    context['current_year'] = month.split('-')[0]

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

    sql = vendors_for_descs_sql
    sql = sql.replace('__MONTH_PK__', str(month_pk))
    rows = conn.execute(sql).fetchall()
    vendors = fill_in_table(rows, {'description': 0, 'pk': 1, 'name': 2})

    for desc in context['descs']:
        for vendor in vendors:
            if desc['description'] == vendor['description']:
                pk = vendor['pk']
                desc['vendors'][pk] = {'pk': pk, 'name': vendor['name']}

        desc['vendors'] = list(desc['vendors'].values())

    sql = agencies_for_descs_sql
    sql = sql.replace('__MONTH_PK__', str(month_pk))
    rows = conn.execute(sql).fetchall()
    agencies = fill_in_table(rows, {'description': 0, 'pk': 1, 'name': 2})

    for desc in context['descs']:
        for agency in agencies:
            if desc['description'] == agency['description']:
                pk = agency['pk']
                desc['agencies'][pk] = {'pk': pk, 'name': agency['name']}

        desc['agencies'] = list(desc['agencies'].values())

    return context


def build_contracts():

    # we must be able to build the following, based on a parameter:
    #
    # list of contract with value between to values. prefix = "B"
    #     should also include nav links for different buckets.
    #
    # list of contracts for a given vendor. prefix = "V"
    #     should also include the vendor name and vendor info.
    #
    # list of contracts for a given agency. prefix = "A"
    #     should also include the agency name and extra info for agency.
    #
    # list of contracts for a given description.
    #
    try:
        param = request.path.split('/')[-1]
    except:
        param = 'A4'

    context = dict()

    [month_pk, month] = latest_month()
    context['current_month'] = month
    context['current_year'] = month.split('-')[0]

    sql = None

    context['param'] = param

    context['param_is_bucket'] = param.startswith('B')
    context['param_is_vendor'] = param.startswith('V')
    context['param_is_description'] = param.startswith('D')

    # must check, interfered with by param 'All'.
    if re.match("^A[0-9]+$", param):
        context['param_is_agency'] = True
    else:
        context['param_is_agency'] = False

    if param == 'All':
        sql = """
        select c1.pk,
        c1.contract_id, c1.ariba_id, c1.sap_id,
        c1.vendor_pk, v1.name,
        y1.contract_value, c1.contract_value,
        effective_date, expir_date, commodity_desc
        from contracts c1, contract_years y1, vendors v1
        where c1.pk = y1.contract_pk and
        y1.year = __LATEST_YEAR__ and
        c1.vendor_pk = v1.pk and
        c1.month_pk = __MONTH_PK__
        order by c1.contract_value desc
        """

    if context['param_is_bucket']:

        sql = """
        select c1.pk,
        c1.contract_id, c1.ariba_id, c1.sap_id,
        c1.vendor_pk, v1.name,
        y1.contract_value, c1.contract_value,
        effective_date, expir_date, commodity_desc
        from contracts c1, contract_years y1, vendors v1
        where c1.pk = y1.contract_pk and
        y1.year = __LATEST_YEAR__ and
        c1.vendor_pk = v1.pk and
        c1.month_pk = __MONTH_PK__ and
        y1.contract_value >= __MIN_VALUE__ and
        y1.contract_value < __MAX_VALUE__
        order by c1.contract_value
        """

        sql = sql.replace('__MIN_VALUE__', str(int(cost_buckets[param][0]) * 100))
        sql = sql.replace('__MAX_VALUE__', str(int(cost_buckets[param][1]) * 100))

    if context['param_is_vendor']:

        pk = int(param[1:])

        sql = """
        select c1.pk,
        c1.contract_id, c1.ariba_id, c1.sap_id,
        c1.vendor_pk, v1.name,
        y1.contract_value, c1.contract_value,
        effective_date, expir_date, commodity_desc
        from contracts c1, contract_years y1, vendors v1
        where v1.pk = __VENDOR_PK__ and
        c1.vendor_pk = v1.pk and
        c1.pk = y1.contract_pk and
        y1.year = __LATEST_YEAR__ and
        c1.month_pk = __MONTH_PK__
        order by c1.contract_value desc
        """

        sql = sql.replace('__VENDOR_PK__', str(pk))

    if context['param_is_agency']:

        pk = int(param[1:])

        sql = """
        select c1.pk,
        c1.contract_id, c1.ariba_id, c1.sap_id,
        c1.vendor_pk, v1.name,
        y1.contract_value, c1.contract_value,
        effective_date, expir_date, commodity_desc
        from contracts c1, contract_years y1, vendors v1,
        budget_unit_joins j1, budget_units b1
        where b1.pk = __AGENCY_PK__ and
        j1.unit_pk = b1.pk and j1.contract_pk = c1.pk and
        c1.vendor_pk = v1.pk and
        c1.pk = y1.contract_pk and
        y1.year = __LATEST_YEAR__ and
        c1.month_pk = __MONTH_PK__
        order by c1.contract_value desc
        """

        sql = sql.replace('__AGENCY_PK__', str(pk))

    if context['param_is_description']:

        sql = """
        select c1.pk,
        c1.contract_id, c1.ariba_id, c1.sap_id,
        c1.vendor_pk, v1.name,
        y1.contract_value, c1.contract_value,
        effective_date, expir_date, commodity_desc
        from contracts c1, contract_years y1, vendors v1
        where c1.commodity_desc = '__DESC__' and
        c1.vendor_pk = v1.pk and
        c1.pk = y1.contract_pk and
        y1.year = __LATEST_YEAR__ and
        c1.month_pk = __MONTH_PK__
        order by c1.contract_value desc
        """

        sql = sql.replace('__DESC__', param[1:])

    if sql is None:
        print("NOT SQL")
        return {}

    sql = sql.replace('__MONTH_PK__', str(month_pk))
    sql = sql.replace('__LATEST_YEAR__', month.split('-')[0])

    rows = conn.execute(sql).fetchall()
    cols = {'pk': 0,
            'cID': 1,
            'aID': 2,
            'sID': 3,
            'vendor_pk': 4,
            'vendor_name': 5,
            'sum_year': 6,
            'sum_all': 7,
            'eff_date': 8,
            'exp_date': 9,
            'description': 10}

    contracts = fill_in_table(rows, cols)
    for contract in contracts:
        contract['sum_year'] = money(contract['sum_year'])
        contract['sum_all'] = money(contract['sum_all'])

        sql = """
        select b1.pk, b1.unit_name
        from contracts c1, budget_unit_joins j1, budget_units b1
        where c1.pk = __CONTRACT_PK__ and
        c1.pk = j1.contract_pk and j1.unit_pk = b1.pk and
        c1.month_pk = __MONTH_PK__
        """

        sql = sql.replace('__CONTRACT_PK__', str(contract['pk']))
        sql = sql.replace('__MONTH_PK__', str(month_pk))

        rows = conn.execute(sql).fetchall()
        agencies = fill_in_table(rows, {'pk': 0, 'name': 1})
        contract['agencies'] = agencies

    if context['param_is_vendor']:
        context['vendor_name'] = contracts[0]['vendor_name']

    if context['param_is_agency']:
        print(f"pk: {param}")
        for agency in contracts[0]['agencies']:
            print(f"agency: {agency}")
            print(f"are they equal? agency[pk]: {agency['pk']} and pk: {pk}")
            if agency['pk'] == pk:
                context['agency_name'] = agency['name']

    context['contracts'] = contracts

    return context


def build_contract():

    try:
        contract_pk = request.path.split('/')[-1]
    except:
        contract_pk = '75169'

    contract_sql = """
    select c1.pk,
    c1.contract_id, c1.ariba_id, c1.sap_id,
    c1.vendor_pk, v1.name,
    y1.contract_value, c1.contract_value,
    effective_date, expir_date, commodity_desc
    from contracts c1, contract_years y1, vendors v1
    where c1.pk = __CONTRACT_PK__ and
    c1.pk = y1.contract_pk and
    y1.year = __LATEST_YEAR__ and
    c1.vendor_pk = v1.pk and
    c1.month_pk = __MONTH_PK__
    """

    contract_agencies_sql = """
    select c1.pk, b1.pk, b1.unit_name
    from contracts c1, budget_unit_joins j1, budget_units b1
    where c1.pk = j1.contract_pk and j1.unit_pk = b1.pk and
    c1.month_pk = __MONTH_PK__
    """

    context = dict()

    [month_pk, month] = latest_month()
    context['current_month'] = month
    context['current_year'] = month.split('-')[0]

    sql = contract_sql
    sql = sql.replace('__MONTH_PK__', str(month_pk))
    sql = sql.replace('__LATEST_YEAR__', month.split('-')[0])
    sql = sql.replace('__CONTRACT_PK__', contract_pk)

    rows = conn.execute(sql).fetchall()
    cols = {'pk': 0,
            'cID': 1,
            'aID': 2,
            'sID': 3,
            'vendor_pk': 4,
            'vendor_name': 5,
            'sum_year': 6,
            'sum_all': 7,
            'eff_date': 8,
            'exp_date': 9,
            'description': 10}

    contracts = fill_in_table(rows, cols)

    if not contracts:
        raise Exception(f"no contract data found for pk: {contract_pk}")

    contracts[0]['sum_year'] = money(contracts[0]['sum_year'])
    contracts[0]['sum_all'] = money(contracts[0]['sum_all'])
    contracts[0]['agencies'] = dict()

    contract = contracts[0]

    sql = contract_agencies_sql
    sql = sql.replace('__MONTH_PK__', str(month_pk))
    rows = conn.execute(sql).fetchall()
    agencies = fill_in_table(rows, {'contract_pk': 0, 'agency_pk': 1, 'agency_name': 2})

    for agency in agencies:
        if contract['pk'] == agency['contract_pk']:
            pk = contract['pk']
            contract['agencies'][pk] = {'pk': pk, 'name': agency['agency_name']}

    contract['agencies'] = list(contract['agencies'].values())

    context['contract'] = contract

    contract_vendor_info_sql = """
    select key_name, value_str from vendor_infos
    where vendor_pk = __VENDOR_PK__
    """

    sql = contract_vendor_info_sql
    sql = sql.replace('__VENDOR_PK__', str(contract['vendor_pk']))

    rows = conn.execute(sql).fetchall()
    vendor_infos = fill_in_table(rows, {'key_name': 0, 'value_str': 1})

    if vendor_infos:
        contract['vendor_infos'] = vendor_infos

    contract_supporting_docs_sql = """
    select url from supporting_docs
    where __CONTRACT_ID_QUAL__ and
    __ARIBA_ID_QUAL__ and
    __SAP_ID_QUAL__
    """

    sql = contract_supporting_docs_sql
    if contract['cID']:
        sql = sql.replace('__CONTRACT_ID_QUAL__', f"contract_id = '{contract['cID']}'")
    else:
        sql = sql.replace('__CONTRACT_ID_QUAL__', f"contract_id is NULL")
    if contract['aID']:
        sql = sql.replace('__ARIBA_ID_QUAL__', f"ariba_id = '{contract['aID']}'")
    else:
        sql = sql.replace('__ARIBA_ID_QUAL__', f"ariba_id is NULL")
    if contract['sID']:
        sql = sql.replace('__SAP_ID_QUAL__', f"sap_id = '{contract['sID']}'")
    else:
        sql = sql.replace('__SAP_ID_QUAL__', f"sap_id is NULL")

    rows = conn.execute(sql).fetchall()
    supporting_docs = fill_in_table(rows, {'url': 0})

    if supporting_docs:
        context['contract']['supporting_docs'] = supporting_docs

    return context
