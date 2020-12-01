from helper import CONF, LOG, Error
from ldap3 import Connection, Server
from ldap3 import SIMPLE, SUBTREE, MODIFY_REPLACE
from ldap3.utils.conv import escape_filter_chars
from ldap3.core.exceptions import LDAPBindError, LDAPConstraintViolationResult, \
    LDAPInvalidCredentialsResult, LDAPUserNameIsMandatoryError, \
    LDAPSocketOpenError, LDAPExceptionError

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
