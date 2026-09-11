#!/bin/sh
# The house dash is a spaced hyphen. See CLAUDE.md, § Punctuation.
# Tracked files only: a PR body or a chat reply is nobody's repository.
#
# The two characters are built from their UTF-8 bytes rather than written out.
# A checker that spells its own quarry is a file git grep finds, and this one
# failed on the commit that introduced it: U+2014 and U+2013 must not appear
# literally anywhere below.
set -eu
cd "$(dirname "$0")/.."
em=$(printf '\342\200\224')
en=$(printf '\342\200\223')
if git grep -n -e "$em" -e "$en" -- . ; then
    echo "dash found above; the house dash is a spaced hyphen - like this" >&2
    exit 1
fi
echo "no em or en dashes in tracked files"
