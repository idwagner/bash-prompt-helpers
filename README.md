# bash-prompt-helpers


## Setup

 1. Clone into $HOME/bin
```sh
cd bash-prompt-helpers/setup
./setup.sh
```
 2. Add to $HOME/.bashrc
```sh
# Bash Prompt Helper
if [ -d $HOME/bin/bash-prompt-helpers ]; then
  export BASH_PROMPT_HELPERS_DIR=$HOME/bin/bash-prompt-helpers
  source $BASH_PROMPT_HELPERS_DIR/setup/baseconfig
  source $BASH_PROMPT_HELPERS_DIR/git-aware-prompt/add_prompt.sh
  source $BASH_PROMPT_HELPERS_DIR/pyenv/add_prompt.sh
fi
```
