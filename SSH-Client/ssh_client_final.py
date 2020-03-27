import os
import sys
import json


class Connection:
    def __init__(self, head_dir, name, host, user, password):
        self.head_dir = head_dir
        self.name = ''
        self.set_name(name)  # TODO proper way of doing this
        self.host = host
        self.user = user
        self.password = password

    def set_name(self, name):
        if name is '' or name.isdigit() or '/' in name or name == 'root' or ' ' in name:
            raise ClientErr.InvalidNameError
        elif not self.head_dir.is_valid_name(name):
            pass
        else:
            self.name = name

    def set_user(self, user):
        if user != '':
            self.user = user

    def set_host(self, hostname):
        if hostname != '':
            self.host = hostname

    def set_pass(self, password):
        if password != '':
            self.password = password if 'del pass' not in password else None


class SecureShell(Connection):
    def __init__(self, head_dir, name, host, user, password=None):
        super().__init__(head_dir, name, host, user, password)

    def con_cmd(self):
        command = 'ssh {}@{}'.format(self.user, self.host)
        command = 'sshpass -p {} '.format(self.password) + command if self.password is not None else command
        return command

    def to_dict(self):
        return {self.name: [self.name, self.host, self.user, self.password]}

    def __str__(self):
        return '(s) ' + self.name

    def __repr__(self):
        return 'S ' + self.name + ' ' + self.user + ' ' + self.host + ' ' + self.password


class Telnet(Connection):
    def __init__(self, head_dir, name, host, user=None, password=None, port=''):
        super().__init__(head_dir, name, host, user, password)
        self.port = port

    def con_cmd(self):
        command = '{} {}'.format(self.host, self.port)
        command = 'telnet -l {} '.format(self.user) + command if self.user is not None else 'telnet ' + command
        command = '(sleep 3; echo {}) | '.format(self.password) + command if self.password is not None else command
        return command

    def to_dict(self):
        return {self.name: [self.name, self.host, self.user, self.password, self.port]}

    def set_port(self, port):
        if port != '':
            self.port = port if 'del user' not in port else None

    def set_user(self, user):
        if user != '':
            self.user = user if 'del user' not in user else None

    def __str__(self):
        return '(t) ' + self.name

    def __repr__(self):
        return 'T ' + self.name + ' ' + self.user + ' ' + self.host + ' ' + self.password + ' ' + self.port


class Directory:
    def __init__(self, head_dir, dir_name):
        self.dir = []
        self.head_dir = head_dir
        self.name = dir_name

    def set_name(self, name):
        if self.is_valid_name(name):
            self.name = name

    def is_valid_name(self, name):
        for entry in self.dir:
            if entry.name == name:
                raise ClientErr.ExistingNameError(name)
        return True

    def add_entry(self, new_entry):
        self.dir.append(new_entry)
        self.dir.sort(key=str)

    def rem_entry(self, ent_key):
        if type(ent_key) is Directory or isinstance(ent_key, Connection):
            self.dir.remove(ent_key)
        else:
            self.dir.remove(self[ent_key])

    def to_dict(self):
        dir_dict = {self.name: {}}
        for entry in self.dir:
            dir_dict[self.name].update(entry.to_dict())
        return dir_dict

    def __str__(self):
        return '(D) ' + self.name

    def __repr__(self):
        return self.name + ' head: ' + str(self.head_dir)

    def __len__(self):
        return len(self.dir)

    def __getitem__(self, key, default=None):  # accepts int index or str key
        if type(key) is not int and key.isdigit():  # int key
            if 0 <= int(key) < len(self):
                return self.dir[int(key)]
            else:
                return default
        else:  # str key
            for i in range(len(self)):
                if self.dir[i].name == key:
                    key = i
                    break
            if type(key) is int:
                return self.dir[key]
            else:
                return default


