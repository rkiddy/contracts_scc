
from flask import request
from sqlalchemy import create_engine, inspect

from dotenv import dotenv_values

cfg = dotenv_values(".env")

engine = create_engine(f"mysql+pymysql://ray:{cfg['PWD']}@{cfg['HOST']}/{cfg['DB']}")
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


def results_sorted_by_key(results, sort_label):
    print(f"sort_label: {sort_label}")
    if sort_label is None:
        return results

    sortish = None
    if sort_label[1] == 'v':
        sortish = 'name'
    if sort_label[1] == 'c':
        sortish = 'sum_year'
    if sort_label[1] == 'a':
        sortish = 'unit_name'
    if sort_label == 'd':
        sortish = 'description'
    if sort_label[1] == 'f':
        sortish = 'eff_date'
    if sort_label[1] == 'x':
        sortish = 'exp_date'

    if sortish is None:
        print(f"Cannot find key for label: {sort_label}")
        return results

    next_result_values = dict()

    for result in results:
        print(f"result: {result}")
        key_val = result[sortish]
        if key_val not in next_result_values:
            next_result_values[key_val] = list()
        next_result_values[key_val].append(result)

    next_results = list()

    key_list = sorted(next_result_values.keys())
    if sort_label[2] == 'a':
        key_list.reverse()

    for key in key_list:
        next_results.extend(next_result_values[key])

    return next_results


def fetch_contracts(month_pk, fetch_key=None, fetch_value=None):

    # also:
    # <a href="/contracts/scc/vendor/{{ contract.vendor_pk }}"
    # <a href="/contracts/scc/agency/{{ agency.pk }}">
    # <a href="/contracts/scc/desc/{{ contract.commodity_desc }}">
    # <a href="/contracts/scc/bucket/{{ bucket }}">

    sql = f"""
        select c1.pk, c1.owner_name, c1.ariba_id, c1.sap_id, c1.contract_id,
            c1.effective_date, c1.expir_date, c1.contract_value,
            c1.commodity_desc, c1.uniq_pk, v1.pk, v1.name
        from contracts c1, budget_unit_joins j1, budget_units u1, vendors v1, months m1
        where c1.pk = j1.contract_pk
            and j1.unit_pk = u1.pk
            and c1.vendor_pk = v1.pk
            and c1.month_pk = m1.pk
            and m1.pk = '{month_pk}'
    """

    if fetch_key == 'vendor_pk':
        sql = f"{sql} and v1.pk = {fetch_value}"
    if fetch_key == 'unit_pk':
        sql = f"{sql} and u1.pk = {fetch_value}"
    if fetch_key == 'description':
        sql = f"{sql} and c1.commodity_desc = '{fetch_value}'"
    if fetch_key == 'bucket':
        sql = f"""
            {sql} and
            c1.contract_value >= {cost_buckets[fetch_value][0] * 100} and
            c1.contract_value < {cost_buckets[fetch_value][1] * 100}
        """
        pass

    columns = {
        'contract_pk': 0,
        'owner_name': 1,
        'ariba_id': 2,
        'sap_id': 3,
        'contract_id': 4,
        'effective_date': 5,
        'expir_date': 6,
        'contract_value': 7,
        'commodity_desc': 8,
        'uniq_pk': 9,
        'vendor_pk': 10,
        'vendor_name': 11
    }
    contracts = fill_in_table(conn.execute(sql).fetchall(), columns)
    contracts_by_pk = dict()
    for contract in contracts:
        contracts_by_pk[contract['contract_pk']] = contract

    sql = f"""
    select j1.contract_pk, u1.pk, u1.unit_name, u1.unit_num
    from budget_unit_joins j1, budget_units u1
    where j1.contract_pk in ({','.join([ str(ckey) for ckey in contracts_by_pk.keys()])}) and j1.unit_pk = u1.pk
    """

    columns = {
        'contract_pk': 0,
        'unit_pk': 1,
        'unit_name': 2,
        'unit_num': 3
    }
    unit_links = fill_in_table(conn.execute(sql).fetchall(), columns)

    for unit_link in unit_links:
        cpk = unit_link['contract_pk']
        if 'agencies' not in contracts_by_pk[cpk]:
            contracts_by_pk[cpk]['agencies'] = list()
        contracts_by_pk[cpk]['agencies'].append(
            {
                'name': unit_link['unit_name'],
                'num': unit_link['unit_num'],
                'pk': unit_link['unit_pk']
            }
        )

    contracts = list(contracts_by_pk.values())

    sql = "select contract_uniq_pk, count(0) from supporting_docs group by contract_uniq_pk"
    columns = {
        'uniq_pk': 0,
        'count': 1
    }
    uniqs = dict()
    for uniq in fill_in_table(conn.execute(sql).fetchall(), columns):
        uniqs[uniq['uniq_pk']] = uniq['count']

    for contract in contracts:
        contract['contract_value'] = money(contract['contract_value'])
        if contract['uniq_pk'] in uniqs:
            contract['docs'] = uniq['count']
        else:
            contract['docs'] = None

    return contracts


