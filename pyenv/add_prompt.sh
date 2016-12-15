

function venv-prompt {
  #set -x
  local cwd=`pwd`
  local parent="${cwd}/."  # Add dummy that will get popped off
  local count=0

  # Check $count parent dir names, and if $parent/bin/activate
  # exists (and not already in the virtualenv) activate it
  while [ $count -lt 3 ]; do
    parent=$(dirname $parent)

    if [ -n "$parent" ] && [ -f $parent/bin/activate ] \
        && [ "$parent" != "$VIRTUAL_ENV" ]; then
      source $parent/bin/activate
      count=999
    fi
    count=$(( $count+1 ))
  done

  
  if [ -n "${VIRTUAL_ENV}" ] && [[ ! "$cwd" =~ ${VIRTUAL_ENV} ]]; then
    deactivate
  fi

  if [ -n "$VIRTUAL_ENV" ]; then

    venvprompt="${bldwht}[${txtrst}py:${txtcyn}$(basename $VIRTUAL_ENV)${bldwht}]${txtrst}"
  else
    venvprompt=""
  fi

}

status_prompts+=(venvprompt)
PROMPT_COMMAND="venv-prompt; $PROMPT_COMMAND"

