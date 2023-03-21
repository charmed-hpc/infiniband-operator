#!/usr/bin/env python3
"""InfiniBand install, remove and return version."""
import logging
import tempfile
from pathlib import Path
from subprocess import CalledProcessError, check_output, run

import requests

logger = logging.getLogger()


def os_release():
    """Return /etc/os-release as a dict."""
    os_release_data = Path("/etc/os-release").read_text()
    os_release_list = [
        item.split("=") for item in os_release_data.strip().split("\n") if item != ""
    ]
    return {k: v.strip('"') for k, v in os_release_list}


def arch() -> str:
    """Return the system architecture."""
    try:
        arch = check_output(["/bin/arch"])
    except CalledProcessError:
        raise InfinibandOpsError("Error detecting system architecture.")
    return arch.decode().strip()


def uname_r() -> str:
    """Return the kernel version."""
    try:
        kernel_version = check_output(["/usr/bin/uname", "-r"])
    except CalledProcessError:
        raise InfinibandOpsError("Error detecting kernel version.")
    return kernel_version.decode().strip()


class InfinibandOpsError(Exception):
    """Error raised for infiniband installation errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class InfinibandOpsManagerBase:
    """InfinibandOpsManagerBase."""

    def __init__(self):
        self._driver_package = "mlnx-ofed-all"
        self._ib_systemd_service = "openibd.service"

    def install(self) -> None:
        """Install Infiniband driver here."""
        raise Exception("Inheriting object needs to define this method.")

    def remove(self) -> None:
        """Remove Infiniband driver here."""
        raise Exception("Inheriting object needs to define this method.")

    def version(self) -> str:
        """Return the version of the InfiniBand driver."""
        # get the version from ofed_info
        try:
            version = check_output(["ofed_info", "-s"])
        except CalledProcessError:
            raise InfinibandOpsError("Cannot return version for package that isn't installed.")

        return version.decode().strip("MLNX_OFED_LINUX-:\n")

    def modprobe(self, modules: list) -> None:
        """Modprobe the Infiniband modules."""
        for module in modules:
            try:
                run(["modprobe", module])
            except CalledProcessError:
                raise InfinibandOpsError(f"Error modprobing {module}")

    def start(self) -> None:
        """Start infiniband systemd service."""
        run(["systemctl", "start", self._ib_systemd_service])

    def enable(self) -> None:
        """Enable infiniband systemd service."""
        run(["systemctl", "enable", self._ib_systemd_service])

    def stop(self) -> None:
        """Stop infiniband systemd service."""
        run(["systemctl", "stop", self._ib_systemd_service])

    def is_active(self) -> bool:
        """Check if systemd infiniband service is active."""
        try:
            cmd = ["systemctl", "is-active", self._ib_systemd_service]
            r = check_output(cmd)
            return "active" == r.decode().strip().lower()
        except CalledProcessError as e:
            logger.error(f"Could not check infiniband: {e}")

        return False


class InfinibandOpsManagerUbuntu(InfinibandOpsManagerBase):
    """InfinibandOpsManager for Ubuntu."""

    def __init__(self):
        super().__init__()
        self._driver_repo_filepath = Path("/etc/apt/sources.list.d/infiniband.list")

    def _set_repository(self, repo_path: Path) -> None:
        """Set a custom repository to install Infiniband drivers."""
        # Remove previous driver repo
        if self._driver_repo_filepath.exists():
            self._driver_repo_filepath.unlink()

        logger.info("Configuring InfiniBand yum repository")

        if repo_path is not None:
            # move it to /etc/apt/sources.list.d/infiniband.list
            repo_path.rename(self._driver_repo_filepath)
        else:
            raise InfinibandOpsError("No InfiniBand repository provided")

        # GPG key url
        key_url = "http://www.mellanox.com/downloads/ofed/RPM-GPG-KEY-Mellanox"

        # download the GPG key on tmp file
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_key_path = Path(f"{tmpdir}/mellanox.gpg")

            try:
                key_req = requests.get(key_url)
            except requests.exceptions.HTTPError:
                raise InfinibandOpsError(f"Error getting InfiniBand GPG key {key_url}")

            tmp_key_path.write_text(key_req.text)

            try:
                run(["apt-key", "add", str(tmp_key_path)])
            except CalledProcessError:
                raise InfinibandOpsError("Failed to add InfiniBand GPG key")

        logger.info("InfiniBand repository configured")

    def install(self, repo_path: Path) -> None:
        """Install InfiniBand drivers on Ubuntu."""
        # set the apt repository
        self._set_repository(repo_path)

        # update repositories
        try:
            run(["apt-get", "update"])
        except CalledProcessError:
            raise InfinibandOpsError("Error running `apt-get update`")

        # install the kernel headers
        uname = uname_r()
        try:
            run(["apt-get", "install", "-y", f"linux-headers-{uname}"])
        except CalledProcessError:
            raise InfinibandOpsError("Error installing kernel headers")

        # install the InfiniBand drivers
        try:
            run(["apt-get", "install", "-y", self._driver_package])
        except CalledProcessError:
            raise InfinibandOpsError("Error installing InfiniBand drivers")

    def remove(self) -> None:
        """Remove InfiniBand drivers from the OS."""
        try:
            run(["apt-get", "-y", "remove", "--purge", self._driver_package])
        except CalledProcessError:
            raise InfinibandOpsError("Error removing InfiniBand drivers")

        # Remove the drivers repo
        if self._driver_repo_filepath.exists():
            self._driver_repo_filepath.unlink()

        try:
            run(["apt-get", "update"])
        except CalledProcessError:
            raise InfinibandOpsError("Error running `apt-get update`")


class InfinibandOpsManagerCentos(InfinibandOpsManagerBase):
    """InfinibandOpsManager for Centos7."""

    def __init__(self):
        """Initialize class level variables."""
        super().__init__()
        self._driver_repo_filepath = Path("/etc/yum.repos.d/infiniband.repo")

    def _set_repository(self, repo_path: Path) -> None:
        """Set a custom repository to install Infiniband drivers."""
        # Remove previous driver repo
        if self._driver_repo_filepath.exists():
            self._driver_repo_filepath.unlink()

        logger.info("Configuring InfiniBand yum repository")

        if repo_path is not None:
            # move it to /etc/yum.repos.d/infiniband.repo
            repo_path.rename(self._driver_repo_filepath)
        else:
            # download driver version 5.8-1.1.2.1 repo as default
            repo_url = "http://linux.mellanox.com/public/repo/mlnx_ofed/5.8-1.1.2.1/rhel7.9/mellanox_mlnx_ofed.repo"
            try:
                req = requests.get(repo_url)
            except requests.exceptions.HTTPError:
                raise InfinibandOpsError(f"Error getting InfiniBand repository from {repo_url}")

            self._driver_repo_filepath.write_text(req.text)

        logger.info("InfiniBand yum repository configured")

    def install(self, repo_path: Path) -> None:
        """Install Mellanox Infiniband drivers."""
        # set the yum repository
        self._set_repository(repo_path)

        # Expire the cache and update repos
        try:
            run(["yum", "clean", "expire-cache"])
        except CalledProcessError:
            raise InfinibandOpsError("Error flushing the cache")

        # Add the devel kernel and kernel headers
        logger.info("Installing kernel devel and headers")

        uname = uname_r()

        try:
            run(
                [
                    "yum",
                    "install",
                    "-y",
                    f"kernel-devel-{uname}",
                    f"kernel-headers-{uname}",
                ]
            )
        except CalledProcessError:
            raise InfinibandOpsError("Error installing devel kernel headers")

        # Install infiniband driver
        logger.info(f"Installing InfiniBand {self._driver_package} drivers")
        try:
            run(["yum", "install", "-y", self._driver_package])
        except CalledProcessError:
            raise InfinibandOpsError(f"Error installing InfiniBand {self._driver_package} drivers")

    def remove(self) -> None:
        """Remove Infiniband drivers from the system."""
        # Remove infiniband driver package
        try:
            run(["yum", "erase", "-y", self._driver_package])
        except CalledProcessError:
            raise InfinibandOpsError("Error removing InfiniBand drivers from the system")

        # Remove the drivers repo
        if self._driver_repo_filepath.exists():
            self._driver_repo_filepath.unlink()

        # Expire the cache and update repos
        try:
            run(["yum", "clean", "expire-cache"])
        except CalledProcessError:
            raise InfinibandOpsError("Error flushing the cache")
