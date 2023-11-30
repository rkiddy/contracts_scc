import re

from dotenv import dotenv_values
from sqlalchemy import create_engine
import datetime as dt

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

    print(f"rows: {rows}")

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

    context['key'] = cfg['ADMIN_KEY']

    return context


def line_is_header(line):

    if line.startswith('Document Type') or line.startswith('Report Month'):
        return True
    if 'Effective Date' in line:
        return True
    if 'Commodity Desc' in line:
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
    # in SA BC file:
    #   PRE-June, 2023
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
    #   June, 2023 and after:
    #     0: Report Type
    #     1: Document Type
    #     2: Budget Unit
    #     3: Budget Unit Name
    #     4: "Contract ID (PO ID)"
    #     5: Vendor Name
    #     6: Effective Date
    #     7: Expiration Date
    #     8: "Contract Value (PO Value)"
    #     9: Commodity Description
    #
    # if month is before '2023-06', ofst = 0.
    ofst = 1

    try:
        row = dict()
        row['owner_name'] = ''
        row['doc_type'] = parts[0+ofst]
        row['units'] = [fix_unit_name(f"{parts[2+ofst]} - {parts[1+ofst]}")]
        row['ariba_id'] = ''
        row['sap_id'] = ''
        row['con_id'] = parts[3+ofst]
        row['v_name'] = parts[4+ofst]
        row['eff_date'] = fix_date(parts[5+ofst])
        row['exp_date'] = fix_date(parts[6+ofst])
        row['con_value_orig'] = parts[7+ofst]
        row['con_value'] = fix_money(parts[7+ofst])
        row['descrip'] = parts[8+ofst].strip()
    except Exception as e:
        print(f"BAD SABC row: {parts}")
        raise e

    return row


def contract_data(parts):
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
    try:
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
    except Exception as e:
        print(f"BAD CON row: {parts}")
        raise e

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
    pass


def unit_pks_for_names(names):
    pks = list()
    for name in names:
        # TODO WHY do I have to do this here? I should not!
        if name.startswith('Board'):
            pass
        name = fix_unit_name(name)
        if name not in unit_names:
            raise Exception(f"Cannot find unit with name: '{name}'")
        pks.append(unit_names[name])
    return pks


def fetch_max_pk(table):
    sql = f"select max(pk) as pk from {table}"
    return db_exec(conn, sql)[0]['pk']


def fetch_max_month_pk():
    sql = "select max(pk) as pk from months where approved is not NULL"
    return int(db_exec(conn, sql)[0]['pk'])


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


def add_month(request):
    month_nums = request.form.get('month')
    source_url1 = request.form.get('source_url1').replace('%20', ' ')
    alt_url1 = request.form.get('alt_url1').replace('%20', ' ')
    source_url2 = request.form.get('source_url2').replace('%20', ' ')
    alt_url2 = request.form.get('alt_url2').replace('%20', ' ')
    now = int(dt.datetime.now().timestamp() * 1000)
    month_pk = fetch_max_pk('months')

    sql = f"insert into months values ({month_pk+1}, '{month_nums}', {now})"
    db_exec(conn, sql)

    sources_pk = fetch_max_pk('sources')

    sql = f"""
        insert into sources values
        ({sources_pk+1},  '{source_url1}', '{alt_url1}', {month_pk+1}),
        ({sources_pk+2},  '{source_url2}', '{alt_url2}', {month_pk+1})
    """
    print(f"sql: {sql}")
    db_exec(conn, sql)
    print(f"Created: month = {month_nums}")


def add_to_sql(cols, values, col, value):
    """Assumes string, adds to cols and values."""
    if value != '':
        cols.append(col)
        values.append(sql_safe(value))


