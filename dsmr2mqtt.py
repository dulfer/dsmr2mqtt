import os
import json

from datetime import datetime
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
GAS_CURRENT_CONSUMPTION_REPORT_INTERVAL = int(
    os.environ.get('GAS_CURRENT_CONSUMPTION_REPORT_INTERVAL', 60))
READINGS_PERISTENCE_DATA_PATH = os.environ.get(
    'READINGS_PERISTENCE_DATA_PATH', '/data/readings.json')
LASTREADING_TIMESTAMP = datetime.now().strftime('%Y-%m-%d %H:%M:%s')

print("MQTT Host:       ", MQTT_HOST)
print("MQTT Port:       ", MQTT_PORT)
print("MQTT Client ID:  ", MQTT_CLIENTID)
print("DSMR_PORT:       ", DSMR_PORT)
print("Report interval: ", REPORT_INTERVAL, "s")

current_date = datetime.combine(datetime.today(), datetime.min.time())

def str2bool(value):
  return value.lower() in ("yes", "true", "on", "y", "t", "1", "high")

class MeterPeriod:
    def __init__(self, name, period, start_value=0):
        self.name = name
        self.period = period
        self.start_value = start_value
        self.counter = 0
        self.current_period = self.get_current_period()

    def get_current_period(self):
        date = datetime.now()
        period = self.period
        if period == 'H':
            rollover = date.hour
        elif period == 'D':
            rollover = date.day
        elif period == 'W':
            rollover = date.isocalendar()[1]
        elif period == 'M':
            rollover = date.month
        elif period == 'Y':
            rollover = date.year

        return rollover

    def update_value(self, value):
        period = self.get_current_period()
        if self.current_period != period:
            self.start_value = value

        self.counter = value - self.start_value

    def get_value(self):
        return round(self.counter, 3)

    def get_start_value(self):
        return round(self.start_value, 3)
    
    def set_start_value(self, value):
        self.start_value = round(value, 3)


class Meter:
    def __init__(self, name, start_values = {}):
        self.name = name
        self.current_value = 0
        self.hour = MeterPeriod('{name}_hourly', 'H')
        self.day = MeterPeriod('{name}_daily', 'D')
        self.week = MeterPeriod('{name}_weekly', 'W')
        self.month = MeterPeriod('{name}_monthly', 'M')
        self.year = MeterPeriod('{name}_yearly', 'Y')

        if len(start_values) > 0:
            self.hour.set_start_value(start_values.get('hour', 0))
            self.day.set_start_value(start_values.get('day', 0))
            self.week.set_start_value(start_values.get('week', 0))
            self.month.set_start_value(start_values.get('month', 0))
            self.year.set_start_value(start_values.get('year', 0))

    def update_value(self, value):
        self.current_value = round(value, 3)
        self.hour.update_value(value)
        self.day.update_value(value)
        self.week.update_value(value)
        self.month.update_value(value)
        self.year.update_value(value)
    
class ConsumptionStats:

    def __init__(self, persisted_data):
        self.name = 'Energy Consumption Statistics'

        # electricity used
        self.electricity_used_tariff_low = Meter(
            'electricity_used_tariff_low', 
            persisted_data.get_value('electricity_used_tariff_low')
        )
        self.electricity_used_tariff_high = Meter(
            'electricity_used_tariff_high',
            persisted_data.get_value('electricity_used_tariff_high')
        )

        # electricity delivered
        self.electricity_returned_tariff_low = Meter(
            'electricity_returned_tariff_low',
            persisted_data.get_value('electricity_returned_tariff_low')
        )
        self.electricity_returned_tariff_high = Meter(
            'electricity_returned_tariff_high',
            persisted_data.get_value('electricity_returned_tariff_high')
        )

        # gas used
        self.gas_used = Meter(
            'gas_used', 
            persisted_data.get_value('gas_used')
        )
        
        # local variables
        self.gas_last_reading = 0
        self.gas_current_used = 0

        self.last_gas_current_consumption_report_timestamp = datetime.combine(
            datetime.today(), datetime.min.time())

    def update_gas_consumption(self, gas):
        gas_reading = float(gas)
        self.gas_used.update_value(gas_reading)

        if ((datetime.now() - self.last_gas_current_consumption_report_timestamp).total_seconds() > GAS_CURRENT_CONSUMPTION_REPORT_INTERVAL):
            if (self.gas_last_reading > 0):
                self.gas_current_used = round(
                    (gas_reading - self.gas_last_reading)*(3600/GAS_CURRENT_CONSUMPTION_REPORT_INTERVAL), 3)
                self.last_gas_current_consumption_report_timestamp = datetime.now()

            self.gas_last_reading = gas_reading

    def update_electricity_used(self, tariff, reading):
        if (tariff == '0001'):
            self.electricity_used_tariff_low.update_value(float(reading))
            
        if (tariff == '0002'):
            self.electricity_used_tariff_high.update_value(float(reading))

    def update_electricity_returned(self, tariff, reading):
        if (tariff == '0001'):
            self.electricity_returned_tariff_low.update_value(float(reading))

        if (tariff == '0002'):
            self.electricity_returned_tariff_high.update_value(float(reading))
            
    def gas_today(self):
        return self.gas_used.day.get_value()

    def gas_currently_used(self):
        return self.gas_current_used

    def electricity_used_today(self):
        return round(self.electricity_used_tariff_high.day.get_value() + self.electricity_used_tariff_low.day.get_value(), 3)

    def electricity_returned_today(self):
        return round(self.electricity_returned_tariff_high.day.get_value() + self.electricity_returned_tariff_low.day.get_value(), 3)
    

