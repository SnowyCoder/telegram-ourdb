#!/bin/bash

# Script for local testing

# Change directory to the script location
cd "$(dirname "$0")"

# Load the .env variables and extend them to subprocesses
source .env
export $(cut -d= -f1 .env)

# Start the bot
