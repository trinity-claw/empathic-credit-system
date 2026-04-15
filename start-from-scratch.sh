#!/usr/bin/env bash
# Bootstrap data + train API models (notebooks 02–04), then start the full stack
# like start.sh. Use on a fresh clone or any machine without models/*.pkl.
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

ROOT="$(cd "$(dirname "$0")" && pwd)"
export PATH="$HOME/.local/bin:$PATH"
export MPLBACKEND=Agg

ok()   { echo -e "${GREEN}✓${NC}  $1"; }
info() { echo -e "${CYAN}→${NC}  $1"; }
warn() { echo -e "${YELLOW}!${NC}  $1"; }
fail() { echo -e "${RED}✗${NC}  $1"; exit 1; }
header() { echo -e "\n${BOLD}$1${NC}"; }

header "═══════════════════════════════════════════════════════════"
header "  Empathic Credit System — START FROM SCRATCH (bootstrap)  "
header "═══════════════════════════════════════════════════════════"

header "0. Dependências"
command -v docker &>/dev/null  || fail "Docker não encontrado."
command -v node   &>/dev/null  || fail "Node.js não encontrado."
command -v uv     &>/dev/null  || fail "uv não encontrado. Execute: curl -LsSf https://astral.sh/uv/install.sh | sh"
ok "Docker, Node e uv encontrados"

cd "$ROOT"
info "Instalando dependências Python (uv sync)…"
uv sync
ok "uv sync"

if [[ ! -f "$ROOT/.env" ]]; then
  info "Criando .env a partir de .env.example…"
  cp "$ROOT/.env.example" "$ROOT/.env"
  warn "Revise REDIS_URL em .env se não usar Redis em localhost:6379."
  ok ".env criado"
fi

mkdir -p "$ROOT/data/raw" "$ROOT/data/processed" "$ROOT/models"

RAW_CSV="$ROOT/data/raw/cs-training.csv"
if [[ ! -f "$RAW_CSV" ]]; then
  header "1. Dataset bruto (OpenML 46929 → cs-training.csv)"
  info "Baixando ~150k linhas (pode levar 1–3 min)…"
  uv run python - <<'PY'
from pathlib import Path

from sklearn.datasets import fetch_openml

out = Path("data/raw/cs-training.csv")
out.parent.mkdir(parents=True, exist_ok=True)
df = fetch_openml(data_id=46929, as_frame=True).frame
df.to_csv(out)
print(f"Wrote {out} ({len(df):,} rows)")
PY
  ok "CSV salvo em data/raw/cs-training.csv"
else
  ok "Dataset já existe em data/raw/cs-training.csv"
fi

header "2. Splits estratificados (parquets em data/processed/)"
uv run python -m src.data.split
ok "Train/val/test gerados"

header "3. Treino dos modelos da API (nbconvert — notebooks 02, 03, 04)"
cd "$ROOT/notebooks"
NB_TIMEOUT="${ECS_NB_TIMEOUT:-3600}"
for nb in 02_baseline_logreg 03_xgboost 04_emotional_features; do
  info "Executando ${nb}.ipynb (timeout ${NB_TIMEOUT}s)…"
  uv run python -m jupyter nbconvert \
    --to notebook \
    --execute \
    --Execute.timeout="${NB_TIMEOUT}" \
    --output "/tmp/ecs_${nb}_executed.ipynb" \
    "${nb}.ipynb"
  ok "${nb}.ipynb concluído"
done
cd "$ROOT"

header "4. Verificando artefatos esperados pela API"
need=(
  "$ROOT/models/xgboost_financial.pkl"
  "$ROOT/models/xgboost_financial_calibrator.pkl"
  "$ROOT/models/xgboost_emotional.pkl"
  "$ROOT/models/xgboost_emotional_calibrator.pkl"
)
for f in "${need[@]}"; do
  [[ -f "$f" ]] || fail "Arquivo ausente após treino: $f"
done
ok "Todos os pickles da API estão presentes em models/"

header "5. Frontend — dependências npm"
cd "$ROOT/frontend"
if [[ ! -d node_modules ]]; then
  info "npm install…"
  npm install
  ok "node_modules instalado"
else
  ok "node_modules já existe (npm install pulado)"
fi
cd "$ROOT"

header "6. Subindo aplicação (Redis + API + worker + Next.js)"
info "Alinhando .env aos pickles recém-gerados…"
uv run python "$ROOT/scripts/normalize_env.py" || true
info "Delegando para start.sh…"
exec "$ROOT/start.sh"
