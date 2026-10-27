# This is bum - version 0.1-alpha

## What is bum?
bum is a package manager front end for RPM written in [bash](https://www.gnu.org/software/bash/).
It is a "function-alike" clone of [yum](http://yum.baseurl.org/) (YellowDog Updater Modified)
and more or less also [dnf](https://github.com/rpm-software-management/dnf). This is mostly 
written for fun and educational purposes and is not meant to really be used by 
anyone as a replacement for yum as yum is currently, and likely to always be, 
far superior in performance and feature completeness.

## Why on earth?
It started as a joke in #rhel on irc.libre.chat (originally on irc.freenode.net)
and then a small group of us thought it would be fun to actually implement
because there's a lot that we could learn about RPM transactions, dependencies,
and other good information from taking the joke just a little too far. Also,
I'm pretty sure we're going to excercise and hopefully improve our bash-fu along the way.

Ironically none of that happened because life happened and we got busy, but now
we have AI and we can do all sorts of fun nonsense side projects.

What can it do?
---------------
Nothing yet ... :X

The goal is to do everything that yum can but that's a lofty goal so first run
will attempt to implement the following:
    - update/upgrade packages
    - install packages with automatic dependency resolution
    - groupinstall packages with automatic dependency resolution
    - remove packages

## Requirements?

bum requires [bash](https://www.gnu.org/software/bash/) version 5.1 at a minimum so that this code base can utilize
advanced parameter transformation operands. Other than that, the only requirement
is [gnu coreutils](https://www.gnu.org/software/coreutils/).
