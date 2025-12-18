# -*- coding: utf-8 -*-

from . import controllers
from . import models

import logging
_logger = logging.getLogger(__name__)

'''
###
# Uncomment for debugging related fields errors "KeyError: None"
###

from odoo import fields
original_setup_related = fields.Field.setup_related

def patched_setup_related(self, model):
    _logger.info(f"Setting up related field: {self.name} on model {model._name}")
    try:
        return original_setup_related(self, model)
    except Exception as e:
        _logger.exception(f"Error setting up related field {self.name} on model {model._name}: {e}")
        raise

fields.Field.setup_related = patched_setup_related
'''

def _pre_init_hook(env):
    _logger.info(f"_pre_init_hook(): Start")
    _logger.info(f"_pre_init_hook(): End")

def _post_init_hook(env):
    _logger.info(f"_post_init_hook(): Start")

    # Lazy Import clubcustomfieldvalue:
    from .models.clubcustomfieldvalue import _post_init_hook as clubcustomfieldvalue_post_init_hook
    clubcustomfieldvalue_post_init_hook(env)

    _logger.info(f"_post_init_hook(): End")

def _uninstall_hook(env):
    _logger.info(f"_uninstall_hook(): Start")
    _logger.info(f"_uninstall_hook(): End")