class Client:
    def __init__(self):
        self.root = Directory(None, 'root')
        self.pwd = '/root'
        self.cur_dir = self.root

    def list_dir(self):
        if len(self.cur_dir) > 0:
            index = 0
            for entry in self.cur_dir:
                print(str(index) + ': ' + str(entry))
                index += 1
        else:
            print('Empty directory')

    def connect(self, path, connection_type):
        path, entry = self.get_path_entry(path, return_connection=True)
        if isinstance(entry, connection_type):
            command = entry.con_cmd()
            # os.system(command)  # Testing
            print(command)  # Testing
            input('Press Enter: ')
            # os.system('clear')  # Testing
        else:
            print('Requested entry is not a valid connection session given the command')

    def make_dir(self, dir_name):
        new_dir = Directory(self.cur_dir, dir_name)
        self.cur_dir.add_entry(new_dir)

    def make_ssh(self, ssh_name, user, host, password):
        new_ssh = SecureShell(self.cur_dir, ssh_name, host, user, password)
        self.cur_dir.add_entry(new_ssh)

    def make_tel(self, tel_name, host, port, user, password):
        new_tel = Telnet(self.cur_dir, tel_name, host, user, password, port)
        self.cur_dir.add_entry(new_tel)

    def rem_entry(self, path, rm_directory=False):
        rem_path, rem_entry = self.get_path_entry(path, return_connection=True)
        if not rm_directory and type(rem_entry) is Directory:
            print('Cannot remove a directory without the -r/--recursive flag')
            return
        rem_entry.head_dir.rem_entry(rem_entry)

    def to_dir(self, path):
        new_path, new_dir = self.get_path_entry(path)
        self.pwd = new_path
        self.cur_dir = new_dir

    def info(self, path):
        info_path, info_entry = self.get_path_entry(path, return_connection=True)
        if type(info_entry) is Directory:
            print('\tDirectory Name: ' + info_entry.name)
            print('\tThis directory contains ' + str(len(info_entry)) + ' entries')
        elif type(info_entry) is SecureShell:
            print('\tSecureShell Name: ' + info_entry.name)
            print('\tSecureShell Username: ' + info_entry.user)
            print('\tSecureShell Host: ' + info_entry.host)
            print('\tSecureShell Password: ' + str(info_entry.password))
        elif type(info_entry) is Telnet:
            print('\tTelnet Name: ' + info_entry.name)
            print('\tTelnet Host: ' + info_entry.host)
            print('\tTelnet Port: ' + str(info_entry.port))
            print('\tTelnet Username: ' + str(info_entry.user))
            print('\tTelnet Password: ' + str(info_entry.password))

    def edit(self, path):
        edit_path, edit_entry = self.get_path_entry(path, return_connection=True)
        if type(edit_entry) is Directory:
            print('Edit the attributes of this Directory. Press [enter] to skip changing the current attribute')
            new_name = input('Current Directory name is \'' + edit_entry.name + '\' change it to >> ')
            edit_entry.set_name(new_name) if new_name != '' and \
                (edit_entry.name == new_name or edit_entry.head_dir.is_valid_name(new_name)) else None
        elif type(edit_entry) is SecureShell:
            print('Edit the attributes of this SecureShell. Press [enter] to skip changing the current attribute')
            new_name = input('Current SecureShell name is \'' + edit_entry.name + '\' change it to >> ')
            edit_entry.set_name(new_name) if new_name != '' and \
                (edit_entry.name == new_name or edit_entry.head_dir.is_valid_name(new_name)) else None
            new_user = input('Current SecureShell username is \'' + edit_entry.user + '\' change it to >> ')
            edit_entry.set_user(new_user) if new_user != '' else None
            new_host = input('Current SecureShell host is \'' + edit_entry.host + '\' change it to >> ')
            edit_entry.set_host(new_host) if new_host != '' else None
            print('Here you can change or delete your password. To delete your password, enter \'del pass\'')
            if edit_entry.password is None:
                new_pass = input('Current SecureShell has no password. Add one as >> ')
            else:
                new_pass = input('Current SecureShell password is \'' + edit_entry.password + '\' change it to >> ')
            edit_entry.set_pass(new_pass) if new_pass != '' else None
        elif type(edit_entry) is Telnet:
            print('Edit the attributes of this Telnet. Press [enter] to skip changing the current attribute')
            new_name = input('Current Telnet name is \'' + edit_entry.name + '\' change it to >> ')
            edit_entry.set_name(new_name) if new_name != '' and \
                (edit_entry.name == new_name or edit_entry.head_dir.is_valid_name(new_name)) else None
            new_host = input('Current Telnet host is \'' + edit_entry.host + '\' change it to >> ')
            edit_entry.set_host(new_host) if new_host != '' else None
            print('Here you can change or delete your custom port. To delete your port, enter \'del port\'')
            if edit_entry.port is None:
                new_port = input('Current Telnet has the default port. Add one as >> ')
            else:
                new_port = input('Current Telnet port is \'' + edit_entry.port + '\' change it to >> ')
            edit_entry.set_port(new_port) if new_port != '' else None
            print('Here you can change or delete your username. To delete your username, enter \'del user\'')
            if edit_entry.user is None:
                new_user = input('Current Telnet has no username. Add one as >> ')
            else:
                new_user = input('Current Telnet username is \'' + edit_entry.user + '\' change it to >> ')
            edit_entry.set_user(new_user) if new_user != '' else None
            print('Here you can change or delete your password. To delete your password, enter \'del pass\'')
            if edit_entry.password is None:
                new_pass = input('Current Telnet has no password. Add one as >> ')
            else:
                new_pass = input('Current Telnet password is \'' + edit_entry.password + '\' change it to >> ')
            edit_entry.set_pass(new_pass) if new_pass != '' else None

    def move(self, source_paths, destination_path):
        source_items = []
        for source_path in source_paths:
            path, entry = self.get_path_entry(source_path, return_connection=True)
            source_items.append(entry)
        try:  # move mode
            full_path, destination_entry = self.get_path_entry(destination_path)  # get destination
            for entry in source_items:
                if type(entry) is Directory and not self.is_valid_move(entry, destination_entry):
                    continue
                else:
                    destination_entry.is_valid_name(entry.name)
                    source_head = entry.head_dir  # save off source
                    entry.head_dir = destination_entry  # update head directory
                    source_head.rem_entry(entry)  # remove entry from source
                    destination_entry.add_entry(entry)  # add entry to directory
        except ClientErr.InvalidPathError:  # rename mode
            if len(source_items) != 1:
                print('Cannot rename more than one entry at a time')
            else:
                entry = source_items[0]
                full_path = destination_path.split('/')
                key = full_path[-1]
                full_path, destination_entry = self.get_path_entry('/'.join(full_path[:-1]))
                destination_entry.is_valid_name(key)
                source_head = entry.head_dir  # save off source
                entry.head_dir = destination_entry  # update head directory
                source_head.rem_entry(entry)  # remove entry from source
                destination_entry.add_entry(entry)  # add entry to directory
                entry.name = key  # update name

    def is_valid_move(self, src_entry, dest_directory):
        if src_entry is dest_directory:
            print('Directory cannot be moved into itself')
            return False
        else:
            return self.check_sub_dir(src_entry, dest_directory)

    def check_sub_dir(self, source_entry, dest_directory):
        for entry in source_entry.dir:
            if entry is dest_directory:
                print('Directory cannot be moved into a subdirectory of itself')
                return False
            elif type(entry) is Directory:
                self.check_sub_dir(entry, dest_directory)
        return True

    def get_path_entry(self, original_path, return_connection=False):
        if original_path[0] == '/':  # full declaration
            path = original_path
        elif original_path[:2] == '~/':  # home declaration
            path = original_path.replace('~', '/root')
        else:  # contextualized declaration
            path = self.pwd + '/' + original_path
        if path[:5] != '/root':
            raise ClientErr.InvalidPathError(1, original_path)
        work_dir = self.root
        path_str = '/root'
        path = path.replace('/root', '').split('/')
        for key in path[1:]:
            if isinstance(work_dir, Connection):
                raise ClientErr.InvalidPathError(4, original_path)
            elif key == '.' or key == '':  # present directory notation
                continue
            elif key == '..':  # traverse upwards
                if work_dir.name == 'root':
                    raise ClientErr.InvalidPathError(5, original_path)
                else:
                    path_str = '/'.join(path_str.rsplit('/', 1)[:1])
                    work_dir = work_dir.head_dir
            elif key:  # traverse downwards
                work_dir = work_dir[key]
                if work_dir is None:
                    raise ClientErr.InvalidPathError(2, original_path)
                key = work_dir.name
                path_str += '/' + key
                if type(work_dir) is Directory:
                    continue
                elif return_connection:
                    continue
                else:
                    raise ClientErr.InvalidPathError(3, original_path)
            else:
                print('Invalid path key')  # should never be reached
        return path_str, work_dir

    def save_file(self):
        with open('.ssh_client.txt', 'w') as file:
            client_dict = self.root.to_dict()
            json.dump(client_dict, file, indent=4)
            file.close()

    def load_file(self):
        try:
            with open('.ssh_client.txt') as file:
                client_dict = json.load(file)
                self.load_dict(self.root, client_dict.get('root'))
                file.close()
        except json.decoder.JSONDecodeError:
            print('Save file is malformed, please fix or delete')
            print('JSON decoder error, incorrect syntax')
            sys.exit(1)

    def load_dict(self, cur_dir, cur_dict):
        if cur_dict is None:
            print('Save file is malformed, please fix or delete')
            print('Non-translatable dictionary in save file')
            sys.exit(1)
        for name in cur_dict.keys():
            if type(cur_dict[name]) is dict:  # Directory saved as dict
                new_dir = Directory(cur_dir, name)
                cur_dir.add_entry(new_dir)
                self.load_dict(new_dir, cur_dict[name])
            elif type(cur_dict[name]) is list:  # Connection saved as list
                if len(cur_dict[name]) == 4:  # SecureShell saved as list len = 4
                    ssh_list = cur_dict[name]
                    new_ssh = SecureShell(cur_dir, ssh_list[0], ssh_list[1], ssh_list[2], ssh_list[3])
                    cur_dir.add_entry(new_ssh)
                elif len(cur_dict[name]) == 5:  # Telnet saved as list len = 5
                    tel_list = cur_dict[name]
                    new_tel = Telnet(cur_dir, tel_list[0], tel_list[1], tel_list[2], tel_list[3], tel_list[4])
                    cur_dir.add_entry(new_tel)
                else:
                    print('Malformed connection at key ' + name)
                    sys.exit(1)
            else:
                print('Malformed json file entry at key ' + name)
                sys.exit(1)


