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
        "remove": None,
        "set_hostname": "hostnamectl set-hostname $SET_HOSTNAME$",
        "reboot": "reboot",
        "enable_service": "systemctl enable $ENABLE_SERVICE$",
        "disable_service": "systemctl disable $DISABLE_SERVICE$",
        "stop_service": "systemctl stop $STOP_SERVICE$",
        "start_service": "systemctl start $START_SERVICE$",
    }
    __reserved_command_keywords = ['command', 'hide', 'ignore_failure', 'create']


    def __init__(self, remote_connection='', custom_command_map=dict()):
        """
            we expect if you pass a remote_connection, it is an already connected paramiko connection.
            custom_command_map needs to be a dictionary with the key being the command, and the value being a string
            command to run. if the command takes an input, it the input param needs to be formatted with the command name (upper case only), surrounded by $$. For example,
            If your command was "install", your dictionary should look as follows.

            dict(install="some command $ARGS$ $KWARGS$).

        """
        # TODO(Mike): Broken
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
                    'install': 'apt-get install -y $ARGS$ $KWARGS$',
                    'upgrade': 'apt-get upgrade -y',
                    'update': 'apt-get update -y',
                    'remove': 'apt-get remove -y $ARGS$ $KWARGS$'
                }
            },
            {
                'package_manager_location':'/usr/bin/pacman',
                'interface': {
                    "install": "pacman -Sy --noconfirm $ARGS$ $KWARGS$",
                    "update": "pacman -Syy",
                    "upgrade": "pacman -Syu",
                    "remove": "pacman -R $ARGS$"
                }
            },
            {
                'package_manager_location':'/usr/bin/yum',
                'interface': {
                    "install": "yum install -y $ARGS$ $KWARGS$",
                    "update": "yum update -y",
                    "upgrade": "yum upgrade -y",
                    "remove": "yum remove -y $ARGS$"
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

    def __create_command__(self, command, args: str = '', kwargs: str = '', ignore_failure=False) -> Any:
        if command not in self.commands or not self.commands.get(command):
            if not ignore_failure:
                raise NotImplementedError(f'{command} is not implemented')
            else:
                return
        _c = self.commands[command].replace('$ARGS$', args).replace('$KWARGS$', kwargs)
        return _c

    def __run_command__(self, *args, **kwargs) -> Any:
        # TODO(Mike): Consider a slightly better way (read less fugly) of doing this
        '''
        Valid kwargs
        - hide (Boolean)
            Hides output from stdout
        - create (Boolean)
            If passed, does not run the command, just returns the output from __create_command__
        - ignore_failure (Boolean)
            If passed, this will ignore failures (such as the command not being found)
        '''
        ignore_failure = kwargs.get('ignore_failure', False)
        command = kwargs.get('command')
        if not command:
            # TODO(Mike): logging?
            if not ignore_failure:
                print("NO COMMAND SUPPLIED!")
            return
        _args = " ".join([arg for arg in args])
        _kwargs = " ".join([f'--{kword}{"=" if arg else ""}' for kword, arg in kwargs.items() if kword not in DistroAbstractionLayer.__reserved_command_keywords])
        ignore_failure = kwargs.get('ignore_failure', False)
        command = self.__create_command__(command, _args, _kwargs, ignore_failure)
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
