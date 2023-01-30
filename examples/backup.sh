#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

RANGE=10

number=$RANDOM
let "number %= $RANGE + 1"

sleep 3s $number
