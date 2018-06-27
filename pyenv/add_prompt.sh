

function venv-prompt {
  # set -x
  local cwd=`pwd -P`
  local parent="${cwd}/."  # Add dummy that will get popped off
  local count=0
  local -a checkdirs
  # Check $count parent dir names, and if $parent/bin/activate
  # exists (and not already in the virtualenv) activate it

  while [ $count -lt 3 ]; do
    parent=$(dirname "$parent")
    checkdirs+=( $parent ${parent}/.venv )
    count=$(( $count+1 ))
  done

  for checkdir in ${checkdirs[@]}; do
    if [ -n "$checkdir" ] && [ -f "$checkdir/bin/activate" ] \
        && [ "$checkdir" != "$VIRTUAL_ENV" ]; then
      source "$checkdir/bin/activate"
      break
    fi
  done

  _deactivate_check=$(echo $VIRTUAL_ENV | sed 's,/.venv,,g')
  if [ -n "${_deactivate_check}" ] && [[ ! "$cwd" =~ ${_deactivate_check} ]]; then
    deactivate
  fi

  if [ -n "$VIRTUAL_ENV" ]; then
    _base=$(basename $VIRTUAL_ENV)
    if [[ "${_base}" =~ ^\. ]]; then
      _base=$(basename $(dirname $VIRTUAL_ENV))
    fi
    venvprompt="${bldwht}[${txtrst}py:${txtcyn}${_base}${bldwht}]${txtrst}"
  else
    venvprompt=""
  fi

}

status_prompts+=(venvprompt)
PROMPT_COMMAND="venv-prompt; $PROMPT_COMMAND"
