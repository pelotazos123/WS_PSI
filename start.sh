#!/bin/bash
cd WS_PSI
source WS-PSI-ENV/bin/activate
chmod +x setup.sh
./setup.sh
pip install waitress 
waitress-serve --host 0.0.0.0 --port 8080 --call flaskr:create_app & tail -f /dev/null