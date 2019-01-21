# cfg-init
Bootstrap configurations set to speed-up dev setup process.

## Usage
Just run init.sh and go through the dialog.

## Content
* Environment tooling
  * *zsh* and *oh-my-zsh* to use as a shell
  * *micro* to use as a prefferred editor
  * *tmux* as terminal multiplexor
  * *git* as a default version control system
* DEV toolings
  * Docker
    * docker-ce + docker-compose
  * JVM
    * JDK8 + JDK10 + switching toolkit
    * gradle installation

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
* switch could be done with supplied scripts