def imports(action, form):
    context = dict()
    context['action'] = action

    if action == 'prepare':
        sql = "select month, substr(from_unixtime(approved/1000),1,16) as approved from months order by pk desc;"
        context['months'] = db_exec(conn, sql)

    if action == 'add_month':
        next_month = form['next_month']
        print(f"next_month: {next_month}")

        # Make sure we do not double-add the month.
        #
        sql = f"select * from months where month = '{next_month}'"
        rows = db_exec(conn, sql)
        if len(rows) > 0:
            pk = rows[0]['pk']
        else:
            now = int(dt.datetime.now().timestamp() * 1000)
            pk = fetch_max_pk('months') + 1
            sql = f"insert into months values ({pk}, '{next_month}', {now})"
            db_exec(conn, sql)

        context['month'] = next_month
        context['month_pk'] = pk
        context['action'] = 'add_sources'

    if action == 'add_sources':

        month_pk = form['month_pk']
        pk1 = fetch_max_pk('sources') + 1
        pk2 = pk1 + 1

        # TODO do not worry about adding duplicates for now.
        #
        url = form['source_1_url']
        url_alt = form['source_1_url_alt']
        sql = f"insert into sources values ({pk1}, '{url}', '{url_alt}', {month_pk})"
        db_exec(conn, sql)

        url = form['source_2_url']
        url_alt = form['source_2_url_alt']
        sql = f"insert into sources values ({pk2}, '{url}', '{url_alt}', {month_pk})"
        db_exec(conn, sql)

        context = dict(form)
        context['action'] = 'add_data'

        print(f"context: {context}")

    if action == 'add_data':
        print("DO EVERYTHING")
        print(f"form: {form}")
        print(f"context: {context}")

        rows = list()

        if '/Contracts' in form['source_1_url']:
            con_url = form['source_1_url']
            sabc_url = form['source_2_url']
        else:
            con_url = form['source_2_url']
            sabc_url = form['source_1_url']

        con_filename = con_url.split('/')[-1].replace('%20', ' ').replace('.pdf', '.tsv')
        sabc_filename = sabc_url.split('/')[-1].replace('%20', ' ').replace('.pdf', '.tsv')

        con_file = f"/tmp/import/{con_filename}"
        sabc_file = f"/tmp/import/{sabc_filename}"

        # TODO call the sabd and contracts file reads as method calls here.

        with open(sabc_file, 'r') as sabc_fd:

            for line in sabc_fd:

                if not line_is_header(line):
                    parts = line.strip('\r').split('\t')
                    row = sabc_data(parts)
                    rows.append(row)

        bad_lines = list()
        with open(con_file, 'r') as con_fd:

            for line in con_fd:

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

        max_con_pk = fetch_max_pk('contracts')
        max_cid_pk = fetch_max_pk('contract_ids')

        mpk = fetch_max_month_pk()

        source_pks = fetch_source_pks(mpk)

        fetch_units()

        con_pk = max_con_pk + 1
        cid_pk = max_cid_pk + 1

        inserts = list()

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
                ariba_id = row['ariba_id']
                if ariba_id.startswith('anCW'):
                    ariba_id = ariba_id[2:]
                add_to_sql(c, v, 'ariba_id', ariba_id)

            if row['sap_id'] != '':
                add_to_sql(c, v, 'sap_id', row['sap_id'])

            if row['con_id'] != '':
                con_id = row['con_id']
                if con_id.startswith('ices'):
                    con_id = con_id[5:]
                if con_id.startswith('Mgmt'):
                    con_id = con_id[5:]
                add_to_sql(c, v, 'contract_id', con_id)

            add_to_sql(c, v, 'vendor_name', row['v_name'])

            c.append('vendor_pk')
            v.append(str(row['v_pk']))

            add_to_sql(c, v, 'effective_date', row['eff_date'])

            add_to_sql(c, v, 'expir_date', row['exp_date'])

            c.append('contract_value')
            v.append(row['con_value'])

            add_to_sql(c, v, 'commodity_desc', row['descrip'])

            c.append('month_pk')
            v.append(str(mpk))

            c.append('source_pk')
            v.append(str(source_pks[row['doc_type']]))

            c = ', '.join(c)
            v = ', '.join(v)

            inserts.append(f"insert into contracts ({c}) values ({v})")

            con_pk += 1

        for sql in inserts:
            print(sql)
            db_exec(conn, sql)

        context['action'] = 'done'
        print("DONE")

    return context
