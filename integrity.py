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


def integrity_check():
    context = dict()
    msgs = list()
    msgs.extend(integrity_check_vendor_missing())
    msgs.extend(integrity_check_vendor_pks())
    msgs.extend(integrity_check_vendor_names())
    # TAKING THIS OUT - msgs.extend(integrity_check_contract_ids())
    # TOO MANY? msgs.extend(integrity_check_changed_vendor_names())
    # TOO MANY? msgs.extend(integrity_check_changed_descriptions())
    msgs.extend(integrity_check_contract_id_types_not_crossed())
    msgs.extend(integrity_check_contract_ids_not_duplicated())
    context['messages'] = msgs
    return context


def integrity_check_vendor_missing():
    msgs = list()

    msgs.append('Question: Is a vendor in the contracts list missing from the vendor list or vice-versa?')

    sql = """
        select c1.vendor_name, c1.vendor_pk, v1.pk, v1.name
        from contracts c1 right outer join vendors v1 on c1.vendor_pk = v1.pk 
        where v1.name is NULL or c1.vendor_name is NULL;
    """
    ok = True
    for found in db_exec(conn, sql):
        msgs.append(str(found))
        ok = False

    if ok:
        msgs.append("vendor missing result GOOD")
    else:
        msgs.append("vendor missing result NOT good.")

    return msgs


def integrity_check_vendor_pks():
    msgs = list()

    msgs.append('Question: Is it possible that two vendors have the same name but not the same pk values?')

    sql = """
        select distinct(concat(c1.vendor_pk, ' - ', c1.vendor_name, ' - ', c2.vendor_name)) as vendor
        from contracts c1, contracts c2
        where c1.vendor_name = c2.vendor_name and c1.vendor_pk != c2.vendor_pk;
    """
    ok = True
    for row in db_exec(conn, sql):
        msgs.append(row['vendor'])
        ok = False

    if ok:
        msgs.append("vendor pk result GOOD")
    else:
        msgs.append("vendor pk result NOT good.")

    return msgs


def integrity_check_vendor_names():
    msgs = list()

    msgs.append('Question: Is it possible that, for a vendor pk, there are different names not added in vendor_infos?')

    sql = """
        select distinct(concat(c1.vendor_name, '|', c1.vendor_pk, '|', v1.name)) as info
        from contracts c1 left outer join vendors v1 on c1.vendor_pk = v1.pk
        where c1.vendor_name != v1.name
    """
    sqls = dict()
    ok = True
    for found in db_exec(conn, sql):
        # For each name I do not match, check with the 'Alternate Name' values.
        parts = str(found['info']).split('|')
        sqls[str(found['info'])] = f"""
            select value_str from vendor_infos
            where vendor_pk = {parts[1]} and key_name = 'Alternate Name'
        """
    ok = True
    for info in sqls:
        parts = info.split('|')
        sql = sqls[info]
        alt_found = False
        for val in db_exec(conn, sql):
            if val['value_str'] == parts[0]:
                alt_found = True
        if not alt_found:
            msgs.append(f"contract name: '{parts[0]}', vendor_pk: {parts[1]}, vendor name: '{parts[2]}'")
            ok = False

    if ok:
        msgs.append("vendor name result GOOD")
    else:
        msgs.append("vendor name result NOT good.")

    return msgs


#
# def fetch_contract_ids(key, sql):
#     ids = dict()
#     for row in db_exec(conn, sql):
#         parts = list()
#         if row['ariba_id'] is None:
#             parts.append('NULL')
#         else:
#             parts.append(row['ariba_id'])
#         if row['contract_id'] is None:
#             parts.append('NULL')
#         else:
#             parts.append(row['contract_id'])
#         if row['sap_id'] is None:
#             parts.append('NULL')
#         else:
#             parts.append(row['sap_id'])
#         ids_key = '|'.join(parts)
#         if ids_key not in ids:
#             ids[ids_key] = list()
#         ids[ids_key].append(str(row[key]))
#     return ids
#
#
# def integrity_check_contract_ids():
#     msgs = list()
#
#     msgs.append('Question: ')
#     checked = 0
#     bad = 0
#
#     sql = f"select pk, ariba_id, contract_id, sap_id from contracts"
#     ids = fetch_contract_ids('pk', sql)
#
#     for ids_key in ids:
#         checked += 1
#         pks = ids[ids_key]
#         uniq_pks = set(ids[ids_key])
#         if len(pks) != len(uniq_pks):
#             msgs.append(f"BAD contract ids: {ids_key} -> {pks}")
#             bad += 1
#     msgs.append(f"checked contract ids # {checked}, found bad # {bad}")
#
#     if bad == 0:
#         msgs.append(f"contract ids result GOOD")
#     else:
#         msgs.append(f"contract ids result NOT good")
#
#     return msgs


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


def integrity_check_contract_id_types_not_crossed():
    """
    A contract should either be from the Contracts source and it will have one or both
    of an Ariba Id and an SAP id and no Contract Id, or the contract should be from the
    SA BC file and it will have a Contract ID and no Ariba Id or SAP Id. If it has a
    Contract Id and either a Ariba Id or SAP Id, something is wrong.
    """
    msgs = list()

    msgs.append('Question: Do all contracts have a Contract ID, or a Ariba and SAP ID combination, but not both?')

    sql = """
        select * from contracts
        where contract_id is not NULL and
            (ariba_id is not NULL or sap_id is not NULL)
        """
    rows = db_exec(conn, sql)
    if rows is None or len(rows) == 0:
        msgs.append(f"contract id types not crossing, result GOOD")
    else:
        for row in rows:
            msgs.append(f"crossed id type contract: {row}")
        msgs.append(f"contract id types CROSSING, result bad")

    return msgs


def integrity_check_contract_ids_not_duplicated():
    msgs = list()

    msgs.append('Question: Might two contracts have the same Ariba ID, but not the same SAP ID, or vice-versa?')

    differing_ariba_ids = list()

    sql = """
        select distinct(concat(c1.sap_id, ' - ', c1.ariba_id, ' - ', c2.ariba_id)) as ids
        from contracts c1, contracts c2
        where c1.sap_id = c2.sap_id and c1.ariba_id < c2.ariba_id;
        """
    rows = db_exec(conn, sql)
    for row in rows:
        differing_ariba_ids.append(row['ids'])

    differing_sap_ids = list()

    sql = """
        select distinct(concat(c1.ariba_id, ' - ', c1.sap_id, ' - ', c2.sap_id)) as ids
        from contracts c1, contracts c2
        where c1.ariba_id = c2.ariba_id and c1.sap_id < c2.sap_id;
        """
    for row in db_exec(conn, sql):
        differing_sap_ids.append(row['ids'])

    if len(differing_ariba_ids) == 0 and len(differing_sap_ids) == 0:
        msgs.append(f"contract ids not duplicated, result GOOD")
    else:
        for row in differing_ariba_ids:
            msgs.append(f"DIFFER ariba_ids: {row}")
        for row in differing_sap_ids:
            msgs.append(f"DIFFER sap_ids: {row}")
        msgs.append(f"contract ids might be DUPLICATED, result bad")

    return msgs
