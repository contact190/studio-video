#!/usr/bin/env bash
# Installe le moteur Studio Vidéo dans une session neuve (2 à 4 minutes).
#   bash setup.sh            : analyse + montage
#   bash setup.sh --voice    : + voix off gratuite (Kokoro, ~350 Mo)
#   bash setup.sh --rea      : + rea-video (mode Atelier)
set -e
cd "$(dirname "$0")"
MODELS="${STUDIO_MODELS:-/tmp/studio-models}"
mkdir -p "$MODELS"
REL=https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models
TTS=https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models

command -v ffmpeg >/dev/null || { echo "ffmpeg manquant"; exit 1; }
python3 -m pip install -q --break-system-packages numpy scipy pillow sherpa-onnx soundfile 2>/dev/null \
  || python3 -m pip install -q numpy scipy pillow sherpa-onnx soundfile

[ -f "$MODELS/silero_vad.onnx" ] || curl -sSL -o "$MODELS/silero_vad.onnx" "$REL/silero_vad.onnx"
if [ ! -d "$MODELS/sherpa-onnx-whisper-small" ]; then
  curl -sSL "$REL/sherpa-onnx-whisper-small.tar.bz2" | tar xj -C "$MODELS"
fi
if [[ " $* " == *" --voice "* ]] && [ ! -d "$MODELS/kokoro-multi-lang-v1_0" ]; then
  curl -sSL "$TTS/kokoro-multi-lang-v1_0.tar.bz2" | tar xj -C "$MODELS"
fi
if [[ " $* " == *" --rea "* ]] && [ ! -d /tmp/rea-video ]; then
  git clone -q --depth 1 https://github.com/JuneYaooo/rea-video.git /tmp/rea-video
  python3 -m venv /tmp/rea-video/.venv && /tmp/rea-video/.venv/bin/pip install -q -e "/tmp/rea-video[ocr]"
  # version sans écran d'OpenCV (pas d'affichage dans la session)
  /tmp/rea-video/.venv/bin/pip uninstall -y -q opencv-python 2>/dev/null || true
  /tmp/rea-video/.venv/bin/pip install -q --force-reinstall --no-deps "opencv-python-headless>=4.8,<5"
fi

(cd render && npm install --no-audit --no-fund --silent)
if ! command -v google-chrome >/dev/null && ! command -v chromium >/dev/null; then
  (cd render && npx remotion browser ensure >/dev/null)
fi
echo "Studio Vidéo prêt. Modèles : $MODELS"
