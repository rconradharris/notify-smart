#!/usr/bin/env python
"""
Webserver to serve the reply form.
"""
import ConfigParser
import os
import string
import time

import flask

app = flask.Flask(__name__)

ALLOWED_CHARS = '-#_'
REPLY_WAIT = 0.5
REPLY_DIRECTORY = os.path.expanduser('~/.irssi/reply-data')
TRANSCRIPTS_DIRECTORY = os.path.expanduser('~/.irssi/transcripts')

CONFIG_PATH = os.path.expanduser('~/.irssi')
CONFIG_FILE = os.path.join(CONFIG_PATH, 'server-irc-notifier.cfg')

CFG = None

def _validate_secret(secret):
    global CFG
    if not CFG:
        if not os.path.exists(CONFIG_FILE):
            print "error: required config file not found at '{}'".format(CONFIG_FILE)
            return False
        CFG = ConfigParser.ConfigParser()
        CFG.read(CONFIG_FILE)
    try:
        cfg_secret = CFG.get('reply', 'secret')
    except ConfigParser.NoOptionError:
        print "Must supply secret in config file at '{}'".format(CONFIG_FILE)
        return False
    return secret == cfg_secret


SANITIZE_TABLE = None

def _sanitize(s):
    global SANITIZE_TABLE
    if not SANITIZE_TABLE:
        whitelist = string.letters + string.digits + ALLOWED_CHARS
        SANITIZE_TABLE = string.maketrans(whitelist, ' ' * len(whitelist))
    return str(s).translate(None, SANITIZE_TABLE)


def _targets():
    return os.listdir(TRANSCRIPTS_DIRECTORY)


@app.route('/channels')
def channels():
    secret = flask.request.args.get('secret', '')
    if not _validate_secret(secret):
        return flask.abort(404)
    return flask.render_template(
        'channels.html', targets=_targets(), secret=secret)


@app.route('/channel/<target>', methods=['GET', 'POST'])
def channel(target):
    secret = flask.request.args.get('secret', '')
    if not _validate_secret(secret):
        return flask.abort(404)
    # Sanitize target to prevent injection attacks
    target = _sanitize(target)
    if flask.request.method == 'POST':
        # Write our reply to reply-data directory which is the communication
        # channel between the webserver and the reply.pl irssi plugin
        if not os.path.exists(REPLY_DIRECTORY):
            os.makedirs(REPLY_DIRECTORY)
        path = os.path.join(REPLY_DIRECTORY, str(time.time()))
        with open(path, 'w') as f:
            reply = flask.request.form['reply']
            f.write(" ".join([target, reply]) + '\n')

        # Give the reply.pl poller a chance to actually emit the new message
        time.sleep(REPLY_WAIT)

        return flask.redirect(
            flask.url_for('channel', target=target, secret=secret))
    else:
        path = os.path.join(TRANSCRIPTS_DIRECTORY, target)
        if not os.path.exists(path):
            return flask.abort(404)
        with open(path) as f:
            lines = f.read().splitlines()
            return flask.render_template(
                'channel.html',
                target=target,
                lines=lines,
                secret=secret,
				targets=_targets())


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
