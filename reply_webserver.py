#!/usr/bin/env python
"""
Webserver to serve the reply form.
"""
import codecs
import os
import re
import shutil
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
RE_YOUTUBE_URL = re.compile(r'(^|\s+)http[s]*://www.youtube.com/watch\?v=(\w+)')

DEFAULT_POLL_INTERVAL = 5.0


class ChannelNotFound(Exception):
    pass


class TranscriptNotFound(Exception):
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
                if os.path.isdir(path):
                    targets.append((network, target))
    return targets


@app.route('/channels')
def channels():
    secret = flask.request.args.get('secret', '')
    if not _validate_secret(secret):
        return flask.abort(404)
    return flask.render_template(
        'channels.html', targets=_targets(), secret=secret)


def linkify(url):
    if config.get('web', 'links_in_new_window', default=True, type=bool):
        return '<a href="{url}" target="_blank">{url}</a>'.format(url=url)
    else:
        return '<a href="{url}">{url}</a>'.format(url=url)

def imageify(url):
    return '<img src="{url}">'.format(url=url)


def youtubeify(video_id):
    width = config.get('web', 'video_max_width', default=560, type=int)
    height = config.get('web', 'video_max_height', default=315, type=int)
    return '<iframe width="{width}" height="{height}" src="https://www.youtube.com/embed/{video_id}"></iframe>'.format(video_id=video_id, width=width, height=height)


def perform_text_transforms(text):
    """From http://stackoverflow.com/questions/1727535/replace-urls-in-text-with-links-to-urls"""
    text = text.replace('<', '&lt;').replace('>', '&gt;')
    if config.get('web', 'inline_videos', default=True, type=bool):
        text =  RE_YOUTUBE_URL.sub(lambda m: youtubeify(m.group(2)), text)
    if config.get('web', 'inline_images', default=True, type=bool):
        text =  RE_IMAGE_URL.sub(lambda m: imageify(m.group(0)), text)
    if config.get('web', 'detect_links', default=True, type=bool):
        text =  RE_URL.sub(lambda m: linkify(m.group(0)), text)
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
    shutil.rmtree(path)
    return flask.redirect(flask.url_for('channels', targets=_targets(), secret=secret))


def write_reply(network, target, reply):
    # Write our reply to reply-data directory which is the communication
    # channel between the webserver and the reply.pl irssi plugin
    if not os.path.exists(REPLY_DIRECTORY):
        os.makedirs(REPLY_DIRECTORY)
    path = os.path.join(REPLY_DIRECTORY, str(time.time()))
    with codecs.open(path, 'w', encoding='utf-8') as f:
        f.write(u'{network} {target} {reply}\n'.format(network=network, target=target, reply=reply))


def parse_message(line):
    author, text = line.split('>', 1)
    author = author.replace('<', '').strip()
    text = text.strip()
    return author, text


def parse_action(line):
    parts = line.strip().split()
    # part[0] is the '*' character
    author = parts[1]
    text = parts[2]
    return author, text


def get_target_path(network, target):
    target_path = os.path.join(TRANSCRIPTS_DIRECTORY, network, target)
    if not os.path.exists(target_path):
        raise ChannelNotFound
    return target_path


def get_transcript_path(network, target, date):
    target_path = get_target_path(network, target)
    path = os.path.join(target_path, date)
    if not os.path.exists(path):
        raise TranscriptNotFound
    return path


def format_channel_content(path, after=None):
    with codecs.open(path, encoding='utf-8') as f:
        # Format lines
        lines = []
        authors = set()
        prev_author = None
        for line_id, line in enumerate(f.read().splitlines()):
            line = line.strip()
            if line.startswith('<'):
                author, text = parse_message(line)
                msg_type = 'msg'
            elif line.startswith('*'):
                author, text = parse_action(line)
                msg_type = 'action'
            elif line.startswith('!'):
                line = line[1:].strip()
                author, text = parse_message(line)
                msg_type = 'hilight'
            else:
                raise Exception("Unknown line format '{}'".format(line))
            authors.add(author)
            text = perform_text_transforms(text)
            if prev_author == author:
                author = None
            if after is None or line_id > after:
                lines.append((line_id, author, msg_type, text))

    # Assign (hopefully) unique labels to each author
    author_labels = {}
    num_labels = len(BOOTSTRAP_LABELS)
    for idx, author in enumerate(sorted(authors)):
        author_labels[author] = BOOTSTRAP_LABELS[idx % num_labels]

    return lines, author_labels


