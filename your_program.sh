#!/bin/sh

# Get the absolute path of the directory containing this shell script
DIR="$( cd "$( dirname "$0" )" && pwd )"

# Add that directory to the Python path so it can always find the 'app' module
export PYTHONPATH="$DIR"

# Run the program
exec python3 -m app.main "$@"