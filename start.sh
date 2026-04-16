#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

ROOT="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$ROOT/.logs"
mkdir -p "$LOG_DIR"

ok()   { echo -e "${GREEN}✓${NC}  $1"; }
info() { echo -e "${CYAN}→${NC}  $1"; }
warn() { echo -e "${YELLOW}!${NC}  $1"; }
fail() { echo -e "${RED}✗${NC}  $1"; exit 1; }
header() { echo -e "\n${BOLD}$1${NC}"; }

cleanup() {
  header "Desligando serviços..."
  [[ -f "$LOG_DIR/uvicorn.pid" ]] && kill "$(cat "$LOG_DIR/uvicorn.pid")" 2>/dev/null && ok "API parada"
  [[ -f "$LOG_DIR/worker.pid"  ]] && kill "$(cat "$LOG_DIR/worker.pid")"  2>/dev/null && ok "Worker parado"
  [[ -f "$LOG_DIR/frontend.pid" ]] && kill "$(cat "$LOG_DIR/frontend.pid")" 2>/dev/null && ok "Frontend parado"
  docker stop ecs-redis 2>/dev/null && ok "Redis parado" || true
}
trap cleanup EXIT INT TERM

header "═══════════════════════════════════════"
header "    Empathic Credit System — START     "
header "═══════════════════════════════════════"

# ── 0. Dependências ───────────────────────────────────────────
header "Verificando dependências..."

command -v docker &>/dev/null  || fail "Docker não encontrado. Instale em https://docs.docker.com/get-docker/"
command -v node   &>/dev/null  || fail "Node.js não encontrado."
export PATH="$HOME/.local/bin:$PATH"
command -v uv     &>/dev/null  || fail "uv não encontrado. Execute: curl -LsSf https://astral.sh/uv/install.sh | sh"
ok "Docker, Node e uv encontrados"

# ── 1. Redis ──────────────────────────────────────────────────
header "Iniciando Redis..."
if docker ps --format '{{.Names}}' | grep -q '^ecs-redis$'; then
  ok "Redis já está rodando"
else
  docker rm -f ecs-redis 2>/dev/null || true
  docker run -d --name ecs-redis -p 6379:6379 redis:7-alpine \
    --loglevel warning > /dev/null
  sleep 2
  docker exec ecs-redis redis-cli ping | grep -q PONG || fail "Redis não respondeu"
  ok "Redis iniciado (Docker, porta 6379)"
fi

# ── 2. FastAPI (uvicorn) ──────────────────────────────────────
header "Iniciando API (FastAPI)..."
pkill -f "uvicorn src.api.main" 2>/dev/null || true
sleep 1
cd "$ROOT"
info "Sincronizando .env com artefatos em models/ (se necessário)…"
uv run python "$ROOT/scripts/normalize_env.py"
ok "Checagem .env"

# Legacy exports can collide with CALIBRATOR_PATH from .env (pydantic-settings / extras).
unset CALIBRATION_PATH calibration_path 2>/dev/null || true

# Host-run API cannot resolve Docker service hostname "redis" (Compose-only DNS).
if [[ "${REDIS_URL:-}" == redis://redis:* ]]; then
  export REDIS_URL="redis://127.0.0.1:${REDIS_URL#redis://redis:}"
  info "REDIS_URL ajustado para 127.0.0.1 (hostname redis só existe na rede Docker)."
fi

uv run uvicorn src.api.main:app --host 0.0.0.0 --port 8000 \
  >> "$LOG_DIR/api.log" 2>&1 &
echo $! > "$LOG_DIR/uvicorn.pid"

info "Aguardando API subir..."
for i in $(seq 1 15); do
  sleep 1
  curl -sf http://localhost:8000/health > /dev/null 2>&1 && break
  [[ $i == 15 ]] && { cat "$LOG_DIR/api.log" | tail -20; fail "API não subiu em 15s"; }
done
ok "API rodando em http://localhost:8000"

# ── 3. rq worker ─────────────────────────────────────────────
header "Iniciando worker (rq)..."
pkill -f "rq worker credit_eval" 2>/dev/null || true
sleep 1
cd "$ROOT"
uv run rq worker credit_eval --url redis://localhost:6379 \
  >> "$LOG_DIR/worker.log" 2>&1 &
echo $! > "$LOG_DIR/worker.pid"
sleep 2
ok "Worker escutando na fila credit_eval"

# ── 4. Frontend (Next.js) ─────────────────────────────────────
header "Iniciando Frontend (Next.js)..."
pkill -f "next dev" 2>/dev/null || true
sleep 1
cd "$ROOT/frontend"
npm run dev >> "$LOG_DIR/frontend.log" 2>&1 &
echo $! > "$LOG_DIR/frontend.pid"

info "Aguardando frontend subir..."
for i in $(seq 1 20); do
  sleep 1
  curl -sf http://localhost:3000 > /dev/null 2>&1 && break
  [[ $i == 20 ]] && { cat "$LOG_DIR/frontend.log" | tail -20; fail "Frontend não subiu em 20s"; }
done
ok "Frontend rodando em http://localhost:3000"

# ── 5. Status final ───────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}╔═══════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║       Sistema 100% operacional        ║${NC}"
echo -e "${BOLD}${GREEN}╚═══════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${CYAN}Dashboard${NC}   → http://localhost:3000"
echo -e "  ${CYAN}API Docs${NC}    → http://localhost:8000/docs"
echo -e "  ${CYAN}API Health${NC}  → http://localhost:8000/health"
echo ""
echo -e "  Logs em: ${YELLOW}.logs/${NC}"
echo ""
echo -e "  ${YELLOW}Pressione Ctrl+C para encerrar tudo.${NC}"
echo ""

# Aguarda indefinidamente (Ctrl+C dispara cleanup)
wait
