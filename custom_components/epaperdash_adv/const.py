"""Constants for the EpaperDash-ADV integration."""
from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "epaperdash_adv"
PLATFORMS = [Platform.IMAGE]

CONF_DASHBOARD_PATH = "dashboard_path"
CONF_LONG_LIVED_TOKEN = "long_lived_token"
CONF_WIDTH = "width"
CONF_HEIGHT = "height"
CONF_ROTATION = "rotation"
CONF_COLOR_MODE = "color_mode"
CONF_DITHER = "dither"
CONF_REFRESH_INTERVAL = "refresh_interval"

DATA_ACCESS_TOKEN = "access_token"

COLOR_MODE_BW = "bw"
COLOR_MODE_GRAYSCALE4 = "gray4"
COLOR_MODE_GRAYSCALE16 = "gray16"
COLOR_MODE_COLOR = "color"

COLOR_MODES = [COLOR_MODE_BW, COLOR_MODE_GRAYSCALE4, COLOR_MODE_GRAYSCALE16, COLOR_MODE_COLOR]
ROTATIONS = [0, 90, 180, 270]

DEFAULT_DASHBOARD_PATH = "/lovelace-eink/0"
DEFAULT_WIDTH = 1072
DEFAULT_HEIGHT = 1448
DEFAULT_ROTATION = 0
DEFAULT_COLOR_MODE = COLOR_MODE_BW
DEFAULT_DITHER = True
DEFAULT_REFRESH_INTERVAL = 300
MIN_REFRESH_INTERVAL = 30

SERVICE_REFRESH = "refresh"
SERVICE_CAPTURE_DEBUG = "capture_debug"
