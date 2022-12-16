FROM alpine:latest

# UPDATE IMAGE
RUN apk update && apk upgrade -q --prune

# SETUP PYTHON
ENV PYTHONUNBUFFERED=1
RUN apk add --no-cache python3 py3-pip && ln -sf python3 /usr/bin/python
RUN python3 -m ensurepip
RUN pip3 install --no-cache --upgrade pip setuptools

# SETUP script prereqs
RUN mkdir -p /opt/dsmr2mqtt
WORKDIR /opt/dsmr2mqtt
COPY ./requirements.txt /opt/dsmr2mqtt/requirements.txt
RUN pip3 install -r /opt/dsmr2mqtt/requirements.txt

# COPY script file
COPY ./dsmr2mqtt.py /opt/dsmr2mqtt/dsmr2mqtt.py
RUN chmod +x /opt/dsmr2mqtt/dsmr2mqtt.py

CMD ["python3", "/opt/dsmr2mqtt/dsmr2mqtt.py"]