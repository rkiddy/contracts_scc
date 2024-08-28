
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

