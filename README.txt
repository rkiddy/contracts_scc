
Taken from a WebObjects application, this is a read-only application for the data.

To begin:

    - create a venv and install:

    $ python3 -m venv .venv
    $ . .venv/bin/activate
    $ pip install -r requirements.txt

(because I used python3 when I created the venv, pip does the right thing.)

and then:

    $ python -m flask run

and then I can get to the app at:

    http://127.0.0.1:5000/

see https://flask.palletsprojects.com/en/2.1.x/quickstart/

Put this into a .env file at the root of the project:

    FLASK_APP=app
    FLASK_ENV=development
    FLASK_DEBUG=1
    FLASK_RUN_PORT=8080
    APP_HOME=<dir>/contracts
    HOST=<db_host>
    PWD=<db_pwd>
    DB=<db_name>
    WWW=/

finally, run as:

 % python -m flask run

The WWW symbol is used to allow both a server-based and local launch. On a production
host, the app url has a prefix, such as "contracts". On a local execution, this prefix
is set to "contracts/" so that the pages' links can work the same on both locally and
remotely run instances.

The Santa Clara County Civil Grand Jury issued a
<a href="https://www.scscourt.org/court_divisions/civil/cgj/2022/Garbage%20In,%20Garbage%20Out%20-%20Santa%20Clara%20County%20Public%20Contract%20Data.pdf">report</a>
(<a href="https://opencalaccess.org/contracts_scc/SCC_CGJ_2022_PD.pdf">backup</a>)
on December 15, 2022 that lays out many of my issues with the Procurement
Department and uses its access to internal information to lay out many more of the
issues and problems with the system run by the Department.

This script could be used to regenerate the contract_ids table, if this is necessary:

#!/bin/bash

echo "delete from contract_ids;" | mysql ca_scc_contracts

( echo "select pk, 'c', contract_id from contracts where contract_id is not NULL;" | \
    mysql --skip-column-names ca_scc_contracts ;
  echo "select pk, 'a', ariba_id from contracts where ariba_id is not NULL;" | \
    mysql --skip-column-names ca_scc_contracts ;
  echo "select pk, 's', sap_id from contracts where sap_id is not NULL;" | \
    mysql --skip-column-names ca_scc_contracts ) | \
sort -n | \
awk '{print "insert into contract_ids values ("NR", "$1", '\''"$2"'\'', '\''"$3"'\'');"}' | \
  mysql ca_scc_contracts

Import Workarounds:

As of now:

I have to download the PDF files manually.

I have to create an import directory manually, usually /tmp/import.

I have to run the tabula tool manually.

This script can be used to run the PDF scanning with tabula:

#!/bin/bash

java -jar ~/Projects/tabula/tabula-1.0.4-SNAPSHOT-jar-with-dependencies.jar \
    --batch /tmp/import \
    --lattice \
    --format TSV \
    --pages all

I think I have to add the month data and source data manually.

I have to change the code to use the correct TSV files.

I have to change the code to use the correct month.


mysql> insert into months values (43, '2023-06', unix_timestamp()*1000);

mysql> insert into sources values (
    83,
    'https://procurement.sccgov.org/sites/g/files/exjcpb696/files/document/Contracts%20Report%20for%20Month%20of%20May%202023.pdf',
    'https://opencalaccess.org/contracts_scc/exports/2023-05/Contracts%20Report%20for%20Month%20of%20May%202023.pdf',
    42,
    NULL
), (
    84,
    'https://procurement.sccgov.org/sites/g/files/exjcpb696/files/document/SA%20BC%20Report%20for%20Month%20of%20May%202023.pdf',
    'https://opencalaccess.org/contracts_scc/exports/2023-05/SA%20BC%20Report%20for%20Month%20of%20May%202023.pdf',
    42,
    NULL
);

Data Questions:

We have a contract. See http://sccgov.iqm2.com/Citizens/Detail_LegiFile.aspx?Frame=&MeetingID=14895&MediaPosition=&ID=115588&CssClass=

Approve Eighth Amendment to Agreement with Global Tel Link Corporation d/b/a ViaPath Technologies relating to
providing Inmate Calling Systems and Inmate Tablet Systems Platform with no change to the maximum contract
amount, and extending the agreement for an eight-month period through October 21, 2023, that has been reviewed
and approved by County Counsel as to form and legality. (LA-1)


