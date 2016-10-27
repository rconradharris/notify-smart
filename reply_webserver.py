#!/usr/bin/env python
"""
Webserver to serve the reply form.
"""
import ConfigParser
import os
import time

import flask

app = flask.Flask(__name__)

DEFAULT_TRANSCRIPT_CONTEXT = 5
MAX_TRANSCRIPT_CONTEXT = 25
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


@app.route('/reply/<target>', methods=['GET', 'POST'])
def reply(target):
    secret = flask.request.args.get('secret', '')
    if not _validate_secret(secret):
        return flask.abort(404)
    n = int(flask.request.args.get('n', DEFAULT_TRANSCRIPT_CONTEXT))
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
            flask.url_for('reply', target=target, secret=secret, n=n))
    else:
        path = os.path.join(TRANSCRIPTS_DIRECTORY, target)
        if not os.path.exists(path):
            return flask.abort(404)
        with open(path) as f:
            lines = f.read().splitlines()[-n:]
            return flask.render_template(
                'reply.html',
                target=target,
                lines=lines,
                secret=secret,
                n=n,
                default_context=DEFAULT_TRANSCRIPT_CONTEXT,
                more_context=MAX_TRANSCRIPT_CONTEXT)


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
