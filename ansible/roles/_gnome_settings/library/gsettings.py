#!/usr/bin/env python
# coding=utf-8
"""
This module implements an Ansible module to get access to the gettings application.
"""

import subprocess

from ansible.module_utils.basic import AnsibleModule
from gi.repository import GLib

__author__ = "Sandor Kazi"
__copyright__ = "Copyright 2016, ansible-desktop-bootstrap project"
__credits__ = ["Sandor Kazi"]
__license__ = "GNU GPL3"
__maintainer__ = "Sandor Kazi"
__email__ = "givenname.familyname_AT_gmail.com"
__status__ = "Development"


def isclose(a, b, rel_tol=1e-09, abs_tol=0.0):
    return abs(a-b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)


class AnsibleGSettingModule(object):
    """
    Ansible module to change gsetting parameters for a given user.
    """

    def __init__(self):
        self.user = None
        self.x_user = None
        self.__x_path = None
        self.variant_type = None

    def __del__(self):
        script = '''
            sudo rm -f {file}
        '''.format(
            file=self.xauth_file
        )
        subprocess.check_output(script, shell=True).strip()

    @property
    def x_path(self):
        if self.__x_path:
            return self.__x_path
        else:
            self.__x_path = '~{}/.Xauthority'.format(self.x_user)
            return self.__x_path

    @x_path.setter
    def x_path(self, x_path):
        self.__x_path = x_path

    @property
    def xauth_file(self):
        try:
            return '''/tmp/.Xauthority-{}-{}'''.format(
                self.user,
                self.x_user
            )
        except AttributeError:
            raise AttributeError('X access not granted yet.')

    def __grant(self, user, x_user=None, x_path=None):
        """
        Copies Xauthority

        :param user: username
        :param x_user: user with .Xauthority (optional)
        :param x_path: path of the .Xauthority file (optinal)
        """
        self.user = user
        self.x_user = x_user or user
        self.x_path = x_path
        script = '''
            sudo touch {file}
            sudo chown {user}:{user} {file}
            sudo chmod 0600 {file}
            sudo cp -f {x_path} {file}
        '''.format(
            user=user,
            file=self.xauth_file,
            x_path=self.x_path
        )
        return subprocess.check_output(script, shell=True).strip()

    def __execute(self, command):
        """
        Executes a given command and returns its output.

        :param command: command to execute
        :return: script output
        :rtype: str
        """
        script = '''
            export XAUTHORITY={file}
            export $(dbus-launch)
            sudo -H -s -u {user} {command}
        '''.format(
            file=self.xauth_file,
            user=self.user,
            command=command,
        )
        return subprocess.check_output(script, shell=True).strip()

    def get_range_string(self, schema, path, key):
        """
        Gets the range of the gsetting.

        :param schema: schema name
        :param path: path for relocatable schemas
        :param key: key identifier
        :return: command output
        :rtype: str
        """
        command = "gsettings range {schema}{colon}{path} {key}".format(
            user=self.user,
            schema=schema,
            colon='' if path is None else ':',
            path='' if path is None else path,
            key=key
        )
        output = self.__execute(command).replace('\n', ' ').replace('\r', ' ')
        return output

    def get_param(self, schema, path, key):
        """
        Gets the gsetting value.

        :param schema: schema name
        :param path: path for relocatable schemas
        :param key: key identifier
        :return: command output
        :rtype: MyVariant
        """
        command = "gsettings get {schema}{colon}{path} {key}".format(
            user=self.user,
            schema=schema,
            colon='' if path is None else ':',
            path='' if path is None else path,
            key=key
        )
        output = self.__execute(command)
        return MyVariant(self.variant_type, output)

    def get_default(self, schema, path, key):
        """
        Gets the default gsetting value.

        :param schema: schema name
        :param path: path for relocatable schemas
        :param key: key identifier
        :return: object holding the resulting value
        :rtype: MyVariant
        """
        command = 'XDG_CONFIG_HOME=/nonexistent gsettings get {schema}{colon}{path} {key}'.format(
            user=self.user,
            schema=schema,
            colon='' if path is None else ':',
            path='' if path is None else path,
            key=key
        )
        output = self.__execute(command)
        return MyVariant(self.variant_type, output)

    def set_param(self, schema, path, key, value):
        """
        Sets the gsetting value.

        :param schema: schema name
        :param path: path for relocatable schemas
        :param key: key identifier
        :param value: value as a string
        :return: script output
        :rtype: str
        """
        command = 'gsettings set {schema}{colon}{path} {key} "{value}"'.format(
            schema=schema,
            colon='' if path is None else ':',
            path='' if path is None else path,
            key=key,
            value=str(value).replace('"', r'\"')
        )
        output = self.__execute(command)
        return output

    def reset_param(self, schema, path, key):
        """
        Resets the gsetting value.

        :param schema: schema name
        :param path: path for relocatable schemas
        :param key: key identifier
        :return: script output
        :rtype: str
        """
        command = 'gsettings reset {schema}{colon}{path} {key}'.format(
            schema=schema,
            colon='' if path is None else ':',
            path='' if path is None else path,
            key=key
        )
        output = self.__execute(command)
        return output

    def __setup_class(self, schema, path, key, range_string=None):
        if range_string is None:
            range_string = self.get_range_string(schema, path, key)

        range_type, range_desc = range_string.split(' ', 1)
        if range_type == 'type':
            self.variant_type = range_desc
        elif range_type == 'flags':
            self.variant_type = 'as'
        elif range_type == 'range':
            self.variant_type = range_desc[0]
        elif range_type == 'enum':
            self.variant_type = 's'
        else:
            raise NotImplementedError('Unknown range type: {}'.format(range_string))

    def __use_type(self, value):
        return MyVariant(self.variant_type, value)

    def main(self):
        """
        Executes the given module command.
        """

        # Module specs
        m = AnsibleModule(
            argument_spec={
                'user':      {'required': True},
                'schema':    {'required': True},
                'path':      {'required': False, 'default': None},
                'key':       {'required': True},
                'value':     {'required': False, 'default': None},
                'state':     {'required': False, 'default': 'present', 'choices': ['present', 'absent']},
                'composite': {'required': False, 'default': False, 'choices': [True, False]},
                'range':     {'required': False, 'default': None},
                'x_user':    {'required': False, 'default': None},
                'x_path':    {'required': False, 'default': None},
            },
            supports_check_mode=True,
        )

        # Parameters
        params = m.params
        user = params.get('user')
        schema = params.get('schema')
        path = params.get('path')
        key = params.get('key')
        value = params.get('value')
        state = params.get('state')
        composite = params.get('composite')
        range_string = params.get('range_string')
        x_user = params.get('x_user')
        x_path = params.get('x_path')

        # Check mode
        check_mode = m.check_mode

        # Error check
        if state == 'present' and value is None:
            m.fail_json(
                changed=False,
                msg='The value parameter have to be set with the state "present".'
            )

        self.__grant(user, x_user=x_user, x_path=x_path)
        self.__setup_class(schema, path, key, range_string)

        value_before = self.get_param(schema, path, key)

        if composite:

            if not value_before.is_container():
                m.fail_json(
                    changed=False,
                    msg='Arg `composite` should be used for collections not {}.'.format(self.variant_type)
                )
                raise NotImplementedError()

            else:

                if state == 'present':

                    value_wanted = value_before.present(value)

                elif state == 'absent':

                    value_wanted = value_before.absent(value)

                else:

                    raise NotImplementedError('Unknown state: {}'.format(state))

        else:

            if state == 'present':

                value_wanted = self.__use_type(value)

            elif state == 'absent':

                value_wanted = self.get_default(schema, path, key)

            else:

                raise NotImplementedError('Unknown state: {}'.format(state))

        if check_mode:

            value_after = value_wanted
            changed = not value_before == value_after

        else:

            if value_wanted == value_before:

                changed = False
                value_after = value_before

            elif state == 'absent' and not composite:

                self.reset_param(schema, path, key)
                changed = True
                value_after = self.get_param(schema, path, key)

            else:

                self.set_param(schema, path, key, value_wanted)
                changed = True
                value_after = self.get_param(schema, path, key)

            if value_after != value_wanted:

                m.fail_json(
                    changed=value_after == value_before,
                    user=user,
                    schema=schema,
                    path=path,
                    key=key,
                    value_before=str(value_before),
                    value_after=str(value_after),
                    msg='Unknown error, value change mismatch...'
                )

        m.exit_json(
            changed=changed,
            user=user,
            schema=schema,
            path=path,
            key=key,
            value_before=str(value_before),
            value_after=str(value_after),
        )


