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
from ops.model import ActiveStatus, BlockedStatus, WaitingStatus, ModelError

logger = logging.getLogger()


class InfinibandOperator(CharmBase):
    """Infiniband Charmed Operator."""

    def __init__(self, *args):
        """Initialize the charm."""
        super().__init__(*args)

        if os_release()["ID"] == "ubuntu":
            self.repo_path = self.model.resources.fetch('apt-repo')
            self._infiniband_ops_manager = InfinibandOpsManagerUbuntu()
        else:
            self.repo_path = self.model.resources.fetch('yum-repo')
            self._infiniband_ops_manager = InfinibandOpsManagerCentos()

        event_handler_bindings = {
            self.on.install: self._on_install,
            self.on.remove: self._on_remove,
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
            logger.info(f"Get InfiniBand repo file in {self.repo_path}")
        except ModelError:
            logger.info(f"No InfiniBand repo file provided. Using a default one")
            repo_path = None

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

if __name__ == "__main__":
    main(InfinibandOperator)
