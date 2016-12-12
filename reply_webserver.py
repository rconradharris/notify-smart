#!/usr/bin/env python
"""
Webserver to serve the reply form.
"""
import codecs
import os
import re
import string
import time

import flask

import config


app = flask.Flask(__name__, static_url_path='')

ALLOWED_CHARS = '-#_'
REPLY_WAIT = 0.5
REPLY_DIRECTORY = os.path.expanduser('~/.irssi/reply-data')
TRANSCRIPTS_DIRECTORY = os.path.expanduser('~/.irssi/transcripts')

CONFIG_PATH = os.path.expanduser('~/.irssi')
CONFIG_FILE = os.path.join(CONFIG_PATH, 'server-irc-notifier.cfg')

RE_URL = re.compile(r'(^|\s+)http([^\.\s]+\.[^\.\s]*)+[^\.\s]{2,}')
RE_IMAGE_URL = re.compile(r'(^|\s+)http([^\.\s]+\.[^\.\s]*)+[^\.\s]{2,}\.(jpg|jpeg|png|gif|,gifv)')
RE_MSG = re.compile(r'\<(.*)\>\s(.*)')
RE_ACTION = re.compile(r'\s*\*\s*(\w+)\s*(.*)')


class ChannelNotFound(Exception):
    pass


def _validate_secret(value):
    secret = config.get('reply', 'secret')
    if not secret:
        print "error: Must supply 'secret' in config file"
        return False
    return value == secret


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


def perform_text_transforms(text):
    """From http://stackoverflow.com/questions/1727535/replace-urls-in-text-with-links-to-urls"""
    text =  RE_IMAGE_URL.sub(lambda m: '<img src="{url}">'.format(url=m.group(0)), text)
    text =  RE_URL.sub(lambda m: '<a href="{url}">{url}</a>'.format(url=m.group(0)), text)
    return text


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


def write_reply(network, target, reply):
    # Write our reply to reply-data directory which is the communication
    # channel between the webserver and the reply.pl irssi plugin
    if not os.path.exists(REPLY_DIRECTORY):
        os.makedirs(REPLY_DIRECTORY)
    path = os.path.join(REPLY_DIRECTORY, str(time.time()))
    with codecs.open(path, 'w', encoding='utf-8') as f:
        f.write(u'{network} {target} {reply}\n'.format(network=network, target=target, reply=reply))


def format_channel_content(network, target):
    path = os.path.join(TRANSCRIPTS_DIRECTORY, network, target)
    if not os.path.exists(path):
        raise ChannelNotFound
    with codecs.open(path, encoding='utf-8') as f:
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
            authors.add(author)
            text = text.replace('<', '&lt;').replace('>', '&gt;')
            text = perform_text_transforms(text)
            lines.append((author, msg_type, text))

    # Assign (hopefully) unique labels to each author
    author_labels = {}
    num_labels = len(BOOTSTRAP_LABELS)
    for idx, author in enumerate(sorted(authors)):
        author_labels[author] = BOOTSTRAP_LABELS[idx % num_labels]

    return lines, author_labels


@app.route('/ajax/channel/<network>/<target>')
def channel_ajax(network, target):
    secret = flask.request.args.get('secret', '')
    if not _validate_secret(secret):
        return flask.abort(404)
    # Sanitize target to prevent injection attacks
    target = _sanitize(target)
    try:
        lines, author_labels = format_channel_content(network, target)
    except ChannelNotFound:
        return flask.abort(404)
    return flask.render_template(
        '_content.html',
        author_labels=author_labels,
        lines=lines)


@app.route('/channel/<network>/<target>', methods=['GET', 'POST'])
def channel(network, target):
    secret = flask.request.args.get('secret', '')
    if not _validate_secret(secret):
        return flask.abort(404)
    # Sanitize target to prevent injection attacks
    target = _sanitize(target)
    if flask.request.method == 'POST':
        write_reply(network, target, flask.request.form['reply'])

        # Give the reply.pl poller a chance to actually emit the new message
        time.sleep(REPLY_WAIT)

        return flask.redirect(
            flask.url_for('channel', network=network, target=target, secret=secret))
    else:
        try:
            lines, author_labels = format_channel_content(network, target)
        except ChannelNotFound:
            return flask.abort(404)
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
