==================
smart-irc-notifier
==================


Notify you of IRC messages, both locally via the Mac OS X notification system,
or if you're away from keyboard, via email or SMS.


Requirements
============

* irssi
* fnotify.pl
* terminal-notifier (get from Homebrew)
* GNU screen or tmux on the server (since ``server-irc-notifier`` needs to run
  persistently even when you logout)


Design
======


There are two notification modes, ``terminal-notifier`` and email/SMS.

``terminal-notifier`` notifications are handled client-side by remotely tailing
the ``fnotify`` log file.

Email/SMS notifications are handled server-side so that they will continue to
work even when your laptop is closed.

So that you don't get Email/SMS notifications when you're active at your
computer, client-side code runs on your laptop to  update the server-side file
with your current-idle time.

If the current-idle time exceeds the threshold OR the last-modified age of
that file exceeds the threshold, then an email/SMS notification is generated.

Setup
=====

Client-side
-----------

The client-side (e.g. your laptop), needs run ``client-irc-notifier``. This
script generates terminal-notifications and updates the server-side with your
idle time so that it knows if it should send email/SMS notifications.

The recommended way of running ``client-irc-notifier`` is by using a
``LocalCommand`` post-hook in your ssh config, like so::

    Host irc                                                                                                                                                                                                           
        Hostname <YOUR-IRC-BOUNCER-HOST>
        User <YOUR-USERNAME>
        PermitLocalCommand yes
        LocalCommand ~/bin/client-irc-notifier

Server-side
-----------

First you need to setup ``fnotify.pl``.

Next you need to run create a config file in ``~/.server-irc-notifier.cfg``,
use ``examples`` directory for help.

Finally, you need to copy ``server-irc-notifier`` script to the server (e.g.
your IRC bouncer) and run it in a screen session.
