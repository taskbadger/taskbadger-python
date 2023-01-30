#!/bin/bash

#set -o errexit
#set -o pipefail
#set -o nounset
#set -o functrace

function usage {
  echo "./$(basename $0) -h --> shows usage"
}

optstring=":h"

while getopts ${optstring} arg; do
  case ${arg} in
    h)
      echo "showing usage!"
      usage
      ;;
    :)
      echo "$0: Must supply an argument to -$OPTARG." >&2
      exit 1
      ;;
    ?)
      echo "Invalid option: -${OPTARG}."
      exit 2
      ;;
  esac
done

shift "$((OPTIND - 1))"
echo "remaining args: $*"

exit
ORG=
PROJECT=
TOKEN=
EMAIL=

NAME=database-backup

function callApi {
  url="https://taskbadger.net/api/$ORG/$PROJECT/tasks/"
  data="$1"
  if (( $# == 2 )); then
    url="${url}${2}/"
  fi

  taskId=$(curl -X POST -s "$url" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d "$data" | jq -r '.id'
  )
  echo $taskId
}

read -rd '' data <<EOF
{
  "name": "${NAME}", "status": "processing",
  "data": {"host": "${HOSTNAME}" },
  "actions": [{
    "integration": "email",
    "trigger": "error",
    "config": {"to": "${EMAIL}"}
  }]
}
EOF
taskId=$(callApi "$data")

echo $taskId
bash $@

if [ "$?" -eq 0 ]; then
  callApi '{"status": "success", "value": 100}' $taskId
else
  callApi '{"status": "error", "data": {"code": "$?"}' $taskId
fi
