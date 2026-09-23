#!/usr/bin/env bash
# Builds every generated asset the showcase composition needs, into composition/assets/.
# None of them are committed: the clips are cut from real recordings, the voice is
# synthesised from voiceover.txt, and the fonts, music and effects are copied in.
#
#   HYPERFRAMES_PYTHON=<python with kokoro-onnx and soundfile> \
#   BRAG_ASSETS=<brag plugin skills/brag/assets> \
#   bash brag-output/clausecam-showcase/prepare.sh
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
OUT="$HERE/composition/assets"
CAPTURE="$HERE/capture.webm"
WALK="$REPO/demo/clausecam-walkthrough.webm"
: "${BRAG_ASSETS:?set BRAG_ASSETS to the skills/brag/assets directory of the brag plugin}"
: "${HYPERFRAMES_PYTHON:?set HYPERFRAMES_PYTHON to a python with kokoro-onnx and soundfile}"
export HYPERFRAMES_PYTHON

mkdir -p "$OUT"/{clips,vo,fonts,music,sfx}

# Shots: id, source, offset into the source (s), length (s). The composition places them.
# Offsets were read from the 2026-09-23 recordings; a fresh recording moves them.
while read -r id src start dur; do
  case "$src" in capture) f="$CAPTURE" ;; walk) f="$WALK" ;; esac
  ffmpeg -nostdin -loglevel error -y -ss "$start" -t "$dur" -i "$f" -an -r 30 \
    -c:v libx264 -preset fast -crf 16 -pix_fmt yuv420p "$OUT/clips/$id.mp4"
done <<'EOF'
sh01 capture 3.6 8.3
sh02 capture 11.9 3.5
sh03 capture 28.9 4.4
sh04 capture 18.8 4.6
sh05 capture 29.0 1.6
sh06 capture 36.9 6.2
sh07 walk 31.0 3.8
sh08 walk 94.6 5.0
sh09 walk 166.6 5.8
sh10 walk 238.8 5.4
sh11 walk 253.6 7.6
sh12 walk 276.0 4.5
sh13 walk 287.0 3.7
sh14 walk 1.0 7.0
EOF
# The landing page's final frame, held under the close.
ffmpeg -nostdin -loglevel error -y -ss 8.3 -i "$WALK" -frames:v 1 "$OUT/clips/close-still.png"

# Voice: one file per line of voiceover.txt, Kokoro af_heart, loudness-normalised.
i=0
while IFS= read -r line; do
  raw="$OUT/vo/raw$(printf %02d "$i").wav"
  npx --yes hyperframes@0.8.50 tts "$line" --voice af_heart --output "$raw" </dev/null >/dev/null
  ffmpeg -nostdin -loglevel error -y -i "$raw" -af loudnorm=I=-16:TP=-1.5:LRA=11 -ar 48000 \
    "$OUT/vo/vo$(printf %02d "$i").wav"
  rm "$raw"
  i=$((i + 1))
done <"$HERE/voiceover.txt"

cp "$REPO"/fnt/public/fonts/{BricolageGrotesque-Variable,IBMPlexSans-SemiBold,IBMPlexMono-Medium}.woff2 "$OUT/fonts/"
cp "$BRAG_ASSETS/music/happy-beats-business-moves-vol-12-by-ende-dot-app.mp3" "$OUT/music/"
for s in impact/impactSoft_medium_001 interface/drop_001 interface/drop_002 interface/click_003 interface/bong_001; do
  cp "$BRAG_ASSETS/sfx/$s.ogg" "$OUT/sfx/"
done
echo "assets ready in $OUT"
