#!/bin/bash

# Going to need to change this for declarative; essentially, I'll need some layers
# to be able to build a charm and then; so that's a base layer, and a charm decl
# layer and something to work against

set -eux

PATH=/snap/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

nonce=$(pwgen -A 8 1)
model="reactive-$nonce"
JUJU_REPOSITORY=$HOME/$model
LAYER_PATH=$JUJU_REPOSITORY/layers
BUILD_PATH=$JUJU_REPOSITORY/builds

mkdir "$JUJU_REPOSITORY"
mkdir "$LAYER_PATH"
mkdir "$BUILD_PATH"

charm pull-source cs:ghost "$LAYER_PATH"
charm build "$LAYER_PATH/ghost" -o "$JUJU_REPOSITORY"

juju add-model "$model"
juju switch "$model"
wget 'https://api.jujucharms.com/charmstore/v5/ghost/resource/ghost-stable' -O ghost.zip
juju deploy "$BUILD_PATH/ghost" --series=xenial
juju deploy cs:haproxy
juju attach ghost ghost-stable=./ghost.zip
juju add-relation ghost haproxy
juju wait -vw
