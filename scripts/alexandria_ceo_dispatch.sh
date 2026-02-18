#!/usr/bin/env bash
set -euo pipefail

systemctl --user daemon-reload
systemctl --user start alexandria-auto-cycle.service
systemctl --user --no-pager --full status alexandria-auto-cycle.service
