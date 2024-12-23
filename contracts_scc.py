
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
    """
    Builds the front page. Uses templates for top_agency, top_costs, top_descriptions, top_vendors,
    so it needs all these as keys in the context.
    """

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


if __name__ == '__main__':
    contracts_scc.run(port=8080)
