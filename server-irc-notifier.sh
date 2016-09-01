#!/usr/bin/env python
"""
Send a email/SMS notification if the user is idle on their laptop.

Idle is determine by the user running a program on their laptop
(irc-notifier.sh) which constantly sends idle-time back to the server where
this script runs.

This script doesn't exit and is intended to be run inside a GNU screen
session window

Configure using ~/.notify-smart.cfg
"""

import ConfigParser
from email.mime.text import MIMEText
import os
import smtplib
import subprocess
import sys
import time


CONFIG_FILE = os.path.expanduser('~/.notify-smart.cfg')
IDLE_TIME_PATH = '.irssi/idle-time'
FNOTIFY_LOG = '.irssi/fnotify'


def is_idle(cfg):
    """Determine whether the user is considered idle.

    A script on the users laptop is updating the local `idle-time` file.

    If the `idle-time` file doesn't exist, then the user is by definition idle
    (because they haven't logged in to create it).

    If the `idle-time` file is present, we two possibilities:

        1) File hasn't been touched in a while: This means the laptop is no
        longer active (from our perspective) and we should consider the user
        idle.

        2) The file has been touched recently: In this case the laptop is
        active (since we're receiving idle reports), however the user might
        not be at their desk. So in this case, use the contents of `idle-time`
        file to determine what to do.
    """
    idle_threshold  = cfg.getint('general', 'idle')
    assert idle_threshold is not None, 'idle is required in config'
    if not os.path.exists(IDLE_TIME_PATH):
        return True
    mtime = os.path.getmtime(IDLE_TIME_PATH)
    if mtime > idle_threshold:
        return True
    with open(IDLE_TIME_PATH) as f:
        idle_time = float(f.read().strip())
    return idle_time > idle_threshold


def notify_email(cfg, body):
    host = cfg.get('email', 'smtp_host')
    assert host
    server = smtp_connect(host,
                          cfg.get('email', 'smtp_user'),
                          cfg.get('email', 'smtp_password'))
    try:
        smtp_send(server,
                  cfg.get('email', 'from_email'),
                  cfg.get('email', 'to_email'),
                  body=body)
    finally:
        smtp_close(server)


def smtp_connect(host, user, password):
    server = smtplib.SMTP(host)
    server.ehlo()
    server.starttls()
    server.login(user, password)
    return server


def smtp_close(server):
    server.quit()


def smtp_send(server, from_email, to_email, body=None, subject=None):
    msg = MIMEText(body)
    if subject:
        msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email
    server.sendmail(from_email, [to_email], msg.as_string())


def get_fnotify_last_line():
    with open(FNOTIFY_LOG) as f:
        return f.read().splitlines()[-1]


def main():
    cfg = ConfigParser.ConfigParser()
    cfg.read(CONFIG_FILE)

    last_fnotify_mtime =  os.path.getmtime(FNOTIFY_LOG)

    while True:
        cur_fnotify_mtime =  os.path.getmtime(FNOTIFY_LOG)

        if cur_fnotify_mtime == last_fnotify_mtime:
            continue    # No update, continue

        last_fnotify_mtime = cur_fnotify_mtime

        last_line = get_fnotify_last_line()
        if is_idle(cfg):
            notify_email(cfg, last_line)
        time.sleep(1.0)


if __name__ == '__main__':
    main()
