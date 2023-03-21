#!/usr/bin/env python3
"""InfiniBand Operator Charm."""
import logging

from infiniband_ops_manager import (
    InfinibandOpsError,
    InfinibandOpsManagerCentos,
    InfinibandOpsManagerUbuntu,
    os_release,
)
from ops.charm import CharmBase
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus, ModelError, WaitingStatus

logger = logging.getLogger()


class InfinibandOperator(CharmBase):
    """Infiniband Charmed Operator."""

    def __init__(self, *args):
        """Initialize the charm."""
        super().__init__(*args)

        if os_release()["ID"] == "ubuntu":
            self.resource_name = "apt-repo"
            self._infiniband_ops_manager = InfinibandOpsManagerUbuntu()
        else:
            self.resource_name = "yum-repo"
            self._infiniband_ops_manager = InfinibandOpsManagerCentos()

        event_handler_bindings = {
            self.on.install: self._on_install,
            self.on.remove: self._on_remove,
            self.on.modprobe_action: self.modprobe_action,
            self.on.ibstatus_action: self.ibstatus_action,
        }
        for event, handler in event_handler_bindings.items():
            self.framework.observe(event, handler)

    def _on_install(self, event):
        """Install Infiniband drivers."""
        install_msg = "Installing Infiniband drivers..."
        logger.info(install_msg)
        self.unit.status = WaitingStatus(install_msg)

        # get the repo file resource
        try:
            logger.info(f"Getting InfiniBand repo file: {self.resource_name}")
            self.repo_path = self.model.resources.fetch(self.resource_name)
        except ModelError:
            logger.info("No InfiniBand repo file provided. Using a default one")
            self.repo_path = None

        # install the driver
        try:
            self._infiniband_ops_manager.install(self.repo_path)
        except InfinibandOpsError as e:
            logger.error(e)
            self.unit.status = BlockedStatus(e)
            event.defer()
            return

        # Set the workload version and status.
        self.unit.set_workload_version(self._infiniband_ops_manager.version())
        self.unit.status = ActiveStatus("Ready")

    def _on_remove(self, event):
        """Remove Infiniband drivers."""
        msg = "Removing Infiniband drivers..."
        logger.info(msg)
        self.unit.status = WaitingStatus(msg)

        try:
            self._infiniband_ops_manager.remove()
        except InfinibandOpsError as e:
            logger.error(e)
            self.unit.status = BlockedStatus(e)
            event.defer()
            return

    def modprobe_action(self, event):
        """Modprobe the Infiniband modules."""
        modules = [
            "rdma_ucm",
            "rdma_cm",
            "ib_ipoib",
            "mlx5_core",
            "mlx5_ib",
            "ib_uverbs",
            "ib_umad",
            "ib_cm",
            "ib_core",
            "mlxfw",
        ]

        msg = "Modprobing InfiniBand modules..."
        logger.info(msg)
        self.unit.status = WaitingStatus(msg)

        try:
            self._infiniband_ops_manager.modprobe(modules)
        except InfinibandOpsError as e:
            logger.error(e)
            self.unit.status = BlockedStatus(e)
            event.defer()
            return

        self.unit.status = ActiveStatus("Ready")

    def ibstatus_action(self, event):
        """Show the InfiniBand status."""
        status = self._infiniband_ops_manager.ibstatus()
        event.set_results({"infiniband-status": status})


if __name__ == "__main__":
    main(InfinibandOperator)
