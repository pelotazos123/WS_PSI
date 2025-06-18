FROM python:3.11-slim

RUN apt-get update && apt-get install -y bash procps

WORKDIR /app

COPY . .

RUN cd WS_PSI && python3 -m venv WS-PSI-ENV

RUN chmod +x /app/start.sh

CMD ["tail", "-f", "/dev/null"]