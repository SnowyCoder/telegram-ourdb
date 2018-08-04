import logging
import os

# Select all direct subdirectories
from importlib import import_module
from pathlib import Path

search_dir = Path(__file__).parent
submodules_names = next(os.walk(search_dir))[1]

submodules_names = [submod for submod in submodules_names if os.path.isfile(search_dir / submod / '__init__.py')]

logging.info("Loading submodules: " + str(submodules_names))
# Load them as modules
submodules = [import_module('modules.' + submodule_name) for submodule_name in submodules_names]

# Select their handles
__handlers__ = [handle for submodule in submodules for handle in submodule.__handlers__]
