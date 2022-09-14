import re

import jinja2
from flask import Flask
from flask import request

import data

app = Flask(__name__)
env = jinja2.Environment(loader=jinja2.FileSystemLoader("pages"))


@app.route('/')
def hello_world():
    return '<h2>Hello, World!</h2>'


@app.route('/contracts/scc')
@app.route('/contracts/scc/')
def contracts_main():
    main = env.get_template('scc_main/scc.html')
    context = data.build('scc_main')
    return main.render(**context)


@app.route('/contracts/scc/vendors')
@app.route('/contracts/scc/vendors/')
def contracts_vendors():
    vendors = env.get_template('scc_vendors/vendors.html')
    context = data.build('scc_vendors')
    return vendors.render(**context)


@app.route("/contracts/scc/vendors/<param>")
def contracts_vendors_by_letter(param):
    if not re.match("^[A-Z]$", param) and param not in ['All', 'NA']:
        raise Exception("Invalid choice for vendor prefix")
    else:
        vendors = env.get_template('scc_vendors/vendors.html')
        context = data.build('scc_vendors')
        return vendors.render(**context)


@app.route('/contracts/scc/agencies')
@app.route('/contracts/scc/agencies/')
def contracts_agencies():
    agencies = env.get_template('scc_agencies/agencies.html')
    context = data.build('scc_agencies')
    return agencies.render(**context)


@app.route('/contracts/scc/contracts/<param>')
def contracts_costs_by_bucket(param):
    # allow any type of parameter for now.
    costs = env.get_template('contracts/contracts_found.html')
    context = data.build('scc_contracts')
    return costs.render(**context)


@app.route('/contracts/scc/descs')
@app.route('/contracts/scc/descs/')
def contracts_descs():
    descs = env.get_template('scc_descs/descs.html')
    context = data.build('scc_descs')
    return descs.render(**context)


@app.route('/contracts/scc/contract/<param>')
def contracts_contract(param):
    contract = env.get_template('contract/contract.html')
    context = data.build('scc_contract')
    return contract.render(**context)


@app.route('/contracts/scc/search', methods=['POST'])
def contracts_search():
    costs = env.get_template('contracts/contracts_found.html')
    context = data.build('scc_contracts')
    return costs.render(**context)