class MyVariant(object):

    def __convert(self, value, formats=["{}", "'{}'"]):
        try:
            if formats is None:
                return GLib.Variant.parse(self.type, value, '\n', '\n')
            elif isinstance(formats, (list, tuple)):
                e = Exception()
                for f in formats:
                    try:
                        return GLib.Variant.parse(self.type, f.format(value), '\n', '\n')
                    except GLib.Error as e:
                        pass
                raise e
            else:
                return GLib.Variant.parse(self.type, formats.format(value), '\n', '\n')
        except GLib.Error:
            raise ValueError('''
                Could not parse {} as type {} using formats {}
            '''.format(
                    value,
                    self.type.dup_string(),
                    formats
            ))

    def __init__(self, type_string, value):
        if not GLib.variant_type_string_is_valid(type_string):
            raise ValueError('Invalid type string {}'.format(type_string))

        self.type = GLib.VariantType.new(type_string)
        self.value = self.__convert(value)

    def present(self, item):
        if not isinstance(item, str):
            raise NotImplementedError('Value must be string, not {}.'.format(type(item)))
        item = self.__convert(item, formats=("[{}]", "['{}']"))
        if item[0] not in self.value:
            result = self.__convert(str(list(item) + list(self.value)))
        else:
            result = self.value
        return self.__child(result)

    def absent(self, item):
        if not isinstance(item, str):
            raise NotImplementedError('Value must be string, not {}.'.format(type(item)))
        item = self.__convert(item, formats=("[{}]", "['{}']"))
        if item[0] in self.value:
            result = self.__convert(str([i for i in list(self.value) if i != item[0]]))
        else:
            result = self.value
        return self.__child(result)

    def __eq__(self, other):
        return str(self) == str(other)

    def __ne__(self, other):
        return str(self) != str(other)

    def __repr__(self):
        return str(self.value)

    def is_container(self):
        return self.value.is_container()

    def copy(self):
        return self.__child(self.value)

    def __child(self, value):
        return MyVariant(self.type.dup_string(), str(value))


if __name__ == '__main__':
    AnsibleGSettingModule().main()