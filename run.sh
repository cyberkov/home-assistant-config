/usr/bin/docker run --rm -t \
    -v /opt/ha/config:/config \
    -v /etc/localtime:/etc/localtime:ro \
    -v /etc/timezone:/etc/timezone:ro \
    -v /etc/letsencrypt:/etc/letsencrypt:ro \
    --device /dev/ttyUSB0 \
    --device /dev/ttyACM0 \
    --net host \
    --name homeassistant homeassistant/home-assistant:latest python -m homeassistant --config /config --log-rotate-days '3'
#    --name homeassistant homeassistant/home-assistant:0.59.2 python -m homeassistant --config /config --log-rotate-days '3'
