#!/usr/bin/env bash
# Setup a local DashScope mock and optional static video server for dev.

set -euo pipefail

MOCK_ROOT="${MOCK_ROOT:-/tmp/prism-mock}"
MOCK_PORT="${MOCK_PORT:-8009}"
VIDEO_PATH="${MOCK_ROOT}/dummy.mp4"
MODULE_DIR="${MOCK_ROOT}/dashscope"
MODULE_PATH="${MODULE_DIR}/__init__.py"

mkdir -p "${MODULE_DIR}"

cat > "${MODULE_PATH}" <<'PY'
from http import HTTPStatus

class _Output:
    def __init__(self, task_id=None, video_url=None):
        self.task_id = task_id
        self.video_url = video_url

class _Response:
    def __init__(self, status_code=HTTPStatus.OK, output=None, code="OK", message=""):
        self.status_code = status_code
        self.output = output or _Output()
        self.code = code
        self.message = message

class VideoSynthesis:
    @staticmethod
    def async_call(*args, **kwargs):
        return _Response(output=_Output(task_id="mock-task"))

    @staticmethod
    def wait(task=None, api_key=None):
        return _Response(output=_Output(video_url="http://127.0.0.1:8009/dummy.mp4"))
PY

if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "ffmpeg is required to generate a dummy video." >&2
    exit 1
fi

if [ ! -f "${VIDEO_PATH}" ]; then
    ffmpeg -f lavfi -i color=black:s=320x240:d=1 -c:v libx264 -pix_fmt yuv420p "${VIDEO_PATH}" -y >/dev/null 2>&1
fi

cat <<EOF
DashScope mock is ready:
  MOCK_ROOT=${MOCK_ROOT}
  MOCK_PORT=${MOCK_PORT}

Next steps (in another terminal):
  cd backend
  PYTHONPATH=${MOCK_ROOT} ./run_dev.sh

Start React frontend:
  cd frontend
  npm run dev
EOF

if [ "${1:-}" = "--serve" ] || [ "${1:-}" = "" ]; then
    echo ""
    echo "Starting mock video server on http://127.0.0.1:${MOCK_PORT}"
    python -m http.server "${MOCK_PORT}" --directory "${MOCK_ROOT}"
fi
