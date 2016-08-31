============
notify-smart
============


Send notifications to email/SMS if computer is idle, otherwise send to
``terminal-notifier``.

Intended to be used with ``irssi`` and ``fnotify.pl`` to notify user of incoming direct
messages in the most appropriate way.


Design
======


There are two notification modes, terminal-notifier and email/SMS.


terminal-notifier notifications are handled client-side by remotely tailing
the fnotify log file.

Email/SMS notifications are handled server-side so that they will continue to
work even when your laptop is closed.

So that you don't get Email/SMS notifications when you're active at your
computer, a client-side piece updates a server-side file with your
current-idle time.

If the current-idle time exceeds the threshold OR the last-modified timestamp
of that file exceeds the threshold, then an email/SMS notification is
generated.


Setup
=====


Server-side
-----------

Set up ``fnotify.pl`` to place direct messages into output file


Client-side
-----------

Use script to login to server and tail output file, pipe this script into
``notify-smart`` to generate the appropriate notifications.

Configure SMTP and idle threshold using ``~/.notify-smart.cfg``
