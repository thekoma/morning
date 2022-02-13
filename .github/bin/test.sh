#!/bin/bash
docker-compose -f docker-compose.yml up -d
try=0
echo "🚦 Starting checks."
while [ $try -lt 12 ]; do
  health=$(docker inspect "$(docker-compose ps -q morning)" |jq '.[0] | .State.Health.Status'|sed 's/"//g')
  if [ "${health}" == "healthy" ]; then
    echo "🌞 Morning is healthy! Great Job!"
    exit_var=0
    break
  else
    ((try++))
    docker-compose ps
    docker-compose logs morning
    echo "⏳ Not ready. Sleeping"
    sleep 5
  fi
  echo "🚨 Test failed"
  exit_var=1
done
docker-compose down -v -t 1 --remove-orphans
exit $exit_var