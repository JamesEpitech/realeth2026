#!/bin/bash

if [ -z "$1" ]; then
    echo "Please provide the path to the image."
    exit 1
fi

xdg-open "$1"
