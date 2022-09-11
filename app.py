from flask import Flask
app = Flask(__name__)

import jinja2

import data

env = jinja2.Environment(loader=jinja2.FileSystemLoader("pages"))


@app.route('/')
def hello_world():
    return '<h2>Hello, World!</h2>'


@app.route('/contracts/scc')
def contracts_scc():
    main = env.get_template('scc_main/scc.html')
    context = data.build('scc_main')
    return main.render(**context)


@app.route('/contracts/scc/vendors')
def contracts_vendors():
    vendors = env.get_template('scc_vendors/vendors.html')
    context = data.build('scc_vendors')
    return vendors.render(**context)


@app.route("/contracts/scc/vendors/<first_letter>")
def contracts_vendors_ltr(first_letter):
    vendors = env.get_template('scc_vendors/vendors.html')
    context = data.build('scc_vendors')
    return vendors.render(**context)


@app.route('/contracts/scc/agencies')
def contracts_agencies():
    agencies = env.get_template('scc_agencies/agencies.html')
    context = data.build('scc_agencies')
    return agencies.render(**context)


@app.route('/contracts/scc/costs')
def contracts_costs():
    costs = env.get_template('scc_costs/costs.html')
    context = data.build('scc_costs')
    return costs.render(**context)


@app.route('/contracts/scc/descs')
def contracts_descs():
    descs = env.get_template('scc_descs/descs.html')
    context = data.build('scc_descs')
    return descs.render(**context)
