
import sys

from dotenv import dotenv_values
from flask import Flask, request
from jinja2 import Environment, PackageLoader

import data
import imports
import integrity

cfg = dotenv_values(".env")

sys.path.append(f"{cfg['APP_HOME']}")


contracts_scc = Flask(__name__)
application = contracts_scc
env = Environment(loader=PackageLoader('contracts_scc'))


@contracts_scc.route(f"/{cfg['WWW']}scc/")
def contracts_main():
    main = env.get_template('scc_main/scc.html')
    context = data.build_scc_main()
    return main.render(**context)


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
    context = data.build_scc_contract(param)
    return contract.render(**context)


@contracts_scc.route(f"/{cfg['WWW']}scc/type/<param>")
def contracts_types(param):
    contract = env.get_template('scc_type/scc_type.html')
    context = data.build_type_data(param)
    return contract.render(**context)


@contracts_scc.route(f"/{cfg['WWW']}scc/docs/")
def contracts_docs():
    contract = env.get_template('scc_docs/supporting.html')
    context = data.build_supporting_docs()
    return contract.render(**context)


# use imports/prepare/<key> to start the import process.
#
@contracts_scc.route(f"/{cfg['WWW']}scc/imports/<action>/<key>", methods=['GET', 'POST'])
def contracts_imports(action, key=None):
    if key != cfg['ADMIN_KEY']:
        raise Exception("Sorry, please use the proper admin key.")
    contract = env.get_template('imports.html')
    context = imports.imports(action, request.form)
    return contract.render(**context)


@contracts_scc.route(f"/{cfg['WWW']}scc/integrity")
def contracts_integrity():
    contract = env.get_template('integrity.html')
    context = integrity.integrity_check()
    return contract.render(**context)


if __name__ == '__main__':
    contracts_scc.run(port=8080)
