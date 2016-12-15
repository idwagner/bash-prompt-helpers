#!/bin/bash


BASH_PROMPT_HELPERS_DIR=$( cd $(dirname $0) && cd .. && pwd -P  )


echo "export BASH_PROMPT_HELPERS_DIR=${BASH_PROMPT_HELPERS_DIR}"
echo "source ${BASH_PROMPT_HELPERS_DIR}/setup/baseconfig"