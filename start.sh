#!/bin/bash
if [ ! -f /data/marketa.db ]; then
    cp marketa.db /data/marketa.db
    echo "Database copied from repo to volume"
fi
python main.py
