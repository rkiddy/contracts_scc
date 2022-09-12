
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

finally, run as:

 % FLASK_APP=app FLASK_ENV=development FLASK_DEBUG=1 FLASK_RUN_PORT=8080 python -m flask run


