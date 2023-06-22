import re

from dotenv import dotenv_values
from sqlalchemy import create_engine

cfg = dotenv_values(".env")

con_engine = create_engine(f"mysql+pymysql://{cfg['USR']}:{cfg['PWD']}@{cfg['HOST']}/{cfg['DB']}")
conn = con_engine.connect()


def db_exec(engine, sql):
    # print(f"sql: {sql}")
    if sql.strip().startswith('select'):
        return [dict(r) for r in engine.execute(sql).fetchall()]
    else:
        return engine.execute(sql)


def shorten_url(url):
    if url is None or url == '':
        return ''
    parts = url.split('/')
    if len(parts) < 2 or not parts[-1].endswith('.pdf'):
        return ''
    return f"{parts[2]}/.../{parts[-1]}"


def imports_main():
    context = dict()

    sql = """
    select m1.month, m1.approved, s1.source_url, s1.alternate_url
    from months m1 left outer join sources s1
    on m1.pk = s1.month_pk
    """
    rows = db_exec(conn, sql)

    months = dict()
    for row in rows:
        if row['month'] not in months:
            months[row['month']] = dict()

        if '/Contracts' in row['source_url']:
            key = 'Contracts'
        else:
            key = 'SABC'

        months[row['month']][key] = dict()
        months[row['month']][key]['url'] = row['source_url']
        months[row['month']][key]['url_s'] = shorten_url(row['source_url'])
        months[row['month']][key]['alt'] = row['alternate_url']
        months[row['month']][key]['alt_s'] = shorten_url(row['alternate_url'])
        months[row['month']][key]['approved'] = row['approved']

    context['months_data'] = months
    context['months'] = sorted(list(months.keys()))
    context['months'].reverse()
    return context


def line_is_header(line):

    if line.startswith('Document Type'):
        return True
    if 'Effective Date' in line:
        return True
    if 'Commodity Description' in line:
        return True
    if line.startswith('Owner Name'):
        return True

    return False


def fix_unit_name(name):
    """
    When read in from file, the unit name might have a double-quote at start or end.
    """
    return name.replace('"', '')


def fix_money(amount):
    amount = amount.strip()
    if not amount.startswith('$'):
        raise Exception("Money amount should start with dollar sign.")
    amount = amount.replace('$', '')
    if re.match(r'\.\d\d$', amount):
        raise Exception("Money amount should end with a dot and cents.")
    amount = amount.replace(' ', '').replace(',', '').replace('.', '')
    return amount


def sabc_data(parts):
    row = dict()
    row['owner_name'] = ''
    row['doc_type'] = parts[0]
    row['units'] = [fix_unit_name(f"{parts[2]} - {parts[1]}")]
    row['ariba_id'] = ''
    row['sap_id'] = ''
    row['con_id'] = parts[3]
    row['v_name'] = parts[4]
    row['eff_date'] = fix_date(parts[5])
    row['exp_date'] = fix_date(parts[6])
    row['con_value_orig'] = parts[7]
    row['con_value'] = fix_money(parts[7])
    row['descrip'] = parts[8].strip()
    return row


def contract_data(parts):
    row = dict()
    row['doc_type'] = 'CON'
    row['owner_name'] = parts[0]
    row['ariba_id'] = parts[1]
    row['con_id'] = ''
    row['sap_id'] = parts[2]
    row['v_name'] = parts[3]
    row['eff_date'] = fix_date(parts[4])
    row['exp_date'] = fix_date(parts[5])
    row['con_value_orig'] = parts[6]
    row['con_value'] = fix_money(parts[6])
    row['units'] = [fix_unit_name(parts[7]).strip()]
    if len(parts) > 8:
        row['descrip'] = parts[8].strip()
    return row


