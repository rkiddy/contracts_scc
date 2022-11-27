
from datetime import datetime as dt

from dotenv import dotenv_values
from flask import request
from sqlalchemy import create_engine, inspect

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

# cost_labels will be: cost_labels[ <min cost> ] -> bucket key
#     eg: cost_labels[100] = B3
cost_labels = dict()
for key in cost_buckets:
    cost_labels[cost_buckets[key][0]] = key


def latest_month():
    sql = 'select pk, month from months where approved is not NULL order by month desc limit 1;'
    row = conn.execute(sql).fetchone()
    return [row['pk'], row['month']]


def latest_year():
    return latest_month()[1].split('-')[0]


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


def year_value_for_contract(contract, latest_yr=latest_year()):

    start = contract['effective_date']
    end = contract['expir_date']

    contract_start = dt.strptime(start, '%Y-%m-%d')
    contract_end = dt.strptime(end, '%Y-%m-%d')
    contract_diff = (contract_end - contract_start).days

    year_start = dt(int(latest_yr), 1, 1)
    year_end = dt(int(latest_yr), 12, 31)

    if year_start < contract_start:
        year_start = contract_start
    if year_end > contract_end:
        year_end = contract_end

    year_diff = (year_end - year_start).days

    fraction = year_diff / contract_diff

    return int(fraction * contract['contract_value'])


