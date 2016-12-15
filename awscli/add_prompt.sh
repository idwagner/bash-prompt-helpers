#!/bin/bash


function aws-login {
  local envreturn
  local runtoken="env PATH=${BASH_PROMPT_HELPERS_DIR}/awscli:$PATH \
    PYTHONPATH=${BASH_PROMPT_HELPERS_DIR}/awscli \
    ${BASH_PROMPT_HELPERS_DIR}/awscli/otptoken.py"

  if [ "$1" == "-l" ]; then
    $runtoken -l
  else
    envreturn=$($runtoken -b $1)
    eval "$envreturn"
  fi


}

function aws-logout {
  local envreturn
  local runtoken="env PATH=${BASH_PROMPT_HELPERS_DIR}/awscli:$PATH \
    PYTHONPATH=${BASH_PROMPT_HELPERS_DIR}/awscli \
    ${BASH_PROMPT_HELPERS_DIR}/awscli/otptoken.py"

  envreturn=$($runtoken -B)
  eval "$envreturn"

}


function aws-token {
  
  if [ "$1" == "-l" ]; then
    ~/bin/winutil/otptoken.py -l
  else
    ~/bin/winutil/otptoken.py -k /Users/iwagner/Library/Keychains/mfa.keychain -t $1
  fi


}

function aws-prompt {
  if [ -n "$AWS_DEFAULT_PROFILE" ]; then
    awsprompt="${bldwht}[${txtrst}aws:${txtcyn}${AWS_DEFAULT_PROFILE}${bldwht}]${txtrst}"
  else
    awsprompt=""
  fi

}

status_prompts+=(awsprompt)
PROMPT_COMMAND="aws-prompt; $PROMPT_COMMAND"
