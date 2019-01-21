# cfg-init
Bootstrap configurations set to speed-up dev setup process.

## Usage
Just run setup scripts for the tooling you need.

## Content
* Tooling
  * **zsh** and **oh-my-zsh** to use as a shell
  * **tmux** as terminal multiplexor
  * **git** as a default version control system
  * **docker-ce** + **docker-compose**
  * **gradle** as a build tool
* Development stacks
  * **JVM** JDK8 + JDK10 + switching toolkit

## Default configurations
### Git defaults
* located inside **.gitconfig** file
* github user configuration
* shortcuts/aliases introduction to reduce useless keyboard typing

### Gradle defaults
* located under **.gradle/** folder
* speed-up build using:
  * daemon to hung around, expecting next call
  * incubating **configure-on-demand** feature
  * turn on incubating **parallel-build** feature

### JDK defaults
* hasJDK8 and JDK11 under the hood
* JDK11 choosen by default
* switch could be done with **update-java-alternatives**