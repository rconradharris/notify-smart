============
notify-smart
============


Send notifications to email/SMS if computer is idle, otherwise send to
terminal-notifier.

Intended to be used with irssi and fnotify to notify user of incoming direct
messages in the most appropriate way.


Setup
=====


Server-side
-----------

Set up fnotify.pl to place direct messages into output file


Client-side
-----------

Use script to login to server and tail output file, pipe this script into
smart-notifier to generate the appropriate notifications.

Configure SMTP and idle threshold using ``~/.notify-smart.cfg``
