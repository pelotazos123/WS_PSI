source WS-PSI-ENV/bin/activate

waitress-serve --host=0.0.0.0 --port=8080 --call flaskr:create_app

