FROM python:3.7.1-stretch

RUN pip3 install numpy pandas paramiko flask sklearn gevent Pillow requests matplotlib

COPY . /

EXPOSE 5000

ENTRYPOINT python3 server/server.py
