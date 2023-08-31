from pathlib import Path
from typing import List
from secrets import token_hex
from shutil import move

import fabric
import os
import pathlib
import shlex
import subprocess
import yaml

class Verdict():
    """Define checker verdict.

    Attributes
    ----------
    status: str
        Verdict status. ``OK`` is given if the service passed all the testcases, ``FAIL`` if the
        service fail on some testcases (e.g.: give invalid response or take too long to respond),
        or ``ERROR`` if the checker cannot execute the testcase properly.
    message: str
        Additional information related to the verdict given.
    """
    def __init__(self, status: str, message: str):
        """Constructor.

        Parameters
        ----------
        status: str
            See the :attr:`~Verdict.status` attribute.
        message: str
            See the :attr:`~Verdict.message` attribute.
        """
        self.status = status
        self.message = message

    def is_ok(self):
        """Check is the verdict is ``OK`` or not.

        Returns
        -------
        bool
            Whether the verdict is ``OK`` or not.
        """
        return self.status == "OK"

    @classmethod
    def OK(cls, message = ""):
        """Create OK verdict object.

        Parameters
        ----------
        message: str
            See the :attr:`~Verdict.message` attribute.

        Returns
        -------
        fulgens.Verdict
            Verdict object with ``OK`` status.
        """
        return Verdict("OK", message)

    @classmethod
    def FAIL(cls, message):
        """Create FAIL verdict object.

        Parameters
        ----------
        message: str
            See the :attr:`~Verdict.message` attribute.

        Returns
        -------
        fulgens.Verdict
            Verdict object with ``FAIL`` status.
        """
        return Verdict("FAIL", message)

    @classmethod
    def ERROR(cls, message):
        """Create ERROR verdict object.

        Parameters
        ----------
        message: str
            See the :attr:`~Verdict.message` attribute.

        Returns
        -------
        fulgens.Verdict
            Verdict object with ``ERROR`` status.
        """
        return Verdict("ERROR", message)

