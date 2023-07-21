
from datetime import datetime as dt

from dotenv import dotenv_values
from flask import request
from sqlalchemy import create_engine, inspect

cfg = dotenv_values(".env")

con_engine = create_engine(f"mysql+pymysql://{cfg['USR']}:{cfg['PWD']}@{cfg['HOST']}/{cfg['DB']}")
conn = con_engine.connect()
inspector = inspect(con_engine)

cost_buckets = {
    'B0': [0, 1],
    'B1': [1, 10],
    'B2': [10, 100],
    'B3': [100, 1000],
    'B4': [1000, 10000],
    'B5': [10000, 100000],
    'B6': [100000, 1000000],
    'B7': [1000000, 10000000],
    'B8': [10000000, 100000000],
    'B9': [100000000, 10000000000]
}


def db_exec(engine, sql):
    # print(f"sql: {sql}")
    if sql.strip().startswith('select'):
        return [dict(r) for r in engine.execute(sql).fetchall()]
    else:
        return engine.execute(sql)


# cost_labels will be: cost_labels[ <min cost> ] -> bucket key
#     eg: cost_labels[100] = B3
def cost_labels(num):
    for key in cost_buckets:
        if cost_buckets[key][0] == num:
            return key
    raise Exception("Could not find number to identif key")


def latest_month():
    sql = 'select pk, month from months where approved is not NULL order by month desc limit 1;'
    row = conn.execute(sql).fetchone()
    return [row['pk'], row['month']]


def latest_year():
    return latest_month()[1].split('-')[0]


def money(cents):
    if cents is None:
        return '$0.00'
    else:
        cents = int(cents) / 100
        cents = str(cents)
        return "${:,.2f}".format(float(cents))


# TODO Get rid of this.
# rows is a result cursor, columns is a dictionary or key -> column number in rows.
def fill_in_table(rows, columns):
    """
    :param rows: data, probably from a database fetch.
    :param columns: names to use in result dictionaries.
    :return: for each row given, a dictionary with the keys as desired.
    """
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
    """
    :param contract: has an 'effective_date' and 'expir_date' (both
        str like '%Y-%m-%d') and a 'contract_value' (int).
    :param latest_yr: defaults to current year (str)
    :return: the fraction of the contract_value represented by the
        current year within the interval of the contract (int).
    """
    c_start = dt.strptime(contract['effective_date'], '%Y-%m-%d')
    c_end = dt.strptime(contract['expir_date'], '%Y-%m-%d')
    c_diff = (c_end - c_start).days + 1

    year_start = dt(int(latest_yr), 1, 1)
    year_end = dt(int(latest_yr), 12, 31)

    if year_end < c_start or year_start > c_end:
        return 0

    if year_start < c_start:
        year_start = c_start
    if year_end > c_end:
        year_end = c_end

    year_diff = (year_end - year_start).days + 1

    fraction = year_diff / c_diff

    return int(fraction * contract['contract_value'])


