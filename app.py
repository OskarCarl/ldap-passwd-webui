#!/usr/bin/env python3

import bottle
from bottle import get, post, static_file, request, response, route, template
from bottle import SimpleTemplate
from configparser import ConfigParser
from ldap3 import Connection, Server
from ldap3 import SIMPLE, SUBTREE, MODIFY_REPLACE
from ldap3.utils.conv import escape_filter_chars
from ldap3.core.exceptions import LDAPBindError, LDAPConstraintViolationResult, \
    LDAPInvalidCredentialsResult, LDAPUserNameIsMandatoryError, \
    LDAPSocketOpenError, LDAPExceptionError
import logging
import os
from os import environ, path
# from base64 import b64encode
# from imghdr import what


BASE_DIR = path.dirname(__file__)
LOG = logging.getLogger(__name__)
LOG_FORMAT = '%(asctime)s %(levelname)s: %(message)s'
VERSION = '2.1.0-dev'


@get('/')
def get_index():
    return index_tpl()


@post('/')
def post_index():
    form = request.forms.getunicode

    def error(msg, username=''):
        return index_tpl(username=username, alerts=[('error', msg)])

    try:
        info = load_info(form('username'), form('password'))
    except Error as e:
        LOG.warning("Unsuccessful attempt to load info for {}: {}".format(form('username'), e))
        return error(str(e))

    return edit_tpl(
        username=info['uid'][0],
        sn=info['sn'][0],
        givenName=info['givenName'][0],
        mail=info['mail'][0]
        # jpegPhoto='data:image/{};base64,{}'.format(
        #     what('', info['jpegPhoto'][0]),
        #     b64encode(info['jpegPhoto'][0]).decode('utf-8')
        #     )
        )


@post('/edit')
def post_edit():
    form = request.forms.getunicode

    def error(msg):
        return template('done', alerts=[('error', msg)])

    if not form('old-password'):
        return error("Password is required!")

    if form('new-password') != form('confirm-password'):
        return error("New password doesn't match the confirmation!")

    if len(form('new-password')) > 0 and len(form('new-password')) < 8:
        return error("New password must be at least 8 characters long!")

    try:
        change_info(
            form('username'),
            {
                'sn': form('sn'),
                'givenName': form('givenName'),
                'cn': '{} {}'.format(form('givenName'), form('sn')),
                'mail': form('mail')
            },
            form('old-password'),
            form('new-password')
            )
    except Error as e:
        LOG.warning("Unsuccessful attempt to change password for {}: {}".format(form('username'), e))
        return error(str(e))

    LOG.info("Information successfully changed for: {}".format(form('username')))

    return template('done', alerts=[('success', 'Information changed successfully!')])


@route('/static/<filename>', name='static')
def serve_static(filename):
    return static_file(filename, root=path.join(BASE_DIR, 'static'))

@route('/favicon.ico')
def serve_favicon():
    return static_file('favicon.ico', root=path.join(BASE_DIR, 'static'))

def index_tpl(**kwargs):
    return template('index', **kwargs)

def edit_tpl(**kwargs):
    return template('edit', **kwargs)

def connect_ldap(conf, **kwargs):
    server = Server(host=conf['host'],
                    port=conf.getint('port', None),
                    use_ssl=conf.getboolean('use_ssl', False),
                    connect_timeout=5)

    return Connection(server, raise_exceptions=True, **kwargs)


def get_dn(conf, username):
    return 'uid={},{}'.format(username, conf['base'])


def load_info(username, password):
    conf = CONF['ldap']
    user_dn = get_dn(conf, username)

    try:
        # Note: raises LDAPUserNameIsMandatoryError when user_dn is None.
        with connect_ldap(conf, authentication=SIMPLE, user=user_dn, password=password) as c:
            c.bind()
            c.search(
                search_base=conf['base'],
                search_filter=conf['search_filter'].format(uid=escape_filter_chars(username)),
                attributes=['uid', 'sn', 'givenName', 'cn', 'mail']
            )
            return c.response[0]['attributes']

    except (LDAPBindError, LDAPInvalidCredentialsResult, LDAPUserNameIsMandatoryError):
        raise Error('Username or password is incorrect!')


def change_info(username, base_info, old_pass, new_pass=''):
    conf = CONF['ldap']
    LOG.info("Changing info for: {}".format(username))
    try:
        change_base_info(conf, username, base_info, old_pass)
        if len(new_pass) > 0:
            change_password(conf, username, old_pass, new_pass)

    except (LDAPBindError, LDAPInvalidCredentialsResult, LDAPUserNameIsMandatoryError):
        raise Error('Username or password is incorrect!')

    except LDAPConstraintViolationResult as e:
        # Extract useful part of the error message (for Samba 4 / AD).
        msg = e.message.split('check_password_restrictions: ')[-1].capitalize()
        raise Error(msg)

    except LDAPSocketOpenError as e:
        LOG.error('{}: {!s}'.format(e.__class__.__name__, e))
        raise Error('Unable to connect to the remote server.')

    except LDAPExceptionError as e:
        LOG.error('{}: {!s}'.format(e.__class__.__name__, e))
        raise Error('Encountered an unexpected error while communicating with the remote server.')


def change_base_info(conf, username, base_info, password):
    user_dn = get_dn(conf, username)

    # Note: raises LDAPUserNameIsMandatoryError when user_dn is None.
    with connect_ldap(conf, authentication=SIMPLE, user=user_dn, password=password) as c:
        c.bind()
        c.modify(
            user_dn,
            {
                'givenName': [(MODIFY_REPLACE, [base_info['givenName']])],
                'sn':   [(MODIFY_REPLACE, [base_info['sn']])],
                'cn':   [(MODIFY_REPLACE, [base_info['cn']])],
                'mail': [(MODIFY_REPLACE, [base_info['mail']])]
            }
            )


def change_password(conf, username, old_pass, new_pass):
    user_dn = get_dn(conf, username)

    # Note: raises LDAPUserNameIsMandatoryError when user_dn is None.
    with connect_ldap(conf, authentication=SIMPLE, user=user_dn, password=old_pass) as c:
        c.bind()
        c.extend.standard.modify_password(user_dn, old_pass, new_pass)


def read_config():
    config = ConfigParser()
    config.read([path.join(BASE_DIR, 'settings.ini'), os.getenv('CONF_FILE', '')])

    return config


class Error(Exception):
    pass


if environ.get('DEBUG'):
    bottle.debug(True)

# Set up logging.
logging.basicConfig(format=LOG_FORMAT)
LOG.setLevel(logging.INFO)
LOG.info("Starting ldap-passwd-webui %s".format(VERSION))

CONF = read_config()

bottle.TEMPLATE_PATH = ["{}/templates".format(BASE_DIR)]

# Set default attributes to pass into templates.
SimpleTemplate.defaults = dict(CONF['html'])
SimpleTemplate.defaults['url'] = bottle.url


# Run bottle internal server when invoked directly (mainly for development).
if __name__ == '__main__':
    bottle.run(**CONF['server'])
# Run bottle in application mode (in production under uWSGI server).
else:
    application = bottle.default_app()
