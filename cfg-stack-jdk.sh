#!/bin/bash

# ========================================================================
# install custom repo
# ========================================================================
sudo add-apt-repository ppa:openjdk-r/ppa -y
sudo apt-get update

# ========================================================================
# jdk/jre setup
# ========================================================================
sudo apt-get install openjdk-8-jre openjdk-8-jdk -y
sudo apt-get install openjdk-11-jre openjdk-11-jdk -y

# ========================================================================
# manipulate by jdk versions
# ========================================================================
update-java-alternatives --list
sudo update-java-alternatives --set /usr/lib/jvm/java-1.11.0-openjdk-amd64
java --version

echo "### JDK installation passed OK"