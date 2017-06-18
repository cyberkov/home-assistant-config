#!/bin/bash
if [ ! -e "secrets.yaml" ]; then
  ln -s secrets_redacted.yaml secrets.yaml
fi
docker run -v "${PWD}:/config" homeassistant/home-assistant:latest /bin/sh -c "python -m homeassistant --config /config --script check_config"
