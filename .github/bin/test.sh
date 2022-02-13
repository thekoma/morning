#!/bin/bash
if ! type -p executable_name &>/dev/null; then
  sudo apt-get update; sudo apt-get install -y jq
fi
docker-compose -f docker-compose.yml up -d
try=0
while [ $try -lt 12 ]; do
  health=$(docker inspect "$(docker-compose ps -q morning)" |jq '.[0] | .State.Health.Status'|sed 's/"//g')
  if [ "${health}" == "healthy" ]; then
    echo "Morning is healthy! Great Job!"
    exit_var=0
    break
  else
    ((try++))
    sleep 5
    docker-compose ps
    docker-compose logs morning
  fi
  echo "Something is wrong. Check it out."
  exit_var=1
done
docker-compore down -v -t 1 --remove-orphans
exit $exit_var