import os
import sys
from pathlib import Path

# Look at this absolutely fucking retarded shit python makes you do just to reference something in a parent folder
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))


from utilities import ensure_authenticated

ensure_authenticated()
