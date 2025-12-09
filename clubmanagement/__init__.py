# -*- coding: utf-8 -*-

from . import controllers
from . import models

def _pre_init_hook(env):
    print(f"_pre_init_hook(): Start")
    print(f"_pre_init_hook(): End")

def _post_init_hook(env):
    print(f"_post_init_hook(): Start")

    # Lazy Import clubcustomfieldvalue:
    from .models.clubcustomfieldvalue import _post_init_hook as clubcustomfieldvalue_post_init_hook
    clubcustomfieldvalue_post_init_hook(env)

    print(f"_post_init_hook(): End")

def _uninstall_hook(env):
    print(f"_uninstall_hook(): Start")
    print(f"_uninstall_hook(): End")