def validate_channel_request(target):
    secret = flask.request.args.get('secret', '')
    if not _validate_secret(secret):
        return flask.abort(404)
    # Sanitize target to prevent injection attacks
    return secret, _sanitize(target)


@app.route('/ajax/channel/<network>/<target>', methods=['GET', 'POST'])
def channel_ajax(network, target):
    secret, target = validate_channel_request(target)

    if flask.request.method == 'POST':
        write_reply(network, target, flask.request.form['reply'])
        return ''

    after = flask.request.args.get('after')
    if after is not None:
        after = int(after)
    try:
        path = get_transcript_path(network, target, 'current')
    except (ChannelNotFound, TranscriptNotFound):
        return flask.abort(404)
    lines, author_labels = format_channel_content(path, after=after)
    return flask.render_template(
        '_content.html',
        author_labels=author_labels,
        lines=lines)


@app.route('/channel/<network>/<target>', methods=['GET', 'POST'])
def channel(network, target):
    secret, target = validate_channel_request(target)

    if flask.request.method == 'POST':
        write_reply(network, target, flask.request.form['reply'])

        # Give the reply.pl poller a chance to actually emit the new message
        time.sleep(REPLY_WAIT)

        return flask.redirect(
            flask.url_for('channel', network=network, target=target, secret=secret))

    try:
        path = get_transcript_path(network, target, 'current')
    except (ChannelNotFound, TranscriptNotFound):
        return flask.abort(404)

    lines, author_labels = format_channel_content(path)
    poll_interval_ms = 1000 * config.get('web', 'poll_interval',
                                         default=DEFAULT_POLL_INTERVAL,
                                         type=float)
    return flask.render_template(
        'channel.html',
        archive=False,
        network=network,
        target=target,
        author_labels=author_labels,
        lines=lines,
        secret=secret,
        targets=_targets(),
        video_max_width=config.get('web', 'video_max_width', default=560, type=int),
        video_max_height=config.get('web', 'video_max_height', default=315, type=int),
        disable_autocorrect=config.get('web', 'disable_autocorrect'),
        disable_autocapitalize=config.get('web', 'disable_autocapitalize'),
        poll_interval_ms=poll_interval_ms
        )


@app.route('/channel/<network>/<target>/settings')
def channel_settings(network, target):
    secret, target = validate_channel_request(target)
    try:
        path = get_target_path(network, target)
    except (ChannelNotFound):
        return flask.abort(404)

    exclude = ['current']
    try:
        transcript_path = get_transcript_path(network, target, 'current')
    except TranscriptNotFound:
        pass
    else:
        # Exclude the file the current symlink points to
        current_dst = os.path.basename(os.readlink(transcript_path))
        exclude.append(current_dst)

    archives = [p for p in os.listdir(path) if p not in exclude]
    archives.sort(reverse=True)

    return flask.render_template(
        'channel_settings.html',
        archives=archives,
        network=network,
        target=target,
        secret=secret,
        targets=_targets(),
        )


@app.route('/channel/<network>/<target>/<date>')
def channel_archive(network, target, date):
    secret, target = validate_channel_request(target)
    try:
        path = get_transcript_path(network, target, date)
    except (ChannelNotFound, TranscriptNotFound):
        return flask.abort(404)
    lines, author_labels = format_channel_content(path)

    return flask.render_template(
        'channel.html',
        archive=True,
        date=date,
        network=network,
        target=target,
        author_labels=author_labels,
        lines=lines,
        secret=secret,
        targets=_targets(),
        video_max_width=config.get('web', 'video_max_width', default=560, type=int),
        video_max_height=config.get('web', 'video_max_height', default=315, type=int)
        )


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
