#!/bin/bash

nc -z "$VIX_HOST" "$VIX_PORT" || exit 1
