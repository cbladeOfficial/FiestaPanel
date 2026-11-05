#!/usr/bin/env python3
"""
FiestaPanel Backward Compatibility Wrapper (panelctl -> fiestapanel)
"""
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
fiestapanel_script = os.path.join(SCRIPT_DIR, "fiestapanel.py")

if os.path.exists(fiestapanel_script):
    with open(fiestapanel_script, "rb") as f:
        code = compile(f.read(), fiestapanel_script, "exec")
        exec(code, {"__name__": "__main__", "__file__": fiestapanel_script})
else:
    import fiestapanel
    fiestapanel.main()