def fetch_contracts(month_pk, fetch_key=None, fetch_value=None):

    # also:
    # <a href="/contracts/scc/vendor/{{ contract.vendor_pk }}"
    # <a href="/contracts/scc/agency/{{ agency.pk }}">
    # <a href="/contracts/scc/desc/{{ contract.commodity_desc }}">
    # <a href="/contracts/scc/bucket/{{ bucket }}">

    sql = f"""
        select c1.pk, c1.owner_name, c1.ariba_id, c1.sap_id, c1.contract_id,
            c1.effective_date, c1.expir_date, c1.contract_value,
            c1.commodity_desc, v1.pk, v1.name
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
        'vendor_pk': 9,
        'vendor_name': 10
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

    sql = "select ariba_id, contract_id, sap_id, pk from supporting_docs"
    columns = {
        'ariba_id': 0,
        'contract_id': 1,
        'sap_id': 2,
        'pk': 3
    }
    docs = dict()
    for doc in fill_in_table(conn.execute(sql).fetchall(), columns):
        cid = f"{doc['ariba_id']}-{doc['contract_id']}-{doc['sap_id']}"
        if cid not in docs:
            docs[cid] = 1
        else:
            docs[cid] += 1

    for contract in contracts:

        contract['year_value'] = money(year_value_for_contract(contract))

        contract['contract_value'] = money(contract['contract_value'])

        cid = f"{contract['ariba_id']}-{contract['contract_id']}-{contract['sap_id']}"
        if cid in docs:
            contract['docs'] = docs[cid]

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
    for agency_info in context['contracts'][0]['agencies']:
        if int(agency_info['pk']) == int(unit_pk):
            agency_name = agency_info['name']
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

    context = dict()

    [month_pk, month] = latest_month()
    context['current_month'] = month
    context['current_year'] = month.split('-')[0]

    top_vendors_sql = f"""
    select v1.pk as vendorPk, v1.name as vendor_name,
    sum(c1.contract_value) as total_value
    from contracts c1, vendors v1
    where c1.vendor_pk = v1.pk
    and c1.month_pk = {month_pk}
    group by v1.pk order by total_value desc limit 5
    """

    top_agencies_sql = f"""
    select unit_pk as agency_pk,
        (select unit_name from budget_units where pk = agency_pk) as agency_name,
        (select sum(c1.contract_value)
    from contracts c1, budget_unit_joins j1
    where c1.pk = j1.contract_pk and
        j1.unit_pk = agency_pk and
        c1.month_pk = {month_pk}) as total_value
    from budget_unit_joins group by unit_pk
    order by total_value desc limit 5
    """

    top_descs_sql = f"""
    select commodity_desc as description,
    sum(contract_value) as total_value
    from contracts where month_pk = {month_pk}
    group by commodity_desc order by total_value desc limit 5
    """

    context['top_vendors'] = fill_in_table(
        conn.execute(top_vendors_sql).fetchall(),
        {'pk': 0, 'name': 1, 'amount': 2})

    context['top_agencies'] = fill_in_table(
        conn.execute(top_agencies_sql).fetchall(),
        {'pk': 0, 'name': 1, 'amount': 2})

    context['top_descs'] = fill_in_table(
        conn.execute(top_descs_sql).fetchall(),
        {'name': 0, 'amount': 1})

    costs_tables = list()
    bucket_min = 0
    bucket_max = 1

    for idx in range(len(cost_buckets.keys())):

        costs_sql = f"""
        select c1.pk, c1.contract_value from contracts c1
        where c1.month_pk = {month_pk}
            and c1.contract_value >= {bucket_min * 100}
            and c1.contract_value < {bucket_max * 100}
        """

        rows = conn.execute(costs_sql).fetchall()
        contracts_count = len(rows)
        contracts_sum = sum([r['contract_value'] for r in rows])
        costs_tables.append(
            {
                'bucket': cost_labels[bucket_min],
                'bucket_label': f"{money(bucket_min * 100)} - {money(bucket_max * 100)}",
                'sum': money(contracts_sum),
                'count': int(contracts_count)
            }
        )

        bucket_min = bucket_max
        bucket_max = bucket_max * 10

    context['costs'] = costs_tables

    context['sources'] = dict()
    sql = f"select source_url from sources where month_pk = {month_pk} and source_url like '%%document/Contract%%'"
    context['sources']['contract_rpt'] = conn.execute(sql).fetchone()['source_url']

    sql = f"select source_url from sources where month_pk = {month_pk} and source_url like '%%document/SA%%'"
    context['sources']['sabc_rpt'] = conn.execute(sql).fetchone()['source_url']

    return context


def build_type_data(type_info):

    context = {}

    [month_pk, month] = latest_month()
    context['current_month'] = month
    context['current_year'] = month.split('-')[0]

    if type_info == 'vendors':
        context['thing_label'] = 'Vendors'
        context['thing_type'] = 'vendor'

        sql = f"""
        select c1.vendor_pk,
            (select name from vendors where pk = c1.vendor_pk) as vendor_name,
            sum(c1.contract_value) as value_sum
        from contracts c1
        where c1.month_pk = {month_pk} group by c1.vendor_pk
        """

    if type_info == 'agencies':
        context['thing_label'] = 'Agencies'
        context['thing_type'] = 'agency'

        sql = f"""
        select u1.pk, u1.unit_name,
            (select sum(c1.contract_value)
                from contracts c1, budget_unit_joins j1
                where c1.pk = j1.contract_pk and j1.unit_pk = u1.pk and c1.month_pk = {month_pk}) as total_value
        from budget_units u1
        """

    if type_info == 'descriptions':
        context['thing_label'] = 'Descriptions'
        context['thing_type'] = 'desc'

        sql = f"""
        select c1.commodity_desc, c1.commodity_desc, sum(c1.contract_value)
        from contracts c1
        where c1.month_pk = {month_pk}
        group by c1.commodity_desc
        """

    things = fill_in_table(
        conn.execute(sql).fetchall(),
        {'pk': 0, 'name': 1, 'total_value': 2})

    next_things = list()
    for thing in things:
        if thing['total_value'] is not None:
            thing['total_value'] = money(thing['total_value'])
            next_things.append(thing)

    context['things'] = next_things
    return context


def build_scc_contract():

    contract_pk = request.path.split('/')[-1]

    context = dict()

    [month_pk, month] = latest_month()
    context['current_month'] = month
    context['current_year'] = month.split('-')[0]

    contract_sql = f"""
    select c1.pk, c1.contract_id, c1.ariba_id, c1.sap_id,
        c1.vendor_pk, v1.name, c1.contract_value,
        c1.effective_date, c1.expir_date, c1.commodity_desc
    from contracts c1, vendors v1
    where c1.pk = {contract_pk} and
        c1.vendor_pk = v1.pk and
        c1.month_pk = {month_pk}
    """

    rows = conn.execute(contract_sql).fetchall()
    cols = {
        'pk': 0,
        'cID': 1,
        'aID': 2,
        'sID': 3,
        'vendor_pk': 4,
        'vendor_name': 5,
        'contract_value': 6,
        'effective_date': 7,
        'expir_date': 8,
        'description': 9
    }

    contract = fill_in_table(rows, cols)[0]

    contract['sum_all'] = money(contract['contract_value'])
    contract['sum_year'] = money(year_value_for_contract(contract))
    contract['agencies'] = dict()

    contract_agencies_sql = f"""
    select c1.pk, b1.pk, b1.unit_name
    from contracts c1, budget_unit_joins j1, budget_units b1
    where c1.pk = j1.contract_pk and j1.unit_pk = b1.pk and
    c1.month_pk = {month_pk}
    """

    rows = conn.execute(contract_agencies_sql).fetchall()
    agencies = fill_in_table(rows, {'contract_pk': 0, 'agency_pk': 1, 'agency_name': 2})

    for agency in agencies:
        if contract['pk'] == agency['contract_pk']:
            pk = contract['pk']
            contract['agencies'][pk] = {'pk': pk, 'name': agency['agency_name']}

    contract['agencies'] = list(contract['agencies'].values())

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

    sql = f"""
    select url from supporting_docs
    where ariba_id = '{contract['aID']}' and
        contract_id = '{contract['cID']}' and
        sap_id = '{contract['sID']}'
    """
    sql = sql.replace("= 'None'", 'is NULL')

    docs = list()
    for doc in conn.execute(sql).fetchall():
        docs.append(doc['url'])

    if len(docs) > 0:
        contract['supporting_docs'] = docs

    context['contract'] = contract

    return context
