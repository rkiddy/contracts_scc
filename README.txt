
Taken from a WebObjects application, this is a read-only application for the data.

To begin:

    - create a venv and install:

    $ python3 -m venv .venv
    $ . .venv/bin/activate
    $ pip install Flask
    $ pip install python-dotenv # not dotenv, not dotenv-python
    $ pip install sqlalchemy
    $ pip install pymysql
    $ pip install cryptography

(because I used python3 when I created the venv, pip does the right thing.)

and then:

    $ FLASK_APP=hello.py python -m flask run

and then I can get to the app at:

    http://127.0.0.1:5000/

see https://flask.palletsprojects.com/en/2.1.x/quickstart/

Put this into a .env file at the root of the project:

    FLASK_APP=app
    FLASK_ENV=development
    FLASK_DEBUG=1
    FLASK_RUN_PORT=8080

finally, run as:

 % python -m flask run

To Do:

- Put the CA (SoS) number alongside the vendor name in the lists.

- On Agencies page and especially the Descriptions page, the right-side column
list is very long. This should be an ajax-ish list which says (# found is ...)
and then a click expands the list and there should be an 'Expand All' in the
column header at the right.

- On the Vendors page, there should be a column that shows number of contracts.

- On pages other then the Vendors page, the number of contracts could be
displayed along with the vendor name.