class CmdSwitch:
    @staticmethod
    def client_help(cur_cli, usr_inp):
        print('This is an SSH/Telnet command line client designed to quickly connect and store connections')
        print('\nThe available commands are meant to mirror the commands and usage of Linux commands')
        print('\tThe following commands are available:\n')
        cmd_help = ClientErr.CommandHelp()
        for cmd_key in cmd_help.help_dict.keys():
            print(cmd_key + ':    ' + cmd_help.help_dict[cmd_key] + '\n')

    @staticmethod
    def client_ll(cur_cli, usr_inp):
        if len(usr_inp) > 1 and ('-h' in usr_inp[1] or '--help' in usr_inp[1]):
            raise ClientErr.CommandHelp('ll')
        cur_cli.list_dir()

    @staticmethod
    def client_cd(cur_cli, usr_inp):
        if len(usr_inp) > 1 and ('-h' in usr_inp[1] or '--help' in usr_inp[1]):
            raise ClientErr.CommandHelp('cd')
        if len(usr_inp) < 2:  # cd alone check
            cur_cli.pwd = '/root'
            cur_cli.cur_dir = cur_cli.root
            return
        path = usr_inp[1]
        cur_cli.to_dir(path)

    @staticmethod
    def client_mv(cur_cli, usr_inp):
        if len(usr_inp) > 1 and ('-h' in usr_inp[1] or '--help' in usr_inp[1]):
            raise ClientErr.CommandHelp('mv')
        if len(usr_inp) < 3:
            raise ClientErr.TooFewArgumentsError
        source_paths = usr_inp[1:-1]
        destination_path = usr_inp[-1]
        cur_cli.move(source_paths, destination_path)

    @staticmethod
    def client_info(cur_cli, usr_inp):
        if len(usr_inp) > 1 and ('-h' in usr_inp[1] or '--help' in usr_inp[1]):
            raise ClientErr.CommandHelp('info')
        if len(usr_inp) < 2:
            raise ClientErr.TooFewArgumentsError
        info_path = usr_inp[1]
        cur_cli.info(info_path)

    @staticmethod
    def client_mkdir(cur_cli, usr_inp):
        if len(usr_inp) > 1 and ('-h' in usr_inp[1] or '--help' in usr_inp[1]):
            raise ClientErr.CommandHelp('mkdir')
        if len(usr_inp) < 2:
            raise ClientErr.TooFewArgumentsError
        name = usr_inp[1]
        cur_cli.make_dir(name)

    @staticmethod
    def client_mkssh(cur_cli, usr_inp):
        if len(usr_inp) > 1 and ('-h' in usr_inp[1] or '--help' in usr_inp[1]):
            raise ClientErr.CommandHelp('mkssh')
        if len(usr_inp) < 4:
            raise ClientErr.TooFewArgumentsError
        ssh_name = usr_inp[1]
        user = usr_inp[2]
        host = usr_inp[3]
        password = usr_inp[4] if len(usr_inp) > 4 else None
        cur_cli.make_ssh(ssh_name, user, host, password)

    @staticmethod
    def client_mktel(cur_cli, usr_inp):
        if len(usr_inp) > 1 and ('-h' in usr_inp[1] or '--help' in usr_inp[1]):
            raise ClientErr.CommandHelp('mktel')
        if len(usr_inp) < 3:
            raise ClientErr.TooFewArgumentsError
        tel_name = usr_inp[1]
        host = usr_inp[2]
        port = usr_inp[3] if len(usr_inp) > 3 else None
        user = usr_inp[4] if len(usr_inp) > 4 else None
        password = usr_inp[5] if len(usr_inp) > 5 else None
        cur_cli.make_tel(tel_name, host, port, user, password)

    @staticmethod
    def client_edit(cur_cli, usr_inp):
        if len(usr_inp) > 1 and ('-h' in usr_inp[1] or '--help' in usr_inp[1]):
            raise ClientErr.CommandHelp('edit')
        if len(usr_inp) < 2:
            raise ClientErr.TooFewArgumentsError
        key = usr_inp[1]
        cur_cli.edit(key)

    @staticmethod
    def client_ssh(cur_cli, usr_inp):
        if len(usr_inp) > 1 and ('-h' in usr_inp[1] or '--help' in usr_inp[1]):
            raise ClientErr.CommandHelp('ssh')
        if len(usr_inp) < 2:
            raise ClientErr.TooFewArgumentsError
        path = usr_inp[1]
        cur_cli.connect(path, SecureShell)

    @staticmethod
    def client_tel(cur_cli, usr_inp):
        if len(usr_inp) > 1 and ('-h' in usr_inp[1] or '--help' in usr_inp[1]):
            raise ClientErr.CommandHelp('tel')
        if len(usr_inp) < 2:
            raise ClientErr.TooFewArgumentsError
        path = usr_inp[1]
        cur_cli.connect(path, Telnet)

    @staticmethod
    def client_pwd(cur_cli, usr_inp):
        if len(usr_inp) > 1 and ('-h' in usr_inp[1] or '--help' in usr_inp[1]):
            raise ClientErr.CommandHelp('pwd')
        print(cur_cli.pwd)

    @staticmethod
    def client_rm(cur_cli, usr_inp):
        if len(usr_inp) > 1 and ('-h' in usr_inp[1] or '--help' in usr_inp[1]):
            raise ClientErr.CommandHelp('rm')
        if len(usr_inp) < 2:
            raise ClientErr.TooFewArgumentsError
        if usr_inp[1] == '-r' or usr_inp[1] == '--recursive':
            path = usr_inp[2]
            cur_cli.rem_entry(path, rm_directory=True)
        else:
            path = usr_inp[1]
            cur_cli.rem_entry(path)

    @staticmethod
    def client_exit(cur_cli, usr_inp):
        if len(usr_inp) > 1 and ('-h' in usr_inp[1] or '--help' in usr_inp[1]):
            raise ClientErr.CommandHelp('exit')
        cur_cli.save_file()
        sys.exit(0)

    @staticmethod
    def client_invalid(cur_cli, usr_inp):
        full_input = ' '.join(usr_inp)
        print(full_input + ' is not a valid command')

    def get(self, key):
        cmd_dict = {
            'll': self.client_ll,
            'cd': self.client_cd,
            'mv': self.client_mv,
            'info': self.client_info,
            'mkdir': self.client_mkdir,
            'mkssh': self.client_mkssh,
            'mktel': self.client_mktel,
            'edit': self.client_edit,
            'ssh': self.client_ssh,
            'tel': self.client_tel,
            'pwd': self.client_pwd,
            'rm': self.client_rm,
            'help': self.client_help,
            'exit': self.client_exit
        }
        return cmd_dict.get(key, self.client_invalid)