def all_contracts():

    context = {}

    [month_pk, month] = latest_month()
    context['current_month'] = month
    context['current_year'] = month.split('-')[0]

    context['contracts'] = fetch_contracts(month_pk)

    return context


def contracts_for_key_value(key, value):

    context = {}

    [month_pk, month] = latest_month()
    context['current_month'] = month
    context['current_year'] = month.split('-')[0]

    context['contracts'] = fetch_contracts(month_pk, key, value)

    return context


def vendor_contracts(vendor_pk):
    context = contracts_for_key_value('vendor_pk', vendor_pk)
    context['fetch_key'] = 'vendor_pk'
    context['fetch_value'] = context['contracts'][0]['vendor_name']
    return context


def agency_contracts(unit_pk):
    context = contracts_for_key_value('unit_pk', unit_pk)
    context['fetch_key'] = 'unit_pk'
    agency_name = None
    for agency in context['contracts'][0]['agencies']:
        if int(agency['pk']) == int(unit_pk):
            agency_name = agency['name']
    context['fetch_value'] = agency_name
    return context


def description_contracts(description):
    context = contracts_for_key_value('description', description)
    context['fetch_key'] = 'description'
    context['fetch_value'] = context['contracts'][0]['commodity_desc']
    return context


def bucket_contracts(bucket):
    context = contracts_for_key_value('bucket', bucket)
    context['fetch_key'] = 'bucket'
    context['fetch_value'] = f"[ {money(cost_buckets[bucket][0] * 100)} - {money(cost_buckets[bucket][1] * 100)} )"
    return context


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

    sql = f"select source_url from sources where month_pk = {month_pk} and source_url like '%%document/SA%%'"
    context['sources']['sabc_rpt'] = conn.execute(sql).fetchone()['source_url']

    return context


def collapse_found_contracts(contracts):

    ids = dict()

    for contract in contracts:
        key = f"{contract['cID']}_{contract['aID']}_{contract['sID']}"
        if key not in ids:
            ids[key] = dict()
            ids[key]['contracts'] = list()
            ids[key]['contracts'].append(contract)
            ids[key]['least'] = contract['month']
            ids[key]['most'] = contract['month']
        else:
            ids[key]['contracts'].append(contract)
            if contract['month'] < ids[key]['least']:
                ids[key]['least'] = contract['month']
            if contract['month'] > ids[key]['most']:
                ids[key]['most'] = contract['month']

    next_contracts = list()
    for key in ids:
        next_contracts.append(ids[key]['contracts'][0])
        if ids[key]['least'] != ids[key]['most']:
            next_contracts[-1]['least'] = ids[key]['least']
            next_contracts[-1]['most'] = ids[key]['most']
        else:
            next_contracts[-1]['only'] = ids[key]['least']
        next_contracts[-1].pop('month')

    return next_contracts