def fetch_contracts(month_pk, fetch_key=None, fetch_value=None):

    # from:
    # <a href="/contracts/scc/
    # <a href="/contracts/scc/vendor/{{ contract.vendor_pk }}"
    # <a href="/contracts/scc/agency/{{ agency.pk }}">
    # <a href="/contracts/scc/desc/{{ contract.commodity_desc }}">
    # <a href="/contracts/scc/bucket/{{ bucket }}">

    # Fetch the main contracts list.
    #
    sql = f"""
        select c1.pk as contract_pk, c1.owner_name,
            c1.ariba_id, c1.contract_id, c1.sap_id,
            c1.effective_date, c1.expir_date, c1.contract_value,
            c1.commodity_desc, v1.pk as vendor_pk, v1.name as vendor_name
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

    contracts = db_exec(con_engine, sql)
    contracts_by_pk = dict()
    contracts_ids = dict()
    for contract in contracts:

        c_pk = contract['contract_pk']

        contract['year_value'] = money(year_value_for_contract(contract))
        contract['contract_value'] = money(contract['contract_value'])

        # for the contract value changes data
        ids = f"{contract['ariba_id']}-{contract['contract_id']}-{contract['sap_id']}".replace('None', '')
        contracts_ids[ids] = {'pk': c_pk}

        # for the main contracts list.
        contracts_by_pk[c_pk] = contract

    # Fetch the budget unit info to associate with contracts.
    #
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
        contracts_by_pk[cpk]['agencies_len'] = len(contracts_by_pk[cpk]['agencies'])

    # Fetch the contract value change information.
    #
    sql = """
        select concat(coalesce(ariba_id, ''), '-', coalesce(contract_id, ''), '-', coalesce(sap_id, '')) as full,
            contract_value, month_pk
        from contracts order by month_pk
    """
    for row in db_exec(conn, sql):
        if row['full'] in contracts_ids:
            if 'values' not in contracts_ids[row['full']]:
                contracts_ids[row['full']]['values'] = list()
            contracts_ids[row['full']]['values'].append(row['contract_value'])

    for ids in contracts_ids:

        c_pk = contracts_ids[ids]['pk']

        contracts_by_pk[c_pk]['v_start'] = money(contracts_ids[ids]['values'][0])
        contracts_by_pk[c_pk]['v_end'] = money(contracts_ids[ids]['values'][-1])

        next_values = list()
        next_values.append(contracts_ids[ids]['values'][0])
        for v in contracts_ids[ids]['values'][1:]:
            if v != next_values[-1]:
                next_values.append(v)
        contracts_by_pk[c_pk]['values'] = [money(r) for r in next_values]
        contracts_by_pk[c_pk]['v_len'] = len(next_values)

    # Attach the contracts to send on.
    #
    contracts = list(contracts_by_pk.values())

    sql = "select ariba_id, contract_id, sap_id from supporting_docs"
    columns = {
        'ariba_id': 0,
        'contract_id': 1,
        'sap_id': 2
    }
    docs = dict()
    for doc in fill_in_table(conn.execute(sql).fetchall(), columns):
        cid = f"{doc['ariba_id']}-{doc['contract_id']}-{doc['sap_id']}"
        if cid not in docs:
            docs[cid] = 1
        else:
            docs[cid] += 1

    for contract in contracts:

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
        if int(dict(agency_info)['pk']) == int(unit_pk):
            agency_name = dict(agency_info)['name']
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

    context['top_vendors'] = fill_in_table(
        conn.execute(top_vendors_sql).fetchall(),
        {'pk': 0, 'name': 1, 'amount': 2})

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

    context['top_agencies'] = fill_in_table(
        conn.execute(top_agencies_sql).fetchall(),
        {'pk': 0, 'name': 1, 'amount': 2})

    top_descs_sql = f"""
    select commodity_desc as description,
    sum(contract_value) as total_value
    from contracts where month_pk = {month_pk}
    group by commodity_desc order by total_value desc limit 5
    """

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
                'bucket': cost_labels(bucket_min),
                'bucket_label': f"{money(bucket_min * 100)} - {money(bucket_max * 100)}",
                'sum': money(contracts_sum),
                'count': int(contracts_count)
            }
        )

        bucket_min = bucket_max
        bucket_max = bucket_max * 10

    context['costs'] = costs_tables

    sql = f"""
    select count(0) as count, sum(contract_value) as sum_costs
    from contracts where month_pk = {month_pk}
    """

    row = conn.execute(sql).fetchone()
    context['all_count'] = int(row['count'])
    context['all_sum'] = money(row['sum_costs'])

    context['sources'] = dict()
    sql = f"select source_url from sources where month_pk = {month_pk} and source_url like '%%/Contract%%'"
    context['sources']['contract_rpt'] = conn.execute(sql).fetchone()['source_url']

    sql = f"select source_url from sources where month_pk = {month_pk} and source_url like '%%/SA%%'"
    context['sources']['sabc_rpt'] = conn.execute(sql).fetchone()['source_url']

    return context


def build_type_data(type_info):

    context = {}

    [month_pk, month] = latest_month()
    context['current_month'] = month
    context['current_year'] = month.split('-')[0]

    sql = None

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

    parts = request.path.split('/')[-1].split('-')

    context = dict()

    context['qual'] = f"{parts[0]}-{parts[1]}-{parts[2]}"

    [month_pk, month] = latest_month()
    context['current_month'] = month
    context['current_year'] = month.split('-')[0]

    if len(parts) == 4:
        display_all = True
    else:
        display_all = False

    if parts[0] == 'None':
        ariba_id_str = "is NULL"
    else:
        ariba_id_str = f"= '{parts[0]}'"

    if parts[1] == 'None':
        contract_id_str = "is NULL"
    else:
        contract_id_str = f"= '{parts[1]}'"

    if parts[2] == 'None':
        sap_id_str = "is NULL"
    else:
        sap_id_str = f"= '{parts[2]}'"

    contracts = list()

    sql = f"""
        select c1.pk, c1.ariba_id, c1.contract_id, c1.sap_id,
            c1.vendor_name, c1.vendor_pk,
            c1.effective_date, c1.expir_date,
            c1.contract_value, c1.commodity_desc, m1.month
        from contracts c1, months m1
        where c1.ariba_id {ariba_id_str} and
            c1.contract_id {contract_id_str} and
            c1.sap_id {sap_id_str}
    """
    if not display_all:
        sql = f"{sql} and c1.month_pk = {month_pk} and c1.month_pk = m1.pk"
    else:
        sql = f"{sql} and c1.month_pk = m1.pk"

    sql = f"{sql} order by month desc"

    rows = db_exec(conn, sql)

    vpk = rows[0]['vendor_pk']

    # mark the contract as to type.
    #
    if rows[0]['contract_id'] is None:
        con_type = "SABC"
    else:
        con_type = "CON"
    context['con_type'] = con_type

    for row in rows:
        next_row = dict(row)
        next_row['contract_pk'] = row['pk']
        next_row['contract_value'] = money(row['contract_value'])
        next_row['aID'] = row['ariba_id']
        next_row['cID'] = row['contract_id']
        next_row['sID'] = row['sap_id']
        contracts.append(next_row)

    pks = list(set([str(r['contract_pk']) for r in contracts]))

    units = dict()
    # set up units dictionary to use contract pk as key, pointing to name and unit pk.
    sql = f"""
        select * from budget_unit_joins j1, budget_units b1
        where j1.unit_pk = b1.pk and
            j1.contract_pk in ({','.join(pks)})
    """
    for row in db_exec(conn, sql):
        pk = row['contract_pk']
        if pk not in units:
            units[pk] = list()
        units[pk].append(row)

    for contract in contracts:
        contract['units'] = units[contract['contract_pk']]

    sql = f"""
        select url
        from supporting_docs
        where ariba_id {ariba_id_str} and
            contract_id {contract_id_str} and
            sap_id {sap_id_str}
    """
    rows = db_exec(conn, sql)
    if rows is not None or len(rows) > 0:
        context['docs'] = rows

    context['contracts'] = contracts

    context['vendor_infos'] = db_exec(conn, f"select * from vendor_infos where vendor_pk = {vpk}")

    return context


def collapse_values(lines: list) -> list:
    rs = list()
    cols = ['start', 'stop', 'efd', 'exd', 'value', 'vendor']
    for line in lines:
        # print(f"line: {line}")
        parts = line.split(' ')
        month = parts[0]
        value = parts[-1]
        efd = parts[-3]
        exd = parts[-2]
        vendor = ' '.join(parts[1:-3])
        if len(rs) == 0:
            rs.append(dict(zip(cols, [month, month, efd, exd, value, vendor])))
        else:
            if value != rs[-1]['value']:
                rs.append(dict(zip(cols, [month, month, efd, exd, value, vendor])))
            else:
                if month < rs[-1]['start']:
                    rs[-1]['start'] = month
                if month > rs[-1]['stop']:
                    rs[-1]['stop'] = month

    next_result = list()
    for r in rs:
        key = f"{r['start']} to {r['stop']} - {r['vendor']} - {r['efd']} - {r['exd']} - {money(r['value'])}"
        next_result.append(key)

    return next_result


ctypes = {
    'a': 'ariba', 's': 'sap', 'c': 'contract'
}


def price_mods():
    context = dict()

    sql = "select * from contract_ids"
    rows = db_exec(con_engine, sql)

    contract_pks = dict()
    ids = dict()

    for row in rows:
        cpk = row['contract_pk']
        if cpk not in contract_pks:
            contract_pks[cpk] = list()
        contract_pks[cpk].append(f"{ctypes[row['id_type']]}: {row['id_value']}")

    # now I have the id sets for each contract pk.

    for cpk in contract_pks:
        contract_pks[cpk] = sorted(contract_pks[cpk])
        id_set = ' - '.join(contract_pks[cpk])
        if id_set not in ids:
            ids[id_set] = list()
        ids[id_set].append(cpk)

    # now I have the id sets, and which contract pks are attached to them.

    contracts = dict()

    for id_set in ids:
        contract_infos = list()
        contract_values = list()
        for pk in ids[id_set]:
            sql = f"""
                select c1.vendor_name as vn, c1.effective_date as efd, c1.expir_date as exd, c1.contract_value as cv, m1.month as m
                from contracts c1, months m1
                where c1.pk = {pk} and c1.month_pk = m1.pk order by c1.pk
            """
            contract = db_exec(con_engine, sql)[0]
            contract_infos.append(f"{contract['m']} {contract['vn']} {contract['efd']} {contract['exd']} {contract['cv']}")
            contract_values.append(contract['cv'])

        track_contract = False

        if len(set(contract_values)) > 1:
            track_contract = True

        if len(set(contract_values)) == 2:
            if contract_values[0] <= 100:
                track_contract = False

        if track_contract:

            next_infos = collapse_values(contract_infos)
            hi_value = contract_values[-1]
            lo_value = contract_values[0]
            if lo_value <= 100:
                lo_value = contract_values[1]

            diff = hi_value - lo_value
            pct = int((hi_value / lo_value) * 100) - 100

            contracts[id_set] = dict()
            contracts[id_set]['values'] = next_infos
            contracts[id_set]['start'] = next_infos[0][:7]
            contracts[id_set]['end'] = next_infos[-1][11:18]
            contracts[id_set]['diff'] = money(diff)
            contracts[id_set]['pct'] = pct

    context['contracts'] = contracts

    return context


def url_label(url):
    return url.split('/')[-1]


def build_supporting_docs():
    context = dict()

    sql = "select ariba_id, contract_id, sap_id, url from supporting_docs"
    rows = db_exec(conn, sql)

    urls = dict()
    for row in rows:
        key = f"{row['ariba_id']}|{row['contract_id']}|{row['sap_id']}"
        if key not in urls:
            urls[key] = list()
        urls[key].append(row['url'])

    found = dict()

    for key in urls:
        parts = key.split('|')

        if parts[0] == 'None':
            ariba_id_str = "is NULL"
        else:
            ariba_id_str = f"= '{parts[0]}'"

        if parts[1] == 'None':
            contract_id_str = "is NULL"
        else:
            contract_id_str = f"= '{parts[1]}'"

        if parts[2] == 'None':
            sap_id_str = "is NULL"
        else:
            sap_id_str = f"= '{parts[2]}'"

        qualifier = f"c1.ariba_id {ariba_id_str} and c1.contract_id {contract_id_str} and c1.sap_id {sap_id_str}"

        sql = f"""
            select c1.pk as c_pk, c1.ariba_id, c1.sap_id, c1.contract_id,
                c1.contract_type, c1.vendor_name, c1.vendor_pk,
                c1.effective_date, c1.expir_date, c1.contract_value, c1.commodity_desc, m1.month
            from contracts c1, months m1
            where c1.month_pk = m1.pk and {qualifier} order by m1.month
            """
        contracts = db_exec(conn, sql)

        found[key] = dict(contracts[-1])
        found[key]['contract_value'] = money(found[key]['contract_value'])
        found[key]['min_month'] = contracts[0]['month']
        found[key]['max_month'] = contracts[-1]['month']

        found[key]['urls'] = list()

        for url in urls[key]:
            found[key]['urls'].append({'url': url, 'label': url_label(url)})

        con_pks = ', '.join(list(set([str(r['c_pk']) for r in contracts])))

        unit_pks = dict()
        sql = f"""
            select * from budget_unit_joins j1, budget_units u1
            where j1.contract_pk in ({con_pks})
        """
        for row in db_exec(conn, sql):
            # print(f"row: {row}")
            unit_pks[row['unit_num']] = row['unit_name']

        found[key]['agencies'] = list()

        for pk in unit_pks:
            found[key]['agencies'].append({'pk': pk, 'name': unit_pks[pk]})

    context['contracts'] = list(found.values())

    return context
