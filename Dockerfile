FROM python:3.11-slim

RUN apt-get update && apt-get install -y bash procps

WORKDIR /app

COPY . .

WORKDIR /app/WS_PSI

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install scikit-learn
RUN chmod +x /app/start.sh

CMD ["tail", "-f", "/dev/null"]