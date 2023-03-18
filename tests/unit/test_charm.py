#!/usr/bin/env python3
import unittest

from charm import InfinibandOperator
from ops.testing import Harness


class TestCharm(unittest.TestCase):
    """Unit test suite for InfiniBand driver operator."""

    def setUp(self) -> None:
        """Set up unit test."""
        self.harness = Harness(InfinibandOperator)
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()

    def test_pass(self) -> None:
        """Test pass."""
        pass
