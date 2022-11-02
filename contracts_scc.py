
import re
import sys

from flask import Flask
from jinja2 import Environment, PackageLoader

sys.path.append("/var/www/opencalaccess_org/contracts_scc/")

import data

contracts_scc = Flask(__name__)
application = contracts_scc
# env = Environment(loader=PackageLoader('app','pages'))
env = Environment(loader=PackageLoader('contracts_scc', 'pages'))


@contracts_scc.route('/')
def hello_world():
    return '<h2><a href="contracts/scc">Launch</a></h2>'


@contracts_scc.route('/contracts/scc')
@contracts_scc.route('/contracts/scc/')
def contracts_main():
    main = env.get_template('scc_main/scc.html')
    context = data.build('scc_main')
    return main.render(**context)


@contracts_scc.route('/contracts/scc/vendors')
@contracts_scc.route('/contracts/scc/vendors/')
def contracts_vendors():
    vendors = env.get_template('scc_vendors/vendors.html')
    context = data.build('scc_vendors')
    return vendors.render(**context)


@contracts_scc.route("/contracts/scc/vendors/<param>")
def contracts_vendors_by_letter(param):
    if not re.match("^[A-Z]$", param) and param not in ['All', 'NA']:
        raise Exception("Invalid choice for vendor prefix")
    else:
        vendors = env.get_template('scc_vendors/vendors.html')
        context = data.build('scc_vendors')
        return vendors.render(**context)


@contracts_scc.route('/contracts/scc/agencies')
@contracts_scc.route('/contracts/scc/agencies/')
def contracts_agencies():
    agencies = env.get_template('scc_agencies/agencies.html')
    context = data.build('scc_agencies')
    return agencies.render(**context)


@contracts_scc.route('/contracts/scc/contracts/<param>')
def contracts(param):
    # allow any type of parameter for now.
    costs = env.get_template('contracts/contracts_found.html')
    context = data.build('scc_contracts')
    return costs.render(**context)


@contracts_scc.route('/contracts/scc/descs')
@contracts_scc.route('/contracts/scc/descs/')
def contracts_descs():
    descs = env.get_template('scc_descs/descs.html')
    context = data.build('scc_descs')
    return descs.render(**context)


@contracts_scc.route('/contracts/scc/contract/<param>')
def contracts_contract(param):
    contract = env.get_template('contract/contract.html')
    context = data.build('scc_contract')
    return contract.render(**context)


@contracts_scc.route('/contracts/scc/search', methods=['POST'])
def contracts_search():
    costs = env.get_template('contracts/contracts_found.html')
    context = data.build('scc_search')
    return costs.render(**context)


@contracts_scc.route('/contracts/scc/contracts_docs')
@contracts_scc.route('/contracts/scc/contracts_docs/')
def contracts_docs():
    costs = env.get_template('contracts/contracts_found.html')
    context = data.build('scc_documents')
    return costs.render(**context)


if __name__ == '__main__':
    contracts_scc.run()
