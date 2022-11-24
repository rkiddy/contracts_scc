
import sys

from dotenv import dotenv_values
from flask import Flask
from jinja2 import Environment, PackageLoader

cfg = dotenv_values(".env")

sys.path.append(f"{cfg['APP_HOME']}")
import data

contracts_scc = Flask(__name__)
application = contracts_scc
env = Environment(loader=PackageLoader('contracts_scc', 'pages'))


@contracts_scc.route(f"/{cfg['WWW']}scc")
@contracts_scc.route(f"/{cfg['WWW']}scc/")
def contracts_main():
    main = env.get_template('scc_main/scc.html')
    context = data.build_scc_main()
    return main.render(**context)


@contracts_scc.route(f"/{cfg['WWW']}scc/all")
def contracts_all():
    main = env.get_template('scc_all/all.html')
    context = data.all_contracts()
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


@contracts_scc.route(f"/{cfg['WWW']}scc/with_docs")
def contracts_docs():
    costs = env.get_template('contracts/contracts_found.html')
    context = data.build_scc_documents()
    return costs.render(**context)


@contracts_scc.route(f"/{cfg['WWW']}scc/contract/<param>")
def contracts_contract(param):
    contract = env.get_template('contract/contract.html')
    context = data.build_scc_contract()
    return contract.render(**context)


@contracts_scc.route(f"/{cfg['WWW']}scc/search", methods=['POST'])
def contracts_search(sort=None):
    costs = env.get_template('contracts/contracts_found.html')
    context = data.build('scc_search', sort)
    return costs.render(**context)


if __name__ == '__main__':
    contracts_scc.run()