class ClientErr:
    class InvalidNameError(Exception):
        def __init__(self):
            Exception.__init__(self)
            self.error_msg = 'Specified name is invalid (cannot be empty, be root, or contain whitespace or / )'

    class ExistingNameError(Exception):
        def __init__(self, name):
            Exception.__init__(self)
            self.error_msg = 'Specified name exists in the specified directory (' + name + ')'

    class TooFewArgumentsError(Exception):
        def __init__(self, cmd_tag):
            Exception.__init__(self)
            self.cmd_tag = cmd_tag
            self.error_dict = {
                'mv': '\'mv\' requires the arguments <entry to be named or moved> <destination entry or name>',
                'mkdir': '\'mkdir\' requires the argument <name of directory>',
                'mkssh': '\'mkssh\' requires the arguments <ssh name> <user> <hostname> <op. password>',
                'mktel': '\'mktel\' requires the arguments <tel name> <host> <op. port> <op. user> <op. password>',
                'ssh': '\'ssh\' requires the argument <name of ssh>',
                'rm': '\'rm\' requires the argument <index or name of entry>'
            }
            self.error_msg = self.error_dict[self.cmd_tag]

    class InvalidPathError(Exception):  # add path string arg and error message
        def __init__(self, code, path):
            Exception.__init__(self)
            self.code = code  # Codes:
            self.error_dict = {
                1: 'Invalid path (',
                2: 'Path does not point to an entry (',
                3: 'Path does not point to a directory (',
                4: 'Path cannot continue after a non directory (',
                5: 'Path cannot move beyond the scope of the client ('
            }
            self.error_msg = self.error_dict[self.code] + path + ')'

    class CommandHelp(Exception):
        def __init__(self, cmd_code=None):
            Exception.__init__(self)
            self.cmd_code = cmd_code
            self.help_dict = {
                'll': '''Display all the entries in the current directory.
                Usage of the ll command: \'ll\'''',
                'cd': '''Change the displayed directory to the specified path. This follows Linux path notation.
                Usage of the cd command: \'cd <path>\'''',
                'mv': '''Rename/Move the specified entry/entries.
                Usage of the mv command: \'mv <entry path if rename/entry(s) path(s) if move> <destination path>\'''',
                'info': '''Display the information of the entry at the given path.
                Usage of the info command: \'info <path>\'''',
                'mkdir': '''Make a directory in the displayed directory.
                Usage of the mkdir command: \'mkdir <directory name>\'''',
                'mkssh': '''Make a SecureShell in the displayed directory.
                Usage of the mkssh command: \'mkssh <ssh name> <username> <host> <op. password>\'''',
                'mktel': '''Make a Telnet in the displayed directory.
                Usage of the mktel command: \'mktel <tel name> <host> <op. port> <op. username> <op. password>\'''',
                'edit': '''Edit the entry at the specified path.
                Usage of the edit command: \'edit <path>\'''',
                'ssh': '''Open the SecureShell at the given path.
                Usage of the ssh command: \'ssh <path>\'''',
                'tel': '''Open the Telnet at the given path.
                Usage of the tel command: \'tel <path>\'''',
                'pwd': '''Display the present working directory.
                Usage of the pwd command: \'pwd\'''',
                'rm': '''Remove the entry at the given path.
                Usage of the rm command: \'rm <path>\'''',
                'help': '''Display the help message.
                Usage of the help command: \'help\'''',
                'exit': '''Safe exit the client and save entries before exiting
                Usage of the exit command: \'exit\''''
            }
            self.help_msg = self.help_dict.get(self.cmd_code)


