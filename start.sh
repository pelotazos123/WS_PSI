#!/bin/bash
pip install waitress
pip install -r requirements.txt
pip install scikit-learn

cd Crypto/py-fhe
pip install .
cd ../..

waitress-serve --host 0.0.0.0 --port 8080 --call flaskr:create_app & tail -f /dev/null