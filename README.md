#Schallerburg Home Assistant Config

This is my currently running home-assistant configuration.
- It is set up on a Intel NUC with Debian 8.0. home-assistant installation is done through the [Docker image](https://hub.docker.com/r/openhab/openhab/).
- The sensitive variables are given as environment variables through a docker-compose file.
- Deployment of Git checkins is done with Jenkins.


Right now I'm using the following bindings:
* [Pushover notifications](http://pushover.net) and Slack for non-critical messages
* Homematic
* [MySensors](http://www.mysensors.org) - build your own sensors with arduino
* RFXCOM - enables switching of cheap powerplugs like Intertechno
* Zwave -  currently in testing. I only have one Dimmer for now
* XBMC - every TV has one with a central MariaDB on the NAS
* MQTT (attached to the [mosquitto](http://mosquitto.org/) server running on the same box)
* InfluxDB

The mysensors sources can be found at http://github.com/cyberkov/mysensors

##Things in use
| Amount | Item | Description |
|---|---|---|
|13 | HM-CC-RT-DN | Wireless Radiator Thermostat |
| 3 | HM-ES-PMSw1-Pl | Wireless Switch Actuator 1-channel with power metering |
| 2 | HM-ES-TX-WM | Energymeter |
| 2 | HM-LC-Sw1-FM | Switch Actuator |
| 1 | HM-OU-CFM-Pl | MP3 Radio chime with light flash and memory |
| 1 | HM-PB-2-WM55-2 | Wireless Push-Button 2-channel |
| 1 | HM-PBI-4-FM | Wireless Interface 4 channel, flush-mount |
| 2 | HM-RC-Sec4-2 | Wireless remote control |
| 3 | HM-Sec-MDIR-2 | Wireless motion detector |
| 1 | HM-Sec-SC | Wireless Shutter Contact |
| 10 | HM-Sec-SCo | Wireless Door/Window Sensor, optical |
| 1 | HM-Sec-SFA-SM | Radio-controlled alarm siren and flash actuator surface-mount |
| 1 | HM-WDS10-TH-O | Wireless Temperature/Humidity Sensor, outdoor (OTH) |
| 5 | HM-WDS40-TH-I-2 | Wireless Temperature/Humidity Sensor,indoor |

