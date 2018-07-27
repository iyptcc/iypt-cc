#!/bin/bash

SP="apps"
if [ $# -ge 1 ]
    then SP=$1
fi

grep -r -o "permission_required(.[^'\"]*" $SP | cut -f 2 -d "(" | cut -c 2-
echo "has_perms-------"
grep -r -o "\.has_perm(.[^'\"]*" $SP | cut -f 2 -d "(" | cut -c 2-