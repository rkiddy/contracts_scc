
import sys

from dotenv import dotenv_values
from flask import Flask, request, redirect
from jinja2 import Environment, PackageLoader

import data
import imports
import integrity

cfg = dotenv_values(".env")

sys.path.append(f"{cfg['APP_HOME']}")


contracts_scc = Flask(__name__)
application = contracts_scc
env = Environment(loader=PackageLoader('contracts_scc'))


@contracts_scc.route(f"/{cfg['WWW']}scc")
@contracts_scc.route(f"/{cfg['WWW']}scc/")
def contracts_main():
    main = env.get_template('scc_main/scc.html')
    context = data.build_scc_main()
    return main.render(**context)


@contracts_scc.route(f"/{cfg['WWW']}scc/all")
@contracts_scc.route(f"/{cfg['WWW']}scc/all/")
def contracts_all():
    main = env.get_template('scc_all/all.html')
    context = data.build_all_contracts()
    context['show_as'] = 'html'
    return main.render(**context)


@contracts_scc.route(f"/{cfg['WWW']}scc/vendor/<vendor_pk>")
def contracts_vendor(vendor_pk):
    main = env.get_template('scc_all/all.html')
    context = data.vendor_contracts(vendor_pk)
    return main.render(**context)


@contracts_scc.route(f"/{cfg['WWW']}scc/agency/<agency_pk>")
def contracts_agency(agency_pk):
    main = env.get_template('scc_all/all.html')
    context = data.agency_contracts(agency_pk)
    return main.render(**context)


@contracts_scc.route(f"/{cfg['WWW']}scc/desc/<description>")
def contracts_description(description):
    main = env.get_template('scc_all/all.html')
    context = data.description_contracts(description)
    return main.render(**context)


@contracts_scc.route(f"/{cfg['WWW']}scc/bucket/<bucket>")
def contracts_bucket(bucket):
    main = env.get_template('scc_all/all.html')
    context = data.bucket_contracts(bucket)
    return main.render(**context)


@contracts_scc.route(f"/{cfg['WWW']}scc/contract/<param>")
def contracts_contract(param):
    contract = env.get_template('contract/contract.html')
    context = data.build_scc_contract()
    return contract.render(**context)


@contracts_scc.route(f"/{cfg['WWW']}scc/type/<param>")
def contracts_types(param):
    contract = env.get_template('scc_type/scc_type.html')
    context = data.build_type_data(param)
    return contract.render(**context)


@contracts_scc.route(f"/{cfg['WWW']}scc/docs")
@contracts_scc.route(f"/{cfg['WWW']}scc/docs/")
def contracts_docs():
    contract = env.get_template('scc_docs/supporting.html')
    context = data.build_supporting_docs()
    return contract.render(**context)


@contracts_scc.route(f"/{cfg['WWW']}scc/imports")
@contracts_scc.route(f"/{cfg['WWW']}scc/imports/")
def contracts_imports():
    contract = env.get_template('imports.html')
    context = imports.imports_main()
    return contract.render(**context)


@contracts_scc.route(f"/{cfg['WWW']}scc/integrity")
def contracts_integrity():
    contract = env.get_template('imports.html')
    context = integrity.integrity_check()
    return contract.render(**context)


@contracts_scc.route(f"/{cfg['WWW']}scc/import_scan/<digest>")
def contracts_import_scan(digest):
    if 'ADMIN_KEY' in cfg and cfg['ADMIN_KEY'] == digest:
        contract = env.get_template('imports.html')
        context = imports.import_scan()
        return contract.render(**context)
    else:
        return contracts_main()


@contracts_scc.route(f"/{cfg['WWW']}scc/import_save/<digest>")
def contracts_import_save(digest):
    if 'ADMIN_KEY' in cfg and cfg['ADMIN_KEY'] == digest:
        contract = env.get_template('imports.html')
        context = imports.import_save()
        return contract.render(**context)
    else:
        return contracts_main()


@contracts_scc.route(f"/{cfg['WWW']}scc/months/<digest>")
def contracts_months(digest):
    if 'ADMIN_KEY' in cfg and cfg['ADMIN_KEY'] == digest:
        contract = env.get_template('months.html')
        return contract.render()
    else:
        return contracts_main()


@contracts_scc.route(f"/{cfg['WWW']}scc/add_month", methods=['POST'])
def contracts_add_month():
    imports.add_month(request)
    return redirect(f"/{cfg['WWW']}scc/imports")


if __name__ == '__main__':
    contracts_scc.run(port=8080)
