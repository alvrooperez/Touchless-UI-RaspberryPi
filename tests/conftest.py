import sys
from unittest.mock import MagicMock

sys.modules['RPi'] = MagicMock()
sys.modules['RPi.GPIO'] = MagicMock()
sys.modules['gpiozero'] = MagicMock()
