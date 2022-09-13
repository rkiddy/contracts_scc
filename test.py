
import pprint

import data

print("scc_main:")
pprint.pprint(data.build('scc_main'), compact=True)
print("")

print("scc_vendors:")
pprint.pprint(data.build('scc_vendors'), compact=True)
print("")

print("scc_agencies:")
pprint.pprint(data.build('scc_agencies'), compact=True)
print("")

print("scc_descs:")
pprint.pprint(data.build('scc_descs'), compact=True)
print("")

print("scc_contracts:")
pprint.pprint(data.build('scc_contracts'), compact=True)
print("")

print("scc_contract:")
pprint.pprint(data.build('scc_contract'), compact=True)
print("")
