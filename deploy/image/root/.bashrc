# ~/.bashrc: executed by bash(1) for non-login shells.

# Helper functions
git_branch() {
    local branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
    if [ -n "$branch" ]; then
        echo "$branch"
    fi
}

venv_info() {
    if [ -n "$VIRTUAL_ENV" ]; then
        echo "($(basename $VIRTUAL_ENV))"
    fi
}

# Color wrapping function
_c() {
    echo -ne "\[\033[${1}m\]"
}

# Softer colors using ANSI codes
c_user=$(_c "38;5;114")    # Soft green
c_at=$(_c "38;5;146")      # Soft blue-gray
c_host=$(_c "38;5;150")    # Soft yellow-green
c_path=$(_c "38;5;110")    # Soft blue
c_git=$(_c "38;5;178")     # Soft yellow
c_venv=$(_c "38;5;140")    # Soft purple
c_prompt=$(_c "38;5;255")  # Bright white
c_reset=$(_c "0")

# Custom prompt with git branch and venv
PS1="\n\n\
${c_user}\u\
${c_at}@\
${c_host}\h \
${c_path}\w\
${c_git}\$([[ \$(git_branch) != \"\" ]] && echo \" \$(git_branch)\")\
${c_venv}\$([[ \$(venv_info) != \"\" ]] && echo \" \$(venv_info)\")\
\n\
${c_prompt}> \
${c_reset}"

# If this is an xterm set the title to user@host:dir
case "$TERM" in
xterm*|rxvt*)
    PS1="\[\e]0;\u@\h: \w\a\]$PS1"
    ;;
*)
    ;;
esac

# enable color support of ls and also add handy aliases
if [ -x /usr/bin/dircolors ]; then
    test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
    alias ls='ls --color=auto'
    alias grep='grep --color=auto'
    alias fgrep='fgrep --color=auto'
    alias egrep='egrep --color=auto'
fi

# some more ls aliases
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'

# Add an "alert" alias for long running commands.  Use like so:
#   sleep 10; alert
alias alert='notify-send --urgency=low -i "$([ $? = 0 ] && echo terminal || echo error)" "$(history|tail -n1|sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*alert$//'\'')"'

# enable programmable completion features
if ! shopt -oq posix; then
  if [ -f /usr/share/bash-completion/bash_completion ]; then
    . /usr/share/bash-completion/bash_completion
  elif [ -f /etc/bash_completion ]; then
    . /etc/bash_completion
  fi
fi
