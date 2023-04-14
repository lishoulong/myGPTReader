#!/bin/bash
GIT_SEQUENCE_EDITOR="sed -i '' '2,\$ s/pick/s/'" git rebase -i $@
