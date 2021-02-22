# Distribution Abstraction Layer

A python based abstraction layer that allows you to interact with your system without having to worry about what distribution the system is

-----

Current TODO

- [x] [~~Implement major package manager interaces (APT, YUM, PACMAN)~~](#package-manager-interface)
- [x] [~~Implement systemctl interface~~](#systemctl-interface)
- [x] [~~Add custom commands feature~~](#custom-commands)
- [ ] Add prebuilt package removal
- [ ] Add ability to "sudo up" for commands that require higher level permission
- [ ] Add other language package managers (pip, npm, etc)
- [ ] Add /etc/init.d interface?

## Package Manager Interface

#### Installing Packages

The core of this tool is that it will allow you to install programs without having to worry about the package manager.

**NOTE: Most package managers require the user to have elevated privilages. If the system you are attempting to install on requires this, be sure you are running your script as root or all package manager interfacing will fail**

NOTE: This does rely on the developer/user having the correct package name to install
```python
>>> from distrolayer import DistroAbstractionLayer
>>> dal = DistroAbstractionLayer()
>>> dal.install('chromium-browser')
apt-get install -y chromium-browser
Reading package lists... Done
Building dependency tree
Reading state information... Done
The following NEW packages will be installed:
  chromium-browser
0 upgraded, 1 newly installed, 0 to remove and 18 not upgraded.
Need to get 0 B/48.3 kB of archives.
After this operation, 164 kB of additional disk space will be used.
Preconfiguring packages ...
Selecting previously unselected package chromium-browser.
(Reading database ... 361604 files and directories currently installed.)
Preparing to unpack .../chromium-browser_1%3a85.0.4183.83-0ubuntu0.20.04.2_amd64.deb ...
=> Installing the chromium snap
==> Checking connectivity with the snap store
==> Installing the chromium snap
snap "chromium" is already installed, see 'snap help refresh'
=> Snap installation complete
Unpacking chromium-browser (1:85.0.4183.83-0ubuntu0.20.04.2) ...
Setting up chromium-browser (1:85.0.4183.83-0ubuntu0.20.04.2) ...
Processing triggers for mime-support (3.64ubuntu1) ...
Processing triggers for hicolor-icon-theme (0.17-2) ...
Processing triggers for gnome-menus (3.36.0-1ubuntu1) ...
Processing triggers for desktop-file-utils (0.24-1ubuntu3) ...
>>>
```

Notice that the output is displayed from apt (the package manager that the distro layer interfaced with in the above example).

You can hide this by adding the `hide` parameter to the `install` command

```python
>>> from distrolayer import DistroAbstractionLayer
>>> dal = DistroAbstractionLayer()
>>> dal.install('chromium-browser', hide=True)
>>>
```

You will notice that there is now no output, use the `hide` param if you are looking to install packages/programs behind the scenes without clogging up stdout

### Upgrading Your System
Some package managers (apt for example) have the ability to run full system updates/upgrades. If those features are supported by the system's package manager, you can use the Distro Layer to run them

```python
>>> from distrolayer import DistroAbstractionLayer
>>> dal = DistroAbstractionLayer()
>>> dal.update()
apt-get update -y
Hit:1 http://us.archive.ubuntu.com/ubuntu focal InRelease
Hit:3 http://us.archive.ubuntu.com/ubuntu focal-updates InRelease
Hit:4 http://us.archive.ubuntu.com/ubuntu focal-backports InRelease
Hit:6 http://security.ubuntu.com/ubuntu focal-security InRelease
Reading package lists... Done
>>>
```

Note: All commands support the `hide` parameter described above.

In the event that your package manager/distribution doesn't have system upgrades/updates, this will fail with a `NotImplementedException` being raised.

Note: The parameter `ignore_failure` can be provided which will **NOT** raise an exception and simply just fail to do anything, allowing you to build in things that may not be supported without having to worry about exceptions

### Package Removal

PENDING

### Systemctl Interface

The distro abstraction layer also provides an interface to systemctl, allowing you to manage services within your script.

```python
>>> dal.start_service('nginx')
systemctl start nginx
>>>
```

```python
>>> dal.stop_service('nginx')
systemctl stop nginx
>>> 
```

```python
>>> dal.disable_service('nginx')
systemctl disable nginx
Synchronizing state of nginx.service with SysV service script with /lib/systemd/systemd-sysv-install.
Executing: /lib/systemd/systemd-sysv-install disable nginx
Removed /etc/systemd/system/multi-user.target.wants/nginx.service.
>>> 
```

```python
>>> dal.enable_service('nginx')
systemctl enable nginx
Synchronizing state of nginx.service with SysV service script with /lib/systemd/systemd-sysv-install.
Executing: /lib/systemd/systemd-sysv-install enable nginx
Created symlink /etc/systemd/system/multi-user.target.wants/nginx.service → /lib/systemd/system/nginx.service.
```

**NOTE: Elevated privilages are not _required_ to interact with user level services, however if the script is trying to interact with system level services, it may require elevated privilages. If this is the case, ensure you are running your script as root**

As this layer is meant for scripting, there is no native way to pull the status of a service.

### Custom Commands

In the event that you need the Distro Abstraction Layer to do something that is not natively supported (such as pulling down the status of the nginx service above), that can be done via one of the following mechanisms

- Providing the command on initialization of the dal object
```python
>>> dal = DistroAbstractionLayer(custom_command_map=dict(get_system_status='systemctl status $GET_SYSTEM_STATUS$'))
>>> dal.get_system_status('nginx')
systemctl status nginx
● nginx.service - A high performance web server and a reverse proxy server
     Loaded: loaded (/lib/systemd/system/nginx.service; enabled; vendor preset: enabled)
     Active: active (running) since Sun 0000-00-20 00:00:00 CST; 0min 00s ago
       Docs: man:nginx(8)
    Process: 335268 ExecStartPre=/usr/sbin/nginx -t -q -g daemon on; master_process on; (code=exited, status=>
    Process: 335269 ExecStart=/usr/sbin/nginx -g daemon on; master_process on; (code=exited, status=0/SUCCESS)
   Main PID: 335270 (nginx)
      Tasks: 5 (limit: 9443)
     Memory: 5.1M
     CGroup: /system.slice/nginx.service
             ├─335270 nginx: master process /usr/sbin/nginx -g daemon on; master_process on;
             ├─335271 nginx: worker process
             ├─335272 nginx: worker process
             ├─335273 nginx: worker process
             └─335274 nginx: worker process
>>>
```

Notice that in order for this to work, the parameter **MUST** be defined in the following manner. `$METHOD_NAME_IN_UPPERCASE$`
Provided this is done correctly, you can dynamically add new functionality to your dal instance.

If you need to add the functionality _after_ you have created your dal instance, you can use the `add_command` method

```python
>>> dal.add_command('get_system_status', 'systemctl status $GET_SYSTEM_STATUS$')
>>> dal.get_system_status('nginx')
systemctl status nginx
● nginx.service - A high performance web server and a reverse proxy server
     Loaded: loaded (/lib/systemd/system/nginx.service; enabled; vendor preset: enabled)
     Active: active (running) since Sun 0000-00-20 00:00:00 CST; 0min 00s ago
       Docs: man:nginx(8)
    Process: 335268 ExecStartPre=/usr/sbin/nginx -t -q -g daemon on; master_process on; (code=exited, status=>
    Process: 335269 ExecStart=/usr/sbin/nginx -g daemon on; master_process on; (code=exited, status=0/SUCCESS)
   Main PID: 335270 (nginx)
      Tasks: 5 (limit: 9443)
     Memory: 5.1M
     CGroup: /system.slice/nginx.service
             ├─335270 nginx: master process /usr/sbin/nginx -g daemon on; master_process on;
             ├─335271 nginx: worker process
             ├─335272 nginx: worker process
             ├─335273 nginx: worker process
             └─335274 nginx: worker process
>>>
```