def fix_bad_lines(lines):
    """
    When reading from Contracts file, a list of units will create false lines.
    The false lines come in a sequence: one line of 8 parts (ending with the first
    unit name), zero or more lines of one part (it being a unit name), and a line of
    two parts (the last unit name and the description).
    TODO error-checking
    """

    fixed_rows = list()

    for parts in lines:

        if len(parts) == 8:
            row = contract_data(parts)
            fixed_rows.append(row)

        if len(parts) == 1:
            fixed_rows[-1]['units'].append(parts[0].strip())

        if len(parts) == 2:
            fixed_rows[-1]['units'].append(parts[0])
            fixed_rows[-1]['descrip'] = parts[1].strip()

    return fixed_rows


def fix_date(date_str):
    parts = date_str.split('/')
    if len(parts) != 3:
        raise Exception(f"Date string not proper format: '{date_str}'")
    year = str(parts[2])
    month = str(parts[0])
    day_of_month = str(parts[1])
    # TODO Why do I have to replace the space here? I do not think I need to.
    fixed_date = f"{year}-{month.zfill(2)}-{day_of_month.zfill(2)}".replace(' ', '')
    return fixed_date


def sql_safe(word):
    """
    Make sure that string values can safely be used in a sql statement.
    """
    next_word = word.replace("'", "''")
    final_word = f"'{next_word}'"
    return final_word


def vendor_pk_for_name(name):

    rows = db_exec(conn, f"select * from vendors where name = {sql_safe(name)}")

    if len(rows) > 1:
        print(f"WARNING: There is more than one pk for vendor named '{name}'")

    if len(rows) > 0:
        return rows[0]['pk']

    pk = fetch_max_pk('vendors') + 1
    sql = f"insert into vendors values ({pk}, {sql_safe(name)})"
    db_exec(conn, sql)

    return pk


unit_names = dict()


def fetch_units():
    """
    Fills the unit_names glabal, which points the unit_names to the pk values.
    """
    rows = db_exec(conn, "select * from budget_units")
    for row in rows:
        if 'unit_num' not in row or row['unit_num'] == '':
            unit_name = row['unit_name']
        else:
            unit_name = f"{row['unit_name']} - {row['unit_num']}"
        unit_names[unit_name] = row['pk']

    rows = db_exec(conn, "select * from budget_unit_names")
    for row in rows:
        unit_names[row['name']] = row['unit_pk']


def unit_pks_for_names(names):
    pks = list()
    for name in names:
        # TODO WHY do I have to do this here? I should not!
        name = fix_unit_name(name)
        if name not in unit_names:
            raise Exception(f"Cannot find unit with name: '{name}'")
        pks.append(unit_names[name])
    return pks


def fetch_max_pk(table):
    sql = f"select max(pk) as pk from {table}"
    return db_exec(conn, sql)[0]['pk']


def fetch_source_pks(month_pk):
    pks = dict()
    sql = f"select pk, source_url from sources where month_pk = {month_pk}"
    for row in db_exec(conn, sql):
        url = row['source_url']
        if '/Contracts' in url:
            pks['CON'] = row['pk']
        if '/SA' in url:
            pks['SA'] = row['pk']
            pks['BC'] = row['pk']
    return pks


def import_scan():
    context = dict()

    rows = list()

    # in SA BC file:
    #     0: Document Type
    #     1: Budget Unit
    #     2: Budget Unit Name
    #     3: "Contract ID (PO ID)"
    #     4: Vendor Name
    #     5: Effective Date
    #     6: Expiration Date
    #     7: "Contract Value (PO Value)"
    #     8: Commodity Description
    #
    file = "/tmp/import/SA BC Report for Month of April 2023.tsv"
    with open(file, 'r') as sabc_file:

        for line in sabc_file:

            if not line_is_header(line):

                parts = line.strip('\r').split('\t')
                row = sabc_data(parts)
                rows.append(row)

    # in Contracts file:
    #     0: Owner Name
    #     1: Contract ID Ariba
    #     2: Contract ID SAP
    #     3: Vendor Name
    #     4: Effective Date
    #     5: Expiration Date
    #     6: Contract Value
    #     7: Authorized Users
    #     8: Commodity Description
    #
    bad_lines = list()
    file = "/tmp/import/Contracts Report for Month of April 2023.tsv"
    with open(file, 'r') as contracts_file:

        for line in contracts_file:

            if not line_is_header(line):

                parts = line.strip('\r').split('\t')

                if len(parts) != 9:
                    bad_lines.append(parts)
                else:
                    for row in fix_bad_lines(bad_lines):
                        rows.append(row)
                        bad_lines = list()

                    row = contract_data(parts)
                    rows.append(row)

    print(f"rows #: {len(rows)}")
    context['rows'] = rows
    return context


