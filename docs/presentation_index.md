# Índice de apresentação (10–15 min)

Use este arquivo como cola seca: cada bloco liga **requisito do case** → **o que mostrar** → **onde está no repo**.

| Min | Requisito (CHALLENGE) | O que mostrar | Evidência no repo |
|-----|------------------------|---------------|-------------------|
| 0–1 | Arquitetura, health | `./start.sh` ou `docker compose`, `GET /health` e `GET /healthz`, `X-Request-ID` | [`README.md`](../README.md), [`src/api/main.py`](../src/api/main.py) |
| 1–3 | API + ML + limite | `POST /credit/evaluate` perfil negado → SHAP + `DENIED`; perfil limpo → `APPROVED` + produto | [`docs/demo_guide.md`](demo_guide.md) PARTE 2, [`src/api/model_store.py`](../src/api/model_store.py) |
| 3–5 | Banco + queries | DBeaver em `data/ecs.db`; 5 queries do README após curls de pré-requisito | [`README.md`](../README.md) seção SQL |
| 5–6 | Emoção + stream | `POST /emotions/stream` → linha em `emotional_events`; Pub/Sub Redis | [`src/api/main.py`](../src/api/main.py), [`src/api/worker.py`](../src/api/worker.py) |
| 6–8 | Assíncrono | Aceitar oferta → fila rq → notificação; deixar claro: async **evaluate** não persiste no SQLite | [`src/api/worker.py`](../src/api/worker.py), [`README.md`](../README.md) |
| 8–10 | Observabilidade | Logs JSON no STDOUT, correlacionar `request_id` | [`src/api/main.py`](../src/api/main.py) |
| 10–12 | Ética / LGPD | Modelo emocional não deployado; Art. 11 vs ganho AUC | [`docs/model_card.md`](model_card.md) |
| 12–15 | Design trade-offs | SQLite, rq, Redis Pub/Sub vs produção | [`README.md`](../README.md) Design Decisions |

## Frases que provam domínio (decore o conceito, não o texto)

- **Calibração:** probabilidade precisa refletir taxa observada; isotônica no pipeline servido.
- **SHAP TreeExplainer:** contribuições exatas para árvores, não aproximação por amostragem.
- **Async vs sync:** decisão auditada e histórico no dashboard vêm do `POST /credit/evaluate` síncrono; async de avaliação é demonstração de fila sem escrita duplicada no worker.
- **Por que não emocional:** delta AUC desprezível e custo regulatório de dado sensível (LGPD Art. 11).

## Perguntas difíceis (respostas de uma linha)

Ver respostas estendidas em [`docs/demo_guide.md`](demo_guide.md) PARTE 3. Resumo:

| Pergunta | Resposta curta |
|----------|------------------|
| Onde está o `user_id`? | Fluxo request-centric; em produção viria do token, não do escopo do case. |
| Async persiste avaliação? | Não hoje; persistência e audit trail no caminho síncrono. |
| Por que SQLite? | Zero ops para o case; `DATABASE_URL` aponta para Postgres em produção. |
| Onde está o consumidor Kafka? | Pub/Sub Redis com publisher; consumidor seria serviço separado em produção. |

## Checklist antes de gravar

1. `uv run pytest` (ou `make test`) verde.
2. Subir API + Redis + worker (`./start.sh` ou compose).
3. Executar pré-requisitos A e B do README e rodar as 5 queries no DBeaver.
4. Fazer 5+ avaliações mistas para KPIs no dashboard ([`docs/demo_guide.md`](demo_guide.md) final).
