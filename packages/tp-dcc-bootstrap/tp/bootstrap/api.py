#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains API module for tpDcc Tools packages manager
"""

from tp.bootstrap.core.manager import get_package_manager_from_path, get_current_package_manager
from tp.bootstrap.core.manager import set_current_package_manager
from tp.bootstrap.commands import run_command