contracts_list_columns = {
    'pk': 0,
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

contracts_search_columns = {
    'pk': 0,
    'cID': 1,
    'aID': 2,
    'sID': 3,
    'vendor_pk': 4,
    'vendor_name': 5,
    'sum_all': 6,
    'month': 7,
    'eff_date': 8,
    'exp_date': 9,
    'description': 10}


def format_money(contracts):
    for contract in contracts:
        if 'sum_year' in contract:
            contract['sum_year'] = money(contract['sum_year'])
        if 'sum_all' in contract:
            contract['sum_all'] = money(contract['sum_all'])
    return contracts


def build_scc_search(sort=None):

    print(f"in build_scc_search, sort = {sort}")

    context = dict()

    context['param'] = ''

    [month_pk, month] = latest_month()
    context['current_month'] = month
    context['current_year'] = month.split('-')[0]

    search_type = request.form['search-type']
    search_term = request.form['search-term']

    sql = """
     select c1.pk,
     c1.contract_id, c1.ariba_id, c1.sap_id,
     c1.vendor_pk, v1.name,
     c1.contract_value, m1.month,
     c1.effective_date, c1.expir_date, c1.commodity_desc
     from contracts c1, vendors v1, months m1
     where c1.month_pk = m1.pk and
     __QUAL__
     c1.vendor_pk = v1.pk
     order by c1.contract_value desc
     """

    if search_type == 'contractID' and search_term != '':
        sql = sql.replace(
            '__QUAL__',
            f"(c1.contract_id = '{search_term}' or "
            f"c1.ariba_id = '{search_term}' or "
            f"c1.sap_id = '{search_term}') and")

    if search_type == 'vendorName' and search_term != '':
        sql = sql.replace(
            '__QUAL__',
            f"v1.name like '%%{search_term}%%' and")

    if search_type == 'descript' and search_term != '':
        sql = sql.replace(
            '__QUAL__',
            f"lower(c1.commodity_desc) like lower('%%{search_term.upper()}%%') and")

    # print(f"sql: {sql}")

    rows = conn.execute(sql).fetchall()

    contracts = fill_in_table(rows, contracts_search_columns)

    # I searched without specifying month_pk.
    # Now I have to sort out start, end of unique contracts.
    #
    contracts = collapse_found_contracts(contracts)

    contracts = format_money(contracts)

    context['contracts'] = results_sorted_by_key(contracts, sort)

    return context


def build_scc_documents():

    context = dict()

    [month_pk, month] = latest_month()
    context['current_month'] = month
    context['current_year'] = month.split('-')[0]

    sql = """
     select c1.pk,
     c1.contract_id, c1.ariba_id, c1.sap_id,
     c1.vendor_pk, v1.name,
     c1.contract_value, m1.month,
     c1.effective_date, c1.expir_date, c1.commodity_desc
     from contracts c1, vendors v1, months m1
     where c1.vendor_pk = v1.pk and
     c1.uniq_pk in (select contract_uniq_pk from supporting_docs)
     order by c1.contract_value desc
     """

    # print(f"sql: {sql}")

    rows = conn.execute(sql).fetchall()

    contracts = fill_in_table(rows, contracts_search_columns)

    # I searched without specifying month_pk.
    # Now I have to sort out start, end of unique contracts.
    #
    contracts = collapse_found_contracts(contracts)

    context['contracts'] = format_money(contracts)

    return context


def build_scc_contract():

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

    contract_allmonths_sql = """
    select c1.pk,
    c1.contract_id, c1.ariba_id, c1.sap_id,
    c1.vendor_pk, v1.name, c1.contract_value,
    effective_date, expir_date, commodity_desc
    from contracts c1, vendors v1
    where c1.pk = __CONTRACT_PK__ and
    c1.vendor_pk = v1.pk
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
        sql = contract_allmonths_sql

        sql = sql.replace('__CONTRACT_PK__', contract_pk)

        rows = conn.execute(sql).fetchall()
        cols = {'pk': 0,
                'cID': 1,
                'aID': 2,
                'sID': 3,
                'vendor_pk': 4,
                'vendor_name': 5,
                'sum_all': 6,
                'eff_date': 7,
                'exp_date': 8,
                'description': 9}

        contracts = fill_in_table(rows, cols)

    if not contracts:
        raise Exception(f"no contract data found for pk: {contract_pk}")

    contracts[0]['sum_all'] = money(contracts[0]['sum_all'])
    if 'sum_year' in contracts[0]:
        contracts[0]['sum_year'] = money(contracts[0]['sum_year'])
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
    where contract_uniq_pk in
    (select uniq_pk from contracts where
        __CONTRACT_ID_QUAL__ and
        __ARIBA_ID_QUAL__ and
        __SAP_ID_QUAL__)
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
