#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECK_SCRIPT="${SCRIPT_DIR}/vps_deploy_check.sh"

exec bash "${CHECK_SCRIPT}" --mode deploy "$@"
