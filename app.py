#!/usr/bin/env python3

import bottle
from bottle import get, post, static_file, request, response, route, template
from bottle import SimpleTemplate
from helper import BASE_DIR, CONF, LOG, Error
from ldap import connect_ldap, load_info, change_info
from os import environ, path
# from base64 import b64encode
# from imghdr import what


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


##
# Entry point
##

if environ.get('DEBUG'):
    bottle.debug(True)

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
