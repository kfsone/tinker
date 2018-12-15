import logging
from paramiko import client as pmclient

import time


class SSHSession(object):
    def __init__(self, hostname, username, password, logger=None):
        self.logger = logger or logging

        self.client = ssh = pmclient.SSHClient()
        ssh.set_missing_host_key_policy(pmclient.AutoAddPolicy())

        self.logger.debug("SSHClient: Connecting to %s with %s and password", hostname, username)
        ssh.connect(hostname, username=username, password=password, look_for_keys=False)


    def execute(self, command, inputs=None, read_stdout=False, *args, **kwargs):
        stdin, stdout, stderr = self.client.exec_command(command, *args, **kwargs)

        if inputs:
            stdin.channel.sendall(inputs)
            stdin.channel.shutdown_write()

        while True:
            if stdout.channel.exit_status_ready():
                break
            time.sleep(0.001)

        rc = stdout.channel.recv_exit_status()
        if read_stdout:
            return rc, stdout.read()
        else:
            return rc


    def ping(self):
        self.execute('echo')


    def close(self):
        if self.client:
            self.logger.debug("Shutting down SSH session")
            self.client.close()
            self.client = None


class SFTPSession(object):
    def __init__(self, hostname=None, username=None, password=None, initial_path=None, logger=None, ssh=None):
        assert ssh or (hostname and username and password)
        self.__own_ssh = not bool(ssh)
        ssh = self.__ssh_client = ssh or SSHSession(hostname, username, password, logger=logger)
        self.logger = logger or logging
        logger.debug("SFTP: Opening session")
        self.client = sftp = ssh.client.open_sftp()

        if initial_path:
            self.logger.debug("remote cd: %s", initial_path)
            sftp.chdir(initial_path)


    def ping(self):
        self.client.stat('.')


    def close(self):
        if self.client:
            self.logger.debug("Shutting down SFTP session")
            self.client.close()
            self.client = None

        if self.__own_ssh and self.__ssh_client:
            self.__ssh_client.close()
            self._ssh_client = None


