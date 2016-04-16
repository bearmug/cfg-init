# config-common
Config files collection to speed-up new workstation setup

### Usage
* **Case #1** Just clone into HOME location. Works well under Linix/Ubuntu and Windows
* **Case #2** Under Linux clone to any place and run **init.sh**

### Run custom components setup and configuration
* setup custom PPA
* update system
* install **git**, **openjdk**, **gradle**
* copy **git** and **gradle** configuration filesto system locations

### Git default configuration
* located inside **.gitconfig** file
* github user configuration
* shortcuts/aliases introduction to reduce useless keyboard typing

### Gradle default configuration
* located under **.gradle/** folder
* speed-up build using:
  * daemon to hung around, expecting next call
  * incubating **configure-on-demand** feature
  * turn on incubating **parallel-build** feature
