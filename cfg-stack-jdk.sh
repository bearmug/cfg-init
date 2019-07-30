#!/bin/bash

# ========================================================================
# install custom repo
# ========================================================================
sudo add-apt-repository ppa:openjdk-r/ppa -y
sudo apt-get update

# ========================================================================
# jdk/jre setup
# ========================================================================
sudo apt-get install openjdk-8-jdk -y
sudo apt-get install openjdk-11-jdk -y
sudo apt-get install openjdk-12-jdk -y
sudo apt-get install openjdk-13-jdk -y
# ========================================================================

# ========================================================================
# manipulate by jdk versions
# ========================================================================
update-java-alternatives --list
sudo update-alternatives --config java
java --version
echo "### JDK installation passed OK"