#!/bin/bash

docker-compose -f docker-compose.yml up -d
try=0
retry=12
exit_var=1
sleep=5
echo "🚦 Starting checks."
while [ $try -lt $retry ]; do
  health=$(docker inspect "$(docker-compose ps -q morning)" |jq '.[0] | .State.Health.Status'|sed 's/"//g')
  echo "🔍 Checking...[${try}/${retry}]"
  if [ "${health}" == "healthy" ]; then
    exit_var=0
    break
  else
    ((try++))
    docker-compose ps
    docker-compose logs morning
    echo "⏳ Not ready. Sleeping $sleep seconds. "
    sleep $sleep

  fi
done

if [ $exit_var == 1 ]; then
  echo "🚨 Test failed"
else
  echo "🌞 Morning is healthy! Great Job!"
fi

docker-compose down -v -t 1 --remove-orphans
exit $exit_var