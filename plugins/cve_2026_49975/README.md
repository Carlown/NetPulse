# CVE-2026-49975 NetPulse plugin

This folder is a NetPulse folder plugin (`main.py` + `_poc.py`). Import the
folder from **Settings -> Plugins -> Import Plugin** or copy it into the
NetPulse plugins directory shown by the application.

The page accepts an `http://` or `https://` target. Clicking **检测并开始**
first completes an HTTP/2 PING probe. The PoC workers start only after that
probe succeeds. While running, a liveness probe is sent every 30 seconds; a
failed probe closes all active sockets and returns the page to the idle state.
