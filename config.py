import ConfigParser
import os

CONFIG_PATH = os.path.expanduser('~/.irssi')
CONFIG_FILE = os.path.join(CONFIG_PATH, 'server-irc-notifier.cfg')


class ConfigError(Exception):
    pass


class ConfigFileNotFound(ConfigError):
    pass


OPTIONS = {
    'notifier': [
        'idle',
        'poll_interval',
        'plugin',
        'title',
    ],
    'reply': [
        'server',
        'secret',
    ],
    'email': [
        'smtp_host',
        'smtp_password',
        'smtp_user',
        'from_email',
        'to_email',
        'debuglevel',
    ],
    'pushover': [
        'user_api_key',
        'app_token',
    ],
    'web': [
        'detect_links',
        'disable_autocapitalize',
        'disable_autocorrect',
        'links_in_new_window',
        'inline_images',
        'inline_videos',
        'poll_interval',
	'video_max_width',
	'video_max_height',
    ]
}


def _read_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    ddict = {}
    cfg = ConfigParser.ConfigParser()
    cfg.read(CONFIG_FILE)
    for section, options in OPTIONS.iteritems():
        for option in options:
            try:
                value = cfg.get(section, option)
            except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
                pass
            else:
                key = ":".join([section, option])
                ddict[key] = value
    return ddict


_CFG_DICT = None


def get(section, option, default=None, type=str):
    global _CFG_DICT

    if _CFG_DICT is None:
        _CFG_DICT = _read_config()

    key = ":".join([section, option])
    try:
        value = _CFG_DICT[key]
    except KeyError:
        return default
    else:
        if type is bool:
            return value.lower() in ('true', 'yes', 'on', '1')
        return type(value)
