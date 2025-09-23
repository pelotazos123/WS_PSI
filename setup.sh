#!/bin/bash

ENV_NAME="WS-PSI-ENV"
echo "### PSI Suite - Instalador de dependencias ###"
echo "Por favor, asegúrate de que este instalador se esté ejecutando en un entorno Linux con Python 3.11"
echo "ENV_NAME: $ENV_NAME"
echo "PYTHON VERSION: $(python3.11 --version)"
echo "#############################################"
echo "Creando el entorno virtual... -> $ENV_NAME"
python3.11 -m venv WS-PSI-ENV

echo "Activando el entorno virtual..."
source WS-PSI-ENV/bin/activate

echo "Actualizando pip..."
pip install --no-cache-dir --upgrade pip

echo "Instalando dependencias de requirements.txt..."
pip install --no-cache-dir -r requirements.txt

echo "Instalando dependencia específica de BFV (py-fhe)..."
cd Crypto/py-fhe
pip install .
echo "Instalación completada."
echo "#############################################"
echo "Entorno virtual creado y dependencias instaladas."
