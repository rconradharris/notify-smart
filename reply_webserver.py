#!/usr/bin/env python
"""
Webserver to serve the reply form.
"""
import os
import time

import flask

app = flask.Flask(__name__)

REPLY_DIRECTORY = os.path.expanduser('~/.irssi/reply-data')

SUCCESS = """\
<html>
    <head>
        <title>Success</title>
        <style>
            body {{ margin-top: 100px; font-size: 72px; }}
        </style>
    </head>
    <body>
        <center>Reply Sent!</center>
    </body>
</html>
"""

FORM = """\
<html>
    <head>
        <title>{target} Reply</title>
        <style>
            body {{ margin-top: 100px; font-size: 72px; }}
            input {{ font-size: 72px; }}
            button {{ width: 300px; font-size: 72px; }}
        </style>
    </head>
    <body>
    <form method="post">
        <center>
        <label>{target}</label>
        <br>
        <br>
        <input type="text" name="reply">
        <br>
        <br>
        <button type="submit">Reply</button>
        </center>
    </form>
    </body>
</html>
"""


@app.route('/success')
def success():
    return SUCCESS.format()


@app.route('/reply/<target>', methods=['GET', 'POST'])
def handle_reply(target):
    if flask.request.method == 'POST':
        reply = flask.request.form['reply']

        # Write our reply to reply-data directory which is the communication
        # channel between the webserver and the reply.pl irssi plugin
        if not os.path.exists(REPLY_DIRECTORY):
            os.makedirs(REPLY_DIRECTORY)
        path = os.path.join(REPLY_DIRECTORY, str(time.time()))
        with open(path, 'w') as f:
            f.write(" ".join([target, reply]) + '\n')

        return flask.redirect(flask.url_for('success'))
    else:
        return FORM.format(target=target)


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
