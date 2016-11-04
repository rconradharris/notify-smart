#!/usr/bin/env python
"""
Webserver to serve the reply form.
"""
import ConfigParser
import os
import re
import string
import time

import flask

app = flask.Flask(__name__, static_url_path='')

ALLOWED_CHARS = '-#_'
REPLY_WAIT = 0.5
REPLY_DIRECTORY = os.path.expanduser('~/.irssi/reply-data')
TRANSCRIPTS_DIRECTORY = os.path.expanduser('~/.irssi/transcripts')

CONFIG_PATH = os.path.expanduser('~/.irssi')
CONFIG_FILE = os.path.join(CONFIG_PATH, 'server-irc-notifier.cfg')

RE_URL = re.compile(r'http([^\.\s]+\.[^\.\s]*)+[^\.\s]{2,}')
RE_MSG = re.compile(r'\<(.*)\>\s(.*)')
RE_ACTION = re.compile(r'\s*\*\s*(\w+)\s*(.*)')

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
    targets = []
    for network in  os.listdir(TRANSCRIPTS_DIRECTORY):
        path = os.path.join(TRANSCRIPTS_DIRECTORY, network)
        if os.path.isdir(path):
            for target in os.listdir(path):
                targets.append((network, target))
    return targets


@app.route('/channels')
def channels():
    secret = flask.request.args.get('secret', '')
    if not _validate_secret(secret):
        return flask.abort(404)
    return flask.render_template(
        'channels.html', targets=_targets(), secret=secret)


def linkify(line):
    """From http://stackoverflow.com/questions/1727535/replace-urls-in-text-with-links-to-urls"""
    return RE_URL.sub(lambda m: '<a href="{url}">{url}</a>'.format(url=m.group(0)), line) if line else ''


BOOTSTRAP_LABELS = map(lambda x: x.lower(), "Default Primary Success Info Warning Danger".split())


@app.route('/channel/<network>/<target>/close', methods=['POST'])
def close_channel(network, target):
    secret = flask.request.args.get('secret', '')
    if not _validate_secret(secret):
        return flask.abort(404)
    path = os.path.join(TRANSCRIPTS_DIRECTORY, network, target)
    if not os.path.exists(path):
        return flask.abort(404)
    os.unlink(path)
    return flask.redirect(flask.url_for('channels', targets=_targets(), secret=secret))


@app.route('/channel/<network>/<target>', methods=['GET', 'POST'])
def channel(network, target):
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
            f.write(" ".join([network, target, reply]) + '\n')

        # Give the reply.pl poller a chance to actually emit the new message
        time.sleep(REPLY_WAIT)

        return flask.redirect(
            flask.url_for('channel', network=network, target=target, secret=secret))
    else:
        path = os.path.join(TRANSCRIPTS_DIRECTORY, network, target)
        if not os.path.exists(path):
            return flask.abort(404)
        with open(path) as f:
            # Format lines
            lines = []
            authors = set()
            for line in f.read().splitlines():
                line = line.strip()
                if line.startswith('<'):
                    author, text = RE_MSG.match(line).groups()
                    msg_type = 'msg'
                elif line.startswith('*'):
                    author, text = RE_ACTION.match(line).groups()
                    msg_type = 'action'
                elif line.startswith('!'):
                    line = line[1:].strip()
                    author, text = RE_MSG.match(line).groups()
                    msg_type = 'hilight'
                else:
                    raise Exception("Unknown line format '{}'".format(line))
                author = author.strip()
                text = linkify(text)
                authors.add(author)
                lines.append((author, msg_type, text))

            # Assign (hopefully) unique labels to each author
            author_labels = {}
            num_labels = len(BOOTSTRAP_LABELS)
            for idx, author in enumerate(sorted(authors)):
                author_labels[author] = BOOTSTRAP_LABELS[idx % num_labels]

            return flask.render_template(
                'channel.html',
                network=network,
                target=target,
                author_labels=author_labels,
                lines=lines,
                secret=secret,
				targets=_targets())


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
