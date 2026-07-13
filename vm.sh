#!/bin/bash
sudo mount -t vboxsf socialclub /mnt -o uid=$(id -u)
cp /mnt/socialclub-docker.zip .
sudo apt install -y unzip
unzip socialclub-docker.zip -d s
cd s && ./setup.sh