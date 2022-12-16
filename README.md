# dsmr2mqtt

Reads telegrams from DSMR meter and publishes the output to MQTT.  

### Dependencies
| | |
|-|-|
| dsmr_parser | https://github.com/ndokter/dsmr_parser |
| paho-mqtt   | https://pypi.org/project/paho-mqtt/ |

## Why?

Running Home Assistant as container in a k8s cluster, reading the output of my smart utility meter is challenging if the controller  migrates the container to a node that doesn't have the P1 cable attached to its USB port.

Not owning a '[SlimmeLezer](https://www.zuidwijk.com/product/slimmelezer/)', nor '[Smart Gateway](https://smartgateways.nl/' but just a P1 cable to read out my smart electricity meter, this weekend project was started to have the telegrams read from the meter and pushed to MQTT for Home Assistant to pick up and process. Regardless on which node it is running.

## Docker

### Environment variables

The docker container expects the following environment variables to be set:

|ENV|Description|Default Value|
|-|-|-|
| MQTT_HOST | MQTT broker host | 'mqtt' |
| MQTT_PORT | self explanatory... | 1883 |
| MQTT_CLIENTID | client id used to connect to MQTT broker | 'dsmr2mqtt' |
| DSMR_PORT | port to DSMR serial connection | '/dev/ttyUSB0' |
| DSMR_VERSION | *not supported* | 5 |
| REPORT_INTERVAL | Report to MQTT every x seconds | 5 |

### Start container

```bash
# build the image
docker build . --tag dsmr2mqtt
docker run -e "MQTT_HOST=mqtt.local" -e "REPORT_INTERVAL=15" --device=/dev/ttyUSB0 dsmr2mqtt
```

## Home Assistant

Uses Home Assistant `DSMR Reader` sensor integration.  
Integration details are available in the Home Assistant documentation pages.  
🔗 https://www.home-assistant.io/integrations/dsmr_reader/#difference-with-the-dsmr-integration

## Mapping

The script does the following mapping between the dsmr_reader dictionary and mqtt topics.

| dsmr_parser                            | mqtt_topic                                   | description             |
| -------------------------------------- | -------------------------------------------- | ----------------------- |
| P1_MESSAGE_HEADER                      | dsmr/meter-stats/dsmr_version                | DSMR version            |
| P1_MESSAGE_TIMESTAMP                   | dsmr/reading/timestamp                       | Telegram timestamp      |
| EQUIPMENT_IDENTIFIER                   | dsmr/meter-stats/dsmr_meter_id               | DSMR meter identifier   |
| ELECTRICITY_USED_TARIFF_1              | dsmr/reading/electricity_delivered_1         | Low tariff usage        |
| ELECTRICITY_USED_TARIFF_2              | dsmr/reading/electricity_delivered_2         | High tariff usage       |
| ELECTRICITY_DELIVERED_TARIFF_1         | dsmr/reading/electricity_returned_1          | Low tariff returned     |
| ELECTRICITY_DELIVERED_TARIFF_2         | dsmr/reading/electricity_returned_2          | High tariff returned    |
| ELECTRICITY_ACTIVE_TARIFF              | dsmr/meter-stats/electricity_tariff          | Electricity tariff      |
| CURRENT_ELECTRICITY_USAGE              | dsmr/reading/electricity_currently_delivered | Current power usage     |
| CURRENT_ELECTRICITY_DELIVERY           | dsmr/reading/electricity_currently_returned  | Current power return    |
| LONG_POWER_FAILURE_COUNT               | dsmr/meter-stats/power_failure_count         | Power failure count     |
| VOLTAGE_SAG_L1_COUNT                   | dsmr/meter-stats/voltage_sag_count_l1        | Voltage sag L1          |
| VOLTAGE_SAG_L2_COUNT                   | dsmr/meter-stats/voltage_sag_count_l2        | Voltage sag L2          |
| VOLTAGE_SAG_L3_COUNT                   | dsmr/meter-stats/voltage_sag_count_l3        | Voltage sag L3          |
| VOLTAGE_SWELL_L1_COUNT                 | dsmr/meter-stats/voltage_swell_count_l1      | Voltage swell L1        |
| VOLTAGE_SWELL_L2_COUNT                 | dsmr/meter-stats/voltage_swell_count_l2      | Voltage swell L2        |
| VOLTAGE_SWELL_L3_COUNT                 | dsmr/meter-stats/voltage_swell_count_l3      | Voltage swell L3        |
| TEXT_MESSAGE_CODE                      |
| TEXT_MESSAGE                           |
| DEVICE_TYPE                            | dsmr/meter-stats/dsmr_meter_type             | DSMR meter type         |
| INSTANTANEOUS_ACTIVE_POWER_L1_POSITIVE | dsmr/reading/phase_currently_delivered_l1    | Current power usage L1  |
| INSTANTANEOUS_ACTIVE_POWER_L2_POSITIVE | dsmr/reading/phase_currently_delivered_l2    | Current power usage L2  |
| INSTANTANEOUS_ACTIVE_POWER_L3_POSITIVE | dsmr/reading/phase_currently_delivered_l3    | Current power usage L3  |
| INSTANTANEOUS_ACTIVE_POWER_L1_NEGATIVE | dsmr/reading/phase_currently_returned_l1     | Current power return L1 |
| INSTANTANEOUS_ACTIVE_POWER_L2_NEGATIVE | dsmr/reading/phase_currently_returned_l2     | Current power return L2 |
| INSTANTANEOUS_ACTIVE_POWER_L3_NEGATIVE | dsmr/reading/phase_currently_returned_l3     | Current power return L3 |
| EQUIPMENT_IDENTIFIER_GAS               | dsmr/meter-stats/gas_meter_id                | Gas meter identifier    |
| HOURLY_GAS_METER_READING               | dsmr/consumption/gas/read_at                 | Gas meter read          |
| INSTANTANEOUS_VOLTAGE_L1               | dsmr/reading/phase_voltage_l1                | Current voltage L1      |
| INSTANTANEOUS_CURRENT_L1               | dsmr/reading/phase_power_current_l1          | Phase power current L1  |
| INSTANTANEOUS_VOLTAGE_L2               | dsmr/reading/phase_voltage_l2                | Current voltage L2      |
| INSTANTANEOUS_CURRENT_L2               | dsmr/reading/phase_power_current_l2          | Phase power current L2  |
| INSTANTANEOUS_VOLTAGE_L3               | dsmr/reading/phase_voltage_l3                | Current voltage L3      |
| INSTANTANEOUS_CURRENT_L3               | dsmr/reading/phase_power_current_l3          | Phase power current L3  |
