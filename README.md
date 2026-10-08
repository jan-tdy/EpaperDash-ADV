# EpaperDash-ADV

A Home Assistant custom integration that produces an e-ink friendly image of
a Lovelace dashboard **view that you design yourself**. There is no special
card to configure inside the integration: build whatever dashboard view you
want in Lovelace, point EpaperDash-ADV at it, and it captures a real
screenshot of that view, converts it to grayscale/1-bit, and serves it at a
plain image URL that an e-ink device can poll on an interval.

This is an independent, clean-room implementation. It was *inspired by* the
idea behind [cryptomilk/hass-eink-dashboard](https://github.com/cryptomilk/hass-eink-dashboard)
(serving a dashboard image to an e-ink device), but takes a different
approach on purpose: instead of a dedicated card/template you edit inside the
integration, it screenshots the actual Lovelace view you already have. No
code from that project was used or copied — it has its own license.

## How it works

1. You build a dashboard view in Lovelace, ideally one kept simple and
   static-looking (e-ink doesn't do animations or frequent partial updates
   well).
2. EpaperDash-ADV launches a headless Chromium (via
   [Playwright](https://playwright.dev/python/)) inside Home Assistant,
   opens that view as a logged-in user, and takes a screenshot.
3. The screenshot is converted to the resolution/rotation/color mode you
   configured (black & white with dithering, 4-level or 16-level grayscale),
   on a timer.
4. The result is available:
   - as a plain, token-protected image URL any device with basic HTTP/image
     support can fetch — no Home Assistant login required on the device side;
   - as an `image` entity inside Home Assistant, for preview/automations.

There is no separate add-on, container, or app to run — it is a single
custom integration.

## Installation

### HACS (recommended)

1. HACS → Integrations → ⋮ → Custom repositories → add this repository URL.
2. Install "EpaperDash-ADV", restart Home Assistant.
3. Settings → Devices & Services → Add Integration → "EpaperDash-ADV".

### Manual

Copy `custom_components/epaperdash_adv` into your Home Assistant
`config/custom_components/` folder and restart.

## System dependencies (important for Home Assistant Container / Core)

The integration downloads a Chromium build via Playwright automatically on
first setup (`playwright install chromium`), but Chromium itself needs a
handful of OS-level shared libraries that are **not** part of the stock
`homeassistant/home-assistant` container image. If you run Home Assistant
Container/Core in Docker, extend the image, for example:

```dockerfile
FROM homeassistant/home-assistant:stable

RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libdbus-1-3 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libasound2 libpangocairo-1.0-0 libpango-1.0-0 libcairo2 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*
```

(Exact package names/versions depend on your base distro; run
`python3 -m playwright install-deps --dry-run` inside the container to see
what Playwright thinks is missing.)

If Chromium fails to start, the config entry will show a clear error instead
of silently failing, pointing back to this section.

## Configuration

- **Long-lived access token**: generate one under your HA user profile
  (Security → Long-lived access tokens). It is used only to let the headless
  browser open the dashboard as a logged-in user — it is never exposed to
  the e-ink device.
- **Dashboard path**: the path of the Lovelace view to capture, e.g.
  `/lovelace-eink/0`. Build a dedicated, minimal dashboard view for this —
  full sidebar/header included views work but waste screen space.
- **Width / height / rotation**: match your panel's native resolution and
  mounting orientation.
- **Color mode**: `bw` (1-bit, dithered or thresholded), `gray4` (posterized
  to 16 gray levels), `gray16` (full 8-bit grayscale), or `color` (debugging
  only).
- **Dither**: Floyd–Steinberg dithering when converting to black & white;
  turn it off for crisp text-heavy dashboards, on for photos/gradients.
- **Refresh interval**: how often (in seconds) the screenshot is retaken.

## Fetching the image on your e-ink device

After setup, the integration exposes:

```
http://<your-ha-host>:8123/api/epaperdash_adv/<entry_id>/<token>/image.png
```

The `entry_id` and `token` are specific to your installation — check the
`capture_debug` service response or your HA logs after setup, or inspect the
`image` entity's picture URL from the frontend.

This endpoint needs **no** Home Assistant authentication — it is meant to be
pollable by very limited devices (a basic/legacy browser, a cron job with
`curl`/`wget`, a custom firmware script that fetches and displays an image on
a schedule). This covers most jailbroken/rooted e-ink e-readers with a way to
periodically fetch and display an image, without needing to name any
specific device or brand here.

Keep the URL private — anyone with it can view your dashboard screenshot.
If it ever leaks, remove and re-add the integration to get a fresh token.

## Troubleshooting

- **Login screen captured instead of the dashboard**: the long-lived token
  injection didn't take effect in time, or the token is invalid. Call the
  `epaperdash_adv.capture_debug` service and open
  `http://<ha>:8123/local/epaperdash_adv_debug.png` to see exactly what was
  captured.
- **Config entry fails to load with a Chromium/Playwright error**: see
  "System dependencies" above.
- **Screenshot looks cut off or badly scaled**: adjust width/height to match
  your panel's native resolution; the browser viewport is set to exactly
  that size.

## License

MIT, see [LICENSE](LICENSE). This project does not reuse any code from
other e-ink dashboard projects.