Attachments

    Printout
    CW2231398 Edovo (JISP) Agreement-Executed
    CW2239938 GTL (JISP) AM7- Executed
    CW2239938 GTL (JISP) AM6- Executed
    CW2239938 GTL (JISP) AM5- Executed
    CW2239938 GTL (JISP) AM4- Executed
    CW2239938 GTL (JISP) AM3- Executed
    CW2239938 GTL (JISP) AM2- Executed
    CW2231398 Edovo (JISP) AM1- Executed
    CW2239938 GTL (JISP) AM8_Partially Signed


So, both CW2231398 and CW2239938 represent the same real contract, but the id numbers are different and
the vendor names are different. Supposedly, the company changed its name, but who knows.

What search?

I did a search in the BoS meeting materials site for "4leaf". It returned 54 attachements.

What the heck are these?

Executed Project Agreement No. 7 to PSA with 4Leaf, Inc.
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=196653

Executed Project Agreement #2 with 4Leaf Inc
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=129780

Executed Agreement with 4Leaf
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=168332

Executed Project Agreement No. 4 to PSA with 4Leaf, Inc.
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=196663

Executed Agreement No. 9 with 4Leaf Inc.
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=198037

Executed third PA with 4Leaf Inc
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=139214

Executed 4th Amendment to Project Agreement with 4Leaf, Inc.
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=142122

Executed Project Agreement No. 7 with 4Leaf, Inc.
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=221580

4Leaf PSA
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=141914

Executed Project Agreement No. 5 to PSA with 4Leaf, Inc.
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=218863

Executed Project Agreement #8 with 4Leaf Inc.
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=156833

Executed 1st Agrement for 4 Leaf Inc. PA#9
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=169512

Executed Project Agreement No. 2 with 4Leaf, Inc.
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=210030

Executed Project Agreement No. 1 with 4Leaf, Inc.
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=200002

Executed First Amendment to Agreement with 4Leaf Inc.
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=159208

Executed First Amendment to PA# 1 with 4 Leaf, Inc.
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=133817

Executed First Amendment to Project Agreement No. 2 with 4Leaf, Inc.
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=218261

Executed Project Agreement No. 7 with 4Leaf, Inc.
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=202665

Executed Project Agreement No. 11 to PSA with 4Leaf, Inc.
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=176164

Executed Project Agreement No. 11 with 4Leaf, Inc.
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=202124

Executed Project Agreement No. 3 to PSA with 4Leaf, INc.
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=176266

Executed Project Agreement No. 4 with 4Leaf, Inc.
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=218222

Executed Project Agreement No. 6 with 4Leaf, Inc.
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=218229

Second Amendment to Agreement with 4 Leaf
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=174744

Executed 1st Agrement for 4 Leaf Inc. PA#8
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=156867

Executed Project No. 10 to Professional Services Agreement with 4leaf,
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=163178

Executed Project Agreement No. 1 with 4Leaf, Inc.
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=197615

Executed 1st Agrement for 4 Leaf Inc. PA#9
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=156868

Executed 1st Agrement for 4 Leaf Inc. PA#9
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=156864

Executed Project Agreement No. 10 with 4Leaf, Inc.
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=201235

Executed 1st Amendment to PA#7 with 4Leaf Inc.
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=156815

Executed Project Agreement #5 with 4Leaf Inc
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=151102

Executed 6th Amendment to PA with 4Leaf Inc
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=146004

Executed Project Agreement No. 4 with 4Leaf, Inc.
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=189540

Executed Project Agrement #5 for 4Leaf Inc.
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=200605

Amendment 1 to PSA with 4LEAF-03-11-2016-signed copy
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=147847

4LEAF Inc Service Agreement 4400007558 - Executed
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=189762

Executed 4Leaf Inc PA#7
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=147398

Department of Planning and Development
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=187233

Agreement with 4Leaf
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=205986

Coversheet for 4Leaf Inc PA#7
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=147399

Department of Planning and Development
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=150126

4leaf PSA FINAL
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=119038

4LEAF Tenth Amendment Signed
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=171340

Measure A Financial Report as of January 31, 2018
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=170051

Measure A - Revised Report (Reports 1 through 4) as of December 31, 2
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=145751

Measure A - (Reports 1 through 4) as of December 31, 2015
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=145743

Financial Report Seismic Safety Project as of June 30, 2015
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=143276

Financial Report Seismic Safety Project as of April 30, 2016
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=149660

Executed 2nd Amendment with 4Leaf Inc.
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=156140

Measure A Financial Report as of December 31, 2016
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=157728

4LEAF Approval Request Beyond 5-Year Term Signed
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=171341

Attachment 1 - FY2018 and FY 2019 Term Contracts
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=195000

Off-agenda Report Actions Taken by the County's Purchasing Agent or De
http://sccgov.iqm2.com/Citizens/FileOpen.aspx?Type=4&ID=197961


