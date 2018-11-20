FROM python:3.7

RUN pip3 install numpy pandas paramiko flask sklearn gevent

COPY . /

EXPOSE 5000

ENTRYPOINT python3 server/server.py
