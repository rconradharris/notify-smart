#!/bin/bash
# http://andy.delcambre.com/2008/12/06/growl-notifications-with-irssi.html
NOTIFIER=/Users/rick/bin/notify-smart

[ -e $NOTIFIER ] || exit 1

# Kill any existly irc-notifier.sh commands
ps -eaf | grep bash.*irc-notifier | grep -v grep | grep -v $$ | awk '{ print $2 }' | xargs kill

# Shell into machine and start reading file
ssh irc -o PermitLocalCommand=no "ps -eaf | grep fnotify | grep -v grep | awk '{ print \$2 }' | xargs kill 2> /dev/null"

(ssh irc -o PermitLocalCommand=no  \
     "tail -n0 -f .irssi/fnotify " | \
   while read message; do                    \
     echo $message | $NOTIFIER 2>&1 > /dev/null; \
   done)&
