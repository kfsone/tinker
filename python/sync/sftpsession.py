import logging
from paramiko import client as pmclient


class SFTPSession(object):
    def __init__(self, hostname, username, password, initial_path=None, logger=None):
        self.__ssh_client = ssh = pmclient.SSHClient()
        ssh.set_missing_host_key_policy(pmclient.AutoAddPolicy())
        self.logger = logger or logging

        logger.debug("Connecting to %s with %s and password", hostname, username)
        ssh.connect(hostname, username=username, password=password, look_for_keys=False)

        logger.debug("opening sftp session")
        self.client = sftp = ssh.open_sftp()

        if initial_path:
            logger.debug("remote cd: %s", initial_path)
            sftp.chdir(initial_path)


    def close(self):
        if self.client:
            self.logger.debug("Shutting down sftp session")
            self.client.close()
            del self.client

        if self.__ssh_client:
            self.logger.debug("Shutting down ssh session")
            self.__ssh_client.close()
            del self.__ssh_client