class ChallengeHelper():
    """
    Helper for checker to get and interact with the service.

    Attributes
    ----------
    addresses: List[str]
        List of service addresses that exposed.
    secret: str
        Team secret key.
    local_challenge_dir: pathlib.Path
        Local challenge directory.
    remote_challenge_dir: pathlib.Path
        Remote challenge directory.
    compose_filename: str
        Compose filename. The default value is ``docker-compose.yml``.
    ssh_conn: fabric.Connection or None
        SSH connection to the server that runs the services. If ``None``, it will assume
        that the service is in the same server as the checker, also :attr:`~ChallengeHelper.remote_challenge_dir`
        and :attr:`~ChallengeHelper.local_challenge_dir` will have the same value.
    """
    def __init__(self, addresses: List[str], secret: str, local_challenge_dir: str | pathlib.Path, remote_challenge_dir: str | pathlib.Path = None, compose_filename: str = "docker-compose.yml", ssh_conn: fabric.Connection | None = None):
        """Constructor.

        Parameters
        ----------
        addresses: List[str]
            See the :attr:`~ChallengeHelper.status` attribute.
        secret: str
            See the :attr:`~ChallengeHelper.secret` attribute.
        local_challenge_dir: str or pathlib.Path
            See the :attr:`~ChallengeHelper.local_challenge_dir` attribute.
        remote_challenge_dir: str or pathlib.Path
            See the :attr:`~ChallengeHelper.remote_challenge_dir` attribute.
        compose_filename: str
            See the :attr:`~ChallengeHelper.compose_filename` attribute.
        ssh_conn: fabric.Connection or None
            See the :attr:`~ChallengeHelper.ssh_conn` attribute.
        """
        self.addresses = addresses
        self.ssh_conn = ssh_conn
        self.secret = secret
        with open(local_challenge_dir.joinpath(compose_filename)) as compose_file:
            compose_data = yaml.safe_load(compose_file)
        self.services = compose_data["services"]

        self.local_chall_dir = Path(local_challenge_dir)

        if ssh_conn == None:
            self.remote_chall_dir = self.local_chall_dir
        else:
            self.remote_chall_dir = Path(remote_challenge_dir)        
        
        self.compose_path = self.remote_chall_dir.joinpath(compose_filename)        
    

    def __cmd_wrapper(self, real_cmd: str):
        return_code = 0
        if not self.ssh_conn:
            cmd_res = subprocess.run(real_cmd, capture_output=True, shell=True)
            return_code = cmd_res.returncode
            return cmd_res.stdout, cmd_res.stderr, cmd_res.returncode
        else:
            cmd_res = self.ssh_conn.run(real_cmd, hide=True)
            return_code = cmd_res.exited
            return cmd_res.stdout.encode(), cmd_res.stderr.encode(), cmd_res.exited
    
    def __cmd_container_wrapper(self, service_name: str, cmd: str):
        real_cmd = f"docker compose -f {self.compose_path} exec {service_name} /bin/sh -c {shlex.quote(cmd)}"
        return self.__cmd_wrapper(real_cmd)

    def __transfer_file_wrapper(self, source: str, dest: str):
        if not self.ssh_conn:
            move(source, dest)
        else:
            self.ssh_conn.get(remote=source, local=str(dest))
        return True
    
    def __transfer_folder_wrapper(self, source: str, dest: str):
        if not self.ssh_conn:
            move(source, dest)
        else:
            folder_tarname = Path("/tmp").joinpath(token_hex(8))
            self.ssh_conn.run(f"tar -czf {folder_tarname} {source}", hide=True)
            self.__transfer_file_wrapper(folder_tarname, folder_tarname)
            self.ssh_conn.run(f"rm -rf {folder_tarname} {source}", hide=True)
            
            self.ssh_conn.local(f"tar --strip-components=1 -C /tmp -xzf {folder_tarname}", hide=True)
            move(source, dest)
            os.remove(folder_tarname)
        return True
    
    def __dir_checker_wrapper(self, path):
        if not self.ssh_conn:
            return Path(path).is_dir()
        else:
            res = self.ssh_conn.run(f"file {path}", hide=True).stdout
            return res.find("directory") != -1

    def __get_container_file_wrapper(self, service_name, source):
        dest_fname = Path("/tmp").joinpath(os.path.basename(source))
        copy_cmd = f"docker compose -f {self.compose_path} cp {service_name}:{source} {dest_fname}"
        cmd_status = self.__cmd_wrapper(copy_cmd)
        if cmd_status[-1] != 0:
            raise Exception(f"failed to copy: {cmd_status[1].decode()}")
        return dest_fname
    
    def fetch(self, service_name: str, source: str | pathlib.Path, dest: str | pathlib.Path):
        """Fetch file/folder from the remote service container to the local filesystem.

        Parameters
        ----------
        service_name: str
            Service name.
        source: str | pathlib.Path
            Service container path file. 
        dest: str | pathlib.Path
            Local filesystem path.

        Returns
        -------
        bool
            Whether fetch is successful or not.

        Raises
        ------
        ValueError
            If the service name requested cannot be found.
        IOError
            If there is something wrong with the file transfer or modification.
        """
        if service_name not in self.services:
            raise ValueError(f"service '{service_name}' cannot be found.")
        
        container_fname = self.__get_container_file_wrapper(service_name, source)
        if self.__dir_checker_wrapper(container_fname):
            return self.__transfer_folder_wrapper(container_fname, dest)
        else:
            return self.__transfer_file_wrapper(container_fname, dest)

    def run(self, service_name: str, cmd: List[str] | str):
        """Run shell commands inside the service container.

        Parameters
        ----------
        service_name: str
            Service name.
        cmd: List[str] or str
            Command to be executed.

        Returns
        -------
        bytes
            Standard output.
        bytes
            Standard error.
        int
            exit code
        
        Raises
        ------
        ValueError
            If the service name requested cannot be found.
        """
        if service_name not in self.services:
            raise ValueError(f"service '{service_name}' cannot be found.")
        if isinstance(cmd, str):
            return self.__cmd_container_wrapper(service_name, cmd)
        else:
            return self.__cmd_container_wrapper(service_name, " ; ".join(cmd))
