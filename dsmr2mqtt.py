import os
import datetime

from dsmr_parser import telegram_specifications
from dsmr_parser.clients import SerialReader, SERIAL_SETTINGS_V5

from paho.mqtt import client as mqtt_client

# ENVIRONMENT VARIABLES
MQTT_HOST = os.environ.get('MQTT_HOST', 'mqtt')
MQTT_PORT = int(os.environ.get('MQTT_PORT', 1883))
MQTT_CLIENTID = os.environ.get('MQTT_CLIENTID', 'dsmr2mqtt')
DSMR_PORT = os.environ.get('DSMR_PORT', '/dev/ttyUSB0')
DSMR_VERSION = os.environ.get('DSMR_VERSION', 5)
REPORT_INTERVAL = int(os.environ.get('REPORT_INTERVAL', 15))

print("MQTT Host:       ", MQTT_HOST)
print("MQTT Port:       ", MQTT_PORT)
print("MQTT Client ID:  ", MQTT_CLIENTID)
print("DSMR_PORT:       ", DSMR_PORT)
print("Report interval: ", REPORT_INTERVAL, "s")

def connect_mqtt():
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    client = mqtt_client.Client(MQTT_CLIENTID)
#    client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.connect(MQTT_HOST, MQTT_PORT)
    return client

def process(topic, value):
  try:
    client.publish(topic, str(value))
  except KeyError:
    print(f"{topic} has no value")

def publish(telegram):
  process("dsmr/meter-stats/dsmr_version", telegram.P1_MESSAGE_HEADER.value)
  process("dsmr/reading/timestamp", str(telegram.P1_MESSAGE_TIMESTAMP.value))
  process("dsmr/meter-stats/dsmr_meter_id", telegram.EQUIPMENT_IDENTIFIER.value)
  process("dsmr/reading/electricity_delivered_1", telegram.ELECTRICITY_USED_TARIFF_1.value)
  process("dsmr/reading/electricity_delivered_2", telegram.ELECTRICITY_USED_TARIFF_2.value)
  process("dsmr/reading/electricity_returned_1", telegram.ELECTRICITY_DELIVERED_TARIFF_1.value)
  process("dsmr/reading/electricity_returned_2", telegram.ELECTRICITY_DELIVERED_TARIFF_2.value)
  process("dsmr/meter-stats/electricity_tariff", telegram.ELECTRICITY_ACTIVE_TARIFF.value)
  process("dsmr/reading/electricity_currently_delivered", telegram.CURRENT_ELECTRICITY_USAGE.value)
  process("dsmr/reading/electricity_currently_returned", telegram.CURRENT_ELECTRICITY_DELIVERY.value)
  process("dsmr/meter-stats/power_failure_count", telegram.LONG_POWER_FAILURE_COUNT.value)
  process("dsmr/meter-stats/voltage_sag_count_l1", telegram.VOLTAGE_SAG_L1_COUNT.value)
  process("dsmr/meter-stats/voltage_swell_count_l1", telegram.VOLTAGE_SWELL_L1_COUNT.value)
  process("dsmr/meter-stats/dsmr_meter_type", telegram.DEVICE_TYPE.value)
  process("dsmr/reading/phase_currently_delivered_l1", telegram.INSTANTANEOUS_ACTIVE_POWER_L1_POSITIVE.value)
  process("dsmr/reading/phase_currently_returned_l1", telegram.INSTANTANEOUS_ACTIVE_POWER_L1_NEGATIVE.value)
  process("dsmr/meter-stats/gas_meter_id", telegram.EQUIPMENT_IDENTIFIER_GAS.value)
  process("dsmr/consumption/gas/read_at", telegram.HOURLY_GAS_METER_READING.value)
  process("dsmr/reading/phase_voltage_l1", telegram.INSTANTANEOUS_VOLTAGE_L1.value)
  process("dsmr/reading/phase_power_current_l1", telegram.INSTANTANEOUS_CURRENT_L1.value)

client = connect_mqtt()
lastrun = datetime.datetime(2000,1,1)
# DSMR connection
serial_reader = SerialReader(
    device=DSMR_PORT,
    serial_settings=SERIAL_SETTINGS_V5,
    telegram_specification=telegram_specifications.V5
)

for telegram in serial_reader.read_as_object():
    if ((datetime.datetime.now() - lastrun).seconds >= REPORT_INTERVAL):
        lastrun = datetime.datetime.now()
        publish(telegram)