def add_to_sql(cols, values, col, value):
    """Assumes string, adds to cols and values."""
    if value != '':
        cols.append(col)
        values.append(sql_safe(value))


def import_save():
    context = import_scan()

    max_con_pk = fetch_max_pk('contracts')
    max_cid_pk = fetch_max_pk('contract_ids')

    source_pks = fetch_source_pks(41)

    fetch_units()

    con_pk = max_con_pk + 1
    cid_pk = max_cid_pk + 1

    inserts = list()

    rows = context['rows']

    for row in rows:

        row['v_pk'] = vendor_pk_for_name(row['v_name'])

        row['unit_pks'] = unit_pks_for_names(row['units'])

        if row['con_id'] != '':
            sql = f"({cid_pk}, {con_pk}, 'c', '{row['con_id']}')"
            inserts.append(f"insert into contract_ids values {sql}")
            cid_pk += 1

        if row['ariba_id'] != '':
            sql = f"({cid_pk}, {con_pk}, 'a', '{row['ariba_id']}')"
            inserts.append(f"insert into contract_ids values {sql}")
            cid_pk += 1

        if row['sap_id'] != '':
            sql = f"({cid_pk}, {con_pk}, 's', '{row['sap_id']}')"
            inserts.append(f"insert into contract_ids values {sql}")
            cid_pk += 1

        for unit_pk in row['unit_pks']:
            inserts.append(f"insert into budget_unit_joins values ({unit_pk}, {con_pk})")

        c = list()
        v = list()

        c.append('pk')
        v.append(str(con_pk))

        if row['owner_name'] != '':
            add_to_sql(c, v, 'owner_name', row['owner_name'])

        if row['ariba_id'] != '':
            add_to_sql(c, v, 'ariba_id', row['ariba_id'])

        if row['sap_id'] != '':
            add_to_sql(c, v, 'sap_id', row['sap_id'])

        if row['con_id'] != '':
            add_to_sql(c, v, 'contract_id', row['con_id'])

        add_to_sql(c, v, 'vendor_name', row['v_name'])

        c.append('vendor_pk')
        v.append(str(row['v_pk']))

        add_to_sql(c, v, 'effective_date', row['eff_date'])

        add_to_sql(c, v, 'expir_date', row['exp_date'])

        c.append('contract_value')
        v.append(row['con_value'])

        add_to_sql(c, v, 'commodity_desc', row['descrip'])

        c.append('month_pk')
        v.append(str(41))

        c.append('source_pk')
        v.append(str(source_pks[row['doc_type']]))

        c = ', '.join(c)
        v = ', '.join(v)

        inserts.append(f"insert into contracts ({c}) values ({v})")

        con_pk += 1

    for sql in inserts:
        print(sql)
        db_exec(conn, sql)

    return context


def integrity_check():
    context = dict()
    msgs = list()
    msgs.extend(integrity_check_vendor_pks())
    msgs.extend(integrity_check_contract_ids())
    msgs.extend(integrity_check_changed_vendor_names())
    msgs.extend(integrity_check_changed_descriptions())
    context['messages'] = msgs
    return context


