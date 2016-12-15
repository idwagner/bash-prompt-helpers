find_git_status() {
  # Based on: http://stackoverflow.com/a/13003854/170413
  local branch
  local git_dirty
  local git_branch

  branch=$(git rev-parse --abbrev-ref HEAD 2> /dev/null)

  if [ -z "$branch" ]; then
    git_prompt=""
    return
  else
    local status=$(git status --porcelain 2> /dev/null)
    local git_dirty
    if [ -n "$status" ]; then
      git_dirty='*'
    else
      git_dirty=''
    fi


    if [ "$branch" == "HEAD" ]; then
      git_branch="detached"
    else
      git_branch="$branch"
    fi

    git_prompt="${bldwht}[${txtrst}git:${txtcyn}${git_branch}${txtred}${git_dirty}${txtrst}${bldwht}]${txtrst}"
  fi

}

status_prompts+=(git_prompt)
PROMPT_COMMAND="find_git_status; $PROMPT_COMMAND"

