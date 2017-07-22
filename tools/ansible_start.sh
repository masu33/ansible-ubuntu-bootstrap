#!/usr/bin/env bash

############
# PLAYBOOK start for local desktop machine
# ----------
if [ -d ansible ] ; then
    ansible-playbook -K ./ansible/desktop.yml -i ./ansible/localhost $@
elif [ -d ../ansible ] ; then
    ansible-playbook -K ../ansible/desktop.yml -i ../ansible/localhost $@
else
    echo "This should be run from the project folder or the tools folder in it."
fi
