FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    bash procps gcc g++ make libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

# Instala las dependencias de tu proyecto (si tienes requirements.txt)
RUN pip install --no-cache-dir -r requirements.txt

RUN chmod +x /app/start.sh

CMD ["/bin/bash", "/app/start.sh"]

CMD ["tail", "-f", "/dev/null"]