if __name__ == '__main__':
    client = Client()
    if os.path.isfile('.ssh_client.txt') and os.stat('.ssh_client.txt').st_size != 0:
        client.load_file()
    cmd_switch = CmdSwitch()
    while True:  # TODO undo testing comment out
        try:
            prompt = client.pwd.replace('/root', '~') + ' '
            user_input = input(prompt).split()
            if len(user_input) == 0:  # just hit enter check
                continue
            cmd = cmd_switch.get(user_input[0])
            cmd(client, user_input)
        except ClientErr.InvalidNameError as ine:
            print(ine.error_msg)
        except ClientErr.ExistingNameError as ene:
            print(ene.error_msg)
        except ClientErr.TooFewArgumentsError as tfae:
            print(tfae.error_msg)
        except ClientErr.InvalidPathError as ipe:
            print(ipe.error_msg)
        except ClientErr.CommandHelp as ch:
            print(ch.help_msg)
        except SystemExit as se:  # saves file in the event of sys exit
            client.save_file()
            print('SSH Client exited with exit code ' + str(se.code))
            sys.exit(se.code)
        except KeyboardInterrupt:  # adds a check to determine if SIGINT is intended and saves file structure
            try:
                print('\nCtrl C has been pressed, press Ctrl C again to exit, else press enter')
                input()
            except KeyboardInterrupt:
                print()
                client.save_file()
                sys.exit(2)