def integrity_check_vendor_pks():
    """
    The vendor_pk in a contract should always go to the same vendor. A vendor
    may have multiple names and, if this occurs, there should be one name in the
    contracts table and the others should appear in the vendor_infos table with
    the 'Alternate Name' key. These alternate names will be checked on import.
    TODO Make the import check the alternate names in the vendor_infos table.
    If multiple vendor names occur, all but one should be added to the list of
    alternate names for the vendor and then the contracts table vendor_name can be
    corrected.
    """
    msgs = list()

    sql = "select vendor_pk as pk, vendor_name as name from contracts"
    vendors = dict()
    for row in db_exec(conn, sql):
        pk = row['pk']
        name = row['name']
        if pk not in vendors:
            vendors[pk] = set()
        vendors[pk].add(name)

    pk_counts = dict()
    for pk in vendors:
        nmlen = len(vendors[pk])
        if nmlen not in pk_counts:
            pk_counts[nmlen] = 0
        pk_counts[nmlen] += 1
        if nmlen > 1:
            print(f"pk: {pk} -> {vendors[pk]}")
    for nmlen in pk_counts:
        msgs.append(f"{nmlen} -> {pk_counts[nmlen]}")

    if len(pk_counts) == 1:
        msgs.append("vendor pk result GOOD")
    else:
        msgs.append("vendor pk result NOT good.")

    return msgs


def fetch_contract_ids(key, sql):
    ids = dict()
    for row in db_exec(conn, sql):
        parts = list()
        if row['ariba_id'] is None:
            parts.append('NULL')
        else:
            parts.append(row['ariba_id'])
        if row['contract_id'] is None:
            parts.append('NULL')
        else:
            parts.append(row['contract_id'])
        if row['sap_id'] is None:
            parts.append('NULL')
        else:
            parts.append(row['sap_id'])
        ids_key = '|'.join(parts)
        if ids_key not in ids:
            ids[ids_key] = list()
        ids[ids_key].append(str(row[key]))
    return ids


def integrity_check_contract_ids():
    msgs = list()
    checked = 0
    bad = 0

    sql = f"select pk, ariba_id, contract_id, sap_id from contracts"
    ids = fetch_contract_ids('pk', sql)

    for ids_key in ids:
        checked += 1
        pks = ids[ids_key]
        uniq_pks = set(ids[ids_key])
        if len(pks) != len(uniq_pks):
            msgs.append(f"BAD contract ids: {ids_key} -> {pks}")
            bad += 1
    msgs.append(f"checked contract ids # {checked}, found bad # {bad}")

    if bad == 0:
        msgs.append(f"contract ids result GOOD")
    else:
        msgs.append(f"contract ids result NOT good")

    return msgs


def integrity_check_changed_vendor_names():
    """
    If multiple vendor names occur, then the latest name should be determined.
    The other names should be added to the list of alternate names for the vendor.
    """
    msgs = list()

    checked = 0
    bad = 0

    sql = f"""
    select v1.name, c1.ariba_id, c1.contract_id, c1.sap_id
    from contracts c1 left outer join vendors v1 on c1.vendor_pk = v1.pk
    """

    ids = fetch_contract_ids('name', sql)
    for ids_key in ids:
        checked += 1
        if len(set(ids[ids_key])) > 1:
            msgs.append(f"CHANGED contract ids to vendor name: {ids_key} -> {ids[ids_key]}")
            bad += 1

    if bad == 0:
        msgs.append(f"checked contract ids matching result to names # {checked}, all GOOD")
    else:
        msgs.append(f"checked contract ids matching result to names # {checked}, found CHANGED # {bad}")

    return msgs


def integrity_check_changed_descriptions():
    """
    Not sure what to do about these changes.
    # TODO Figure out what a changed description means. Is it a real change?
    """
    msgs = list()
    checked = 0
    bad = 0

    sql = f"select commodity_desc, ariba_id, contract_id, sap_id from contracts"
    ids = fetch_contract_ids('commodity_desc', sql)
    for ids_key in ids:
        checked += 1
        if len(set(ids[ids_key])) > 1:
            msgs.append(f"CHANGED contract ids to description: {ids_key} -> {ids[ids_key]}")
            bad += 1

    if bad == 0:
        msgs.append(f"checked contract ids matching result to descriptions # {checked}, all GOOD")
    else:
        msgs.append(f"checked contract ids matching result to descriptions # {checked}, found CHANGED # {bad}")

    return msgs