class DataPersistence:
    def __init__(self) -> None:
        self.data = self.load_datafile()

    def get_value(self, key):
        return self.data[key]

    def set_value(self, key, value):
        self.data[key] = value

    def load_datafile(self):
        with open(READINGS_PERISTENCE_DATA_PATH, 'r') as datafile:
            file_data = json.load(datafile)

        return file_data

    def write_datafile(self):
        self.data['file_date'] = datetime.now()
        with open(READINGS_PERISTENCE_DATA_PATH, 'w') as outfile:
            json.dump(self.data, outfile, indent=4, sort_keys=True, default=str)


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
        if (topic == "dsmr/reading/timestamp"):
            LASTREADING_TIMESTAMP = str(value)

        if (topic == "dsmr/consumption/gas/delivered"):
            stats.update_gas_consumption(str(value))
            client.publish("dsmr/consumption/gas/read_at", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            client.publish("dsmr/consumption/gas/currently_delivered", stats.gas_currently_used())
            client.publish("dsmr/day-consumption/gas", stats.gas_today())

            # also periodically update electricity totals
            client.publish("dsmr/day-consumption/electricity_merged", stats.electricity_used_today())
            client.publish("dsmr/day-consumption/electricity_returned_merged", stats.electricity_returned_today())

        if (topic == "dsmr/reading/electricity_delivered_1"):
            stats.update_electricity_used('0001', str(value))
            client.publish('dsmr/day-consumption/electricity1', stats.electricity_used_tariff_low.day.get_value())

        if (topic == "dsmr/reading/electricity_delivered_2"):
            stats.update_electricity_used('0002', str(value))
            client.publish('dsmr/day-consumption/electricity2', stats.electricity_used_tariff_high.day.get_value())

        if (topic == "dsmr/reading/electricity_returned_1"):
            stats.update_electricity_returned('0001', str(value))
            client.publish('dsmr/day-consumption/electricity1_returned', stats.electricity_returned_tariff_low.day.get_value())

        if (topic == "dsmr/reading/electricity_returned_2"):
            stats.update_electricity_returned('0002', str(value))
            client.publish('dsmr/day-consumption/electricity2_returned', stats.electricity_returned_tariff_high.day.get_value())

        client.publish(topic, str(value))

    except KeyError:
        print(f"{topic} has no value")

def publish(telegram):
    process("dsmr/meter-stats/dsmr_version", telegram.P1_MESSAGE_HEADER.value)
    process("dsmr/reading/timestamp", str(telegram.P1_MESSAGE_TIMESTAMP.value))
    process("dsmr/meter-stats/dsmr_meter_id",
            telegram.EQUIPMENT_IDENTIFIER.value)
    process("dsmr/reading/electricity_delivered_1",
            telegram.ELECTRICITY_USED_TARIFF_1.value)
    process("dsmr/reading/electricity_delivered_2",
            telegram.ELECTRICITY_USED_TARIFF_2.value)
    process("dsmr/reading/electricity_returned_1",
            telegram.ELECTRICITY_DELIVERED_TARIFF_1.value)
    process("dsmr/reading/electricity_returned_2",
            telegram.ELECTRICITY_DELIVERED_TARIFF_2.value)
    process("dsmr/meter-stats/electricity_tariff",
            telegram.ELECTRICITY_ACTIVE_TARIFF.value)
    process("dsmr/reading/electricity_currently_delivered",
            telegram.CURRENT_ELECTRICITY_USAGE.value)
    process("dsmr/reading/electricity_currently_returned",
            telegram.CURRENT_ELECTRICITY_DELIVERY.value)
    process("dsmr/meter-stats/power_failure_count",
            telegram.LONG_POWER_FAILURE_COUNT.value)
    process("dsmr/meter-stats/voltage_sag_count_l1",
            telegram.VOLTAGE_SAG_L1_COUNT.value)
    process("dsmr/meter-stats/voltage_swell_count_l1",
            telegram.VOLTAGE_SWELL_L1_COUNT.value)
    process("dsmr/meter-stats/dsmr_meter_type", telegram.DEVICE_TYPE.value)
    process("dsmr/reading/phase_currently_delivered_l1",
            telegram.INSTANTANEOUS_ACTIVE_POWER_L1_POSITIVE.value)
    process("dsmr/reading/phase_currently_returned_l1",
            telegram.INSTANTANEOUS_ACTIVE_POWER_L1_NEGATIVE.value)
    process("dsmr/reading/phase_voltage_l1",
            telegram.INSTANTANEOUS_VOLTAGE_L1.value)
    process("dsmr/reading/phase_power_current_l1",
            telegram.INSTANTANEOUS_CURRENT_L1.value)
    process("dsmr/meter-stats/gas_meter_id",
            telegram.EQUIPMENT_IDENTIFIER_GAS.value)
    process("dsmr/consumption/gas/delivered",
            telegram.HOURLY_GAS_METER_READING.value)

def persist_datapoints():

    current_date = datetime.now()

    # --- used
    stats_persist.data['electricity_used_tariff_low']['hour']       = stats.electricity_used_tariff_low.hour.get_start_value()
    stats_persist.data['electricity_used_tariff_low']['day']        = stats.electricity_used_tariff_low.day.get_start_value()
    stats_persist.data['electricity_used_tariff_low']['week']       = stats.electricity_used_tariff_low.week.get_start_value() 
    stats_persist.data['electricity_used_tariff_low']['month']      = stats.electricity_used_tariff_low.month.get_start_value()
    stats_persist.data['electricity_used_tariff_low']['year']       = stats.electricity_used_tariff_low.year.get_start_value()

    stats_persist.data['electricity_used_tariff_high']['hour']      = stats.electricity_used_tariff_high.hour.get_start_value()
    stats_persist.data['electricity_used_tariff_high']['day']       = stats.electricity_used_tariff_high.day.get_start_value()
    stats_persist.data['electricity_used_tariff_high']['week']      = stats.electricity_used_tariff_high.week.get_start_value() 
    stats_persist.data['electricity_used_tariff_high']['month']     = stats.electricity_used_tariff_high.month.get_start_value()
    stats_persist.data['electricity_used_tariff_high']['year']      = stats.electricity_used_tariff_high.year.get_start_value()
    # --- returned
    stats_persist.data['electricity_returned_tariff_low']['hour']   = stats.electricity_returned_tariff_low.hour.get_start_value()
    stats_persist.data['electricity_returned_tariff_low']['day']    = stats.electricity_returned_tariff_low.day.get_start_value()
    stats_persist.data['electricity_returned_tariff_low']['week']   = stats.electricity_returned_tariff_low.week.get_start_value() 
    stats_persist.data['electricity_returned_tariff_low']['month']  = stats.electricity_returned_tariff_low.month.get_start_value()
    stats_persist.data['electricity_returned_tariff_low']['year']   = stats.electricity_returned_tariff_low.year.get_start_value()
    
    stats_persist.data['electricity_returned_tariff_high']['hour']  = stats.electricity_returned_tariff_high.hour.get_start_value()
    stats_persist.data['electricity_returned_tariff_high']['day']   = stats.electricity_returned_tariff_high.day.get_start_value()
    stats_persist.data['electricity_returned_tariff_high']['week']  = stats.electricity_returned_tariff_high.week.get_start_value() 
    stats_persist.data['electricity_returned_tariff_high']['month'] = stats.electricity_returned_tariff_high.month.get_start_value()
    stats_persist.data['electricity_returned_tariff_high']['year']  = stats.electricity_returned_tariff_high.year.get_start_value()
    # --- gas
    stats_persist.data['gas_used']['hour']  = stats.gas_used.hour.get_start_value()
    stats_persist.data['gas_used']['day']   = stats.gas_used.day.get_start_value()
    stats_persist.data['gas_used']['week']  = stats.gas_used.week.get_start_value() 
    stats_persist.data['gas_used']['month'] = stats.gas_used.month.get_start_value()
    stats_persist.data['gas_used']['year']  = stats.gas_used.year.get_start_value()

    stats_persist.data['file_date'] = current_date
    
    stats_persist.write_datafile()

# variables
lastrun = datetime(2000, 1, 1)
lastpersist = datetime(2000, 1, 1)

# connect to MQTT broker
client = connect_mqtt()

# DSMR connection
serial_reader = SerialReader(
    device=DSMR_PORT,
    serial_settings=SERIAL_SETTINGS_V5,
    telegram_specification=telegram_specifications.V5
)

# init stats counter
stats_persist = DataPersistence()
stats = ConsumptionStats(stats_persist)

# process incoming DSMR telegrams
for telegram in serial_reader.read_as_object():
    if ((datetime.now() - lastrun).seconds >= REPORT_INTERVAL):
        publish(telegram)

        # persist data every hour
        if (datetime.now().hour != lastpersist.hour):
            persist_datapoints()
            lastpersist = datetime.now()
        
        lastrun = datetime.now()