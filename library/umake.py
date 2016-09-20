#!/usr/bin/env python
# coding=utf-8
"""
This module implements an Ansible module to use ubuntu-make.
"""

import json
import subprocess
import os
import yaml

from ansible.module_utils.basic import AnsibleModule
from ansible.errors import AnsibleOptionsError

__author__ = "Sandor Kazi"
__copyright__ = "Copyright 2016, ansible-desktop-bootstrap project"
__credits__ = ["Sandor Kazi"]
__license__ = "GNU GPL3"
__maintainer__ = "Sandor Kazi"
__email__ = "givenname.familyname_AT_gmail.com"
__status__ = "Development"


class AnsibleUMakeModule(object):
    """
    Ansible module to use ubuntu-make.
    """

    CONFIG_LOCATION = '~/.config/umake'
    DEFAULT_LOCATION = '~/.local/share/umake'

    def __location(self, group, component):
        """
        Returns the current location of the framework specified.
        :param group: ubuntu-make command
        :param component: ubuntu-make item
        :return: path where it is currently installed or None
        """
        try:
            return yaml.load(file(os.path.expanduser(self.CONFIG_LOCATION)))['frameworks'][group][component]['path']
        except (IndexError, KeyError, IOError):
            return None

    def __execute(self, command):
        """
        Executes a given command.
        :param command: command to executre
        :return: output produced
        """
        output = subprocess.check_output(
            command,
            shell=True
        ).strip()
        return output

    def main(self, test=None):
        """
        Executes the given module command.
        :type test: dictionary object for testing purposes only
        """

        # Normal (Ansible) call
        if test is None:
            # Module specs
            module = AnsibleModule(
                argument_spec={
                    'executable': {'default': 'umake'},
                    'group': {'required': True},
                    'component': {'required': True},
                    'path': {'default': None},
                    'state': {
                        'choices': ['absent', 'present'],
                        'default': 'present',
                    },
                },
                supports_check_mode=True,
            )

            # Parameters
            params = module.params
            group = params.get('group')
            component = params.get('component')
            path = params.get('path')
            state = params.get('state')

            # Check mode
            check_mode = module.check_mode

        # Test call
        else:
            # Parameters
            params = test.get('params', {})
            group = params.get('group')
            component = params.get('component')
            path = params.get('path')
            state = params.get('state')

            # Check mode
            check_mode = test.get('check_mode')

        # Handling option errors
        if state == 'absent' and path is not None:
            raise AnsibleOptionsError('You can\'t specify a destination dir while removing a framework')

        # Operation logic
        else:
            switch = ' '
            if state == 'absent':
                path = ''
                switch = ' -r'
            elif path is None:
                path = os.path.abspath(
                    os.path.expanduser(
                        '{}/{}/{}'.format(
                            self.DEFAULT_LOCATION,
                            group,
                            component
                        )
                    )
                )

            old_path = self.__location(group, component)

            command = '''yes "no" | umake {group} {component}{switch}{path}'''.format(
                group=group,
                component=component,
                switch=switch,
                path=path,
            )

            changed = (
                (state == 'present' and old_path is None) or
                (state == 'present' and old_path != path) or
                (state == 'absent' and old_path is not None)
            )

            if check_mode:
                pass
            else:
                if changed:
                    self.__execute(command)
                else:
                    pass

        print json.dumps({
            'changed': changed,
            'command': command,
            'old_path': old_path,
            'new_path': path,
        })


if __name__ == '__main__':
    AnsibleUMakeModule().main()