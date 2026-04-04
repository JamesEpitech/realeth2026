#!/bin/bash

PI_USER=epitech
PI_IP=10.105.174.149
REMOTE_SCRIPT="/home/$PI_USER/Desktop/script.sh"
REMOTE_FILE="/home/$PI_USER/Desktop/output.jpg"
LOCAL_FILE="./output.jpg"
LOCAL_SCRIPT="./process.sh"

echo "Running remote script..."
ssh ${PI_USER}@${PI_IP} "bash ${REMOTE_SCRIPT}"

echo "Copying file from Pi..."
scp ${PI_USER}@${PI_IP}:${REMOTE_FILE} ${LOCAL_FILE}

echo "Running local script..."
bash ${LOCAL_SCRIPT} ${LOCAL_FILE}

echo "Done."
