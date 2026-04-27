#!/usr/bin/env bash
# One-shot copy of pretrained models and MovieLens-1M raw data from the source
# recsys repo into this backend tree. Run once before `docker build`.
#
# Override the source path by exporting ISA_RECSYS_SRC before invoking, e.g.:
#   ISA_RECSYS_SRC=/path/to/ISA_movielens_recsys bash backend/scripts/copy-assets.sh

set -euo pipefail

ISA_RECSYS_SRC="${ISA_RECSYS_SRC:-/home/ptomco/School/5-year/LS/ISA/ISA_movielens_recsys}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

MODELS_SRC="${ISA_RECSYS_SRC}/models"
DATA_SRC="${ISA_RECSYS_SRC}/data/raw/ml-1m"

MODELS_DST="${BACKEND_DIR}/models"
DATA_DST="${BACKEND_DIR}/data/ml-1m"

if [ ! -d "${ISA_RECSYS_SRC}" ]; then
  echo "ERROR: ISA_RECSYS_SRC does not exist: ${ISA_RECSYS_SRC}" >&2
  echo "Set ISA_RECSYS_SRC to the path of the source recsys repository." >&2
  exit 1
fi

mkdir -p "${MODELS_DST}" "${DATA_DST}"

echo "Copying models from ${MODELS_SRC}/ → ${MODELS_DST}/"
cp "${MODELS_SRC}/svd_model.pkl"        "${MODELS_DST}/"
cp "${MODELS_SRC}/cold_start_model.pkl" "${MODELS_DST}/"

echo "Copying MovieLens-1M raw data from ${DATA_SRC}/ → ${DATA_DST}/"
cp "${DATA_SRC}/movies.dat"  "${DATA_DST}/"
cp "${DATA_SRC}/users.dat"   "${DATA_DST}/"
cp "${DATA_SRC}/ratings.dat" "${DATA_DST}/"

echo "Done. ${MODELS_DST} and ${DATA_DST} are now populated."
