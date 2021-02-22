#!/usr/bin/env python3

from pathlib import Path
from shlex import split as Split
from subprocess import run as Run, PIPE
from typing import Any

class DistroAbstractionLayer:
    _command_map = {
        "install": None,
        "upgrade": None,
        "update": None,
        "set_hostname": "hostnamectl set-hostname $SET_HOSTNAME$",
        "reboot": "reboot",
        "enable_service": "systemctl enable $ENABLE_SERVICE$",
        "disable_service": "systemctl disable $DISABLE_SERVICE$",
        "stop_service": "systemctl stop $STOP_SERVICE$",
        "start_service": "systemctl start $START_SERVICE$",
    }

    def __init__(self, remote_connection='', custom_command_map=dict()):
        """
            we expect if you pass a remote_connection, it is an already connected paramiko connection.
            custom_command_map needs to be a dictionary with the key being the command, and the value being a string
            command to run. if the command takes an input, it the input param needs to be formatted with the command name (upper case only), surrounded by $$. For example,
            If your command was "install", your dictionary should look as follows.

            dict(install="some command $INSTALL$).

            Currently, we only allow for single param custom commands. If you need more, you will have to build it yourself.
        """
        self._methods = [method for method in dir(DistroAbstractionLayer) if callable(getattr(DistroAbstractionLayer, method)) and not method.startswith('__')]
        self._connection = remote_connection
        self.distro = self.__get_distro__()
        self.commands = self.__init_command_map__(custom_command_map)

    def __get_distro__(self):
        command = ['/usr/bin/cat', '/etc/issue']
        if Path('/etc/redhat-release').exists():
            command = ['/usr/bin/cat', '/etc/redhat-release']
        return Run(command, stdout=PIPE).stdout.decode('utf-8').rstrip().replace('\\n', '').replace('\\l', '')

    def __init_command_map__(self, custom_commands: dict):
        # package manager locations
        # /usr/bin/apt (apt package manager)
        # /usr/bin/pacman (pacman)
        # /usr/bin/yum (yum)
        package_manager_locations = [
            {
                'package_manager_location': '/usr/bin/apt',
                'interface': {
                    'install': 'apt-get install -y $INSTALL$',
                    'upgrade': 'apt-get upgrade -y',
                    'update': 'apt-get update -y',
                }
            },
            {
                'package_manager_location':'/usr/bin/pacman',
                'interface': {
                    "install": "pacman -Sy $INSTALL$ --noconfirm",
                    "update": "pacman -Syy",
                    "upgrade": None,
                }
            },
            {
                'package_manager_location':'/usr/bin/yum',
                'interface': {
                    "install": "yum install $INSTALL$ -y",
                    "update": "yum update -y",
                    "upgrade": None,
                }
            }
        ]

        commands = self._command_map.copy()
        for pm in package_manager_locations:
            location = pm['package_manager_location']
            if Path(location).exists():
                for key, command in pm['interface'].items():
                    commands[key] = command
                break
        
        if not commands['install']:
            # TODO(Mike): Logging
            print('Unable to find package manager')
        
        for key, value in custom_commands.items():
            # This allows custom commands to overwrite preset commands
            commands[key] = value

        return commands

    def get_groups_on_server(self):
        command = 'cat /etc/group'
        output = None
        if self._connection:
            output = self._connection.run(command, hide=True).stdout
        else:
            output = Run(Split(command), stdout=PIPE).stdout.decode('utf-8')
        return [group.split(':')[0] for group in output.split('\n')]

    def encrypt_password(self, password):
        input_command = f'''python3 -c "from crypt import crypt; import re; print(crypt('{password}').replace('$',r'$'))"'''
        if self._connection:
            return self._connection.run(input_command, hide=True).stdout.rstrip()
        else:
            return Run(Split(input_command), stdout=PIPE).stdout.decode('utf-8').rstrip()

    def get_valid_commands(self):
        return [key for key,value in self.commands.items() if value]

    def show_command(self, command):
        run_command = self.commands.get(command, None)
        if not run_command:
            print(f'Unable to find command: {command}. Please check get_valid_commands() and ensure the provided command is part of the dal')

    def add_command(self, command, run_command):
        '''
        This allows you to dynamically add a new command to the current distro command set. This will also allow you to override commands that 
        are already set. Make sure your param (limit 1) is the name of the command, in all caps, wrapped with $. An example below
        
        apt-get install -y $INSTALL$
        '''
        self.commands[command] = run_command

    def get_program_path(self, program):
        input_command = f'which {program}'
        if self._connection:
            command = lambda input_command: self._connection.run(input_command, hide=True).stdout
        else:
            command = lambda input_command: Run(Split(input_command), stdout=PIPE).stdout.decode('utf-8')
        output = command(input_command)
        if output.startswith('which:'):
            output = ''
        else:
            output = output.rstrip()
        return output if output != '' else None

    def __create_command__(self, command, param) -> Any:
        if command not in self.commands or not self.commands.get(command):
            raise NotImplementedError(f'{command} is not implemented')
        _c = self.commands[command]
        if param:
            _c = _c.replace(f'${command.upper()}$', param)
        return _c

    def __run_command__(self, *args, **kwargs) -> Any:
        '''
        Valid kwargs
        - param (String)
            Parameter(s) to pass to __create_command__. This should be a string
        - hide (Boolean)
            Hides output from stdout
        - create (Boolean)
            If passed, does not run the command, just returns the output from __create_command__
        '''
        command = kwargs['command']
        if not command:
            print('No command found')
            return
        param = kwargs.get('param', ' '.join([arg for arg in args]))
        command = self.__create_command__(command, param)
        if not command:
            print('No command found')
            return
        if kwargs.get('create'):
            return command
        hide = kwargs.get('hide', False)

        if not hide:
            print(f'{command}')
        command = Split(command)
        run_args = dict()
        if hide:
            run_args['capture_output'] = True
        
        result = Run(command, **run_args)
        if result.stderr:
            print(result.stderr.decode('utf-8'))

    def __getattribute__(self, name: str) -> Any:
        try:
            return super().__getattribute__(name)
        except AttributeError:
            return lambda *args, **kwargs: self.__run_command__(*args, **kwargs, command=name)
