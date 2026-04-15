# Roteiro da Apresentação — Empathic Credit System

**Duração**: 30 minutos
**Formato**: Compartilhamento de tela + demo ao vivo
**Audiência**: Pablo (CEO), Leonardo, equipe de engenharia

---

## 1. Abertura (2 min)

### O que falar

"Eu construí um sistema completo de credit scoring que:
- Treina um modelo XGBoost que atinge **AUC 0.87** e **KS 0.58** em dados de teste não vistos durante o treino
- Provou experimentalmente que features emocionais **não agregam valor preditivo** (delta de AUC = -0.0008) e recomendou contra o deploy
- Implementa análise de impacto disparatado usando a **regra dos 4/5** — um requisito regulatório para decisões automatizadas de crédito
- Serve predições via FastAPI com **explicações SHAP em toda resposta**, trilha de auditoria completa e deploy assíncrono de crédito"

### Mostrar

- Tabela de resultados no README.md (3 modelos lado a lado)
- Frase-chave: "Toda decisão que esse sistema toma é explicável e auditável."

---

## 2. Arquitetura do Sistema (5 min)

### O que falar

"A arquitetura começa onde o desafio pede: no cérebro do cliente. O app mobile captura leituras do sensor emocional — estresse, impulsividade, estabilidade — e faz stream para nossa API via `POST /emotions/stream`. Esses eventos são persistidos no banco de dados e publicados no Redis Pub/Sub para consumidores downstream.

Quando uma avaliação de crédito é solicitada, a API roda o modelo XGBoost, calibra a probabilidade, mapeia para um produto de crédito (limite, taxa, tipo), gera explicações SHAP e retorna tudo em uma resposta. Se aprovado, uma oferta de crédito é criada. O usuário pode aceitar, o que dispara um job assíncrono via rq que atualiza o perfil e envia uma notificação.

Toda requisição recebe um ID de correlação via middleware X-Request-ID. Todo evento do ciclo de vida é logado na tabela credit_events."

### Mostrar

- Diagrama de arquitetura no README (ASCII completo do cérebro até notificação)
- `docker-compose.yml` — 4 serviços: api, worker, redis, dashboard
- Scroll rápido pelo `src/api/main.py` — os endpoints

### Números para citar

- 7 endpoints de API
- 7 tabelas no banco de dados
- X-Request-ID em toda requisição/resposta com duration_ms

---

## 3. Pipeline de ML (8 min)

### 3a. Dataset e EDA (2 min)

"O dataset é o Give Me Some Credit do Kaggle/OpenML — 150.000 tomadores de crédito com taxa de inadimplência de 6,68%. Desbalanceamento forte. Principais achados da EDA:
- `monthly_income` tem ~20% de valores ausentes
- `dependents` tem ~2,6% de missing
- Valores sentinela 96/98 nas colunas de past_due (269 linhas) — eu sinalizei com uma feature binária `had_past_due_sentinel`
- `revolving_utilization` tem outliers extremos (máximo > 50.000) por problemas de qualidade dos dados"

### Mostrar

- `notebooks/01_eda.ipynb` — gráficos de distribuição, tabela de missing values

### 3b. Baseline (2 min)

"Comecei com Regressão Logística como baseline — Pipeline com SimpleImputer(mediana) + StandardScaler + LogReg(class_weight=balanced). Obtive **AUC 0.82** na validação. Os coeficientes fazem sentido intuitivo: variáveis de past_due aumentam o risco, idade e renda diminuem. Isso confirmou que os dados estão limpos e o target está bem definido."

### Mostrar

- `notebooks/02_baseline_logreg.ipynb` — gráfico de barras dos coeficientes
- Destacar: "Esses coeficientes batem com a intuição de risco de crédito — se não batessem, teríamos um problema nos dados."

### 3c. XGBoost + Calibração (2 min)

"O XGBoost levou o AUC para **0.87** na validação. Mas as probabilidades brutas do XGBoost são mal calibradas — Brier score 0.055 bruto vs **0.049 após calibração com IsotonicRegression**. A curva de calibração foi de um S para quase diagonal.

Usei regressão isotônica ao invés de Platt scaling porque a relação entre probabilidades brutas e frequências reais é não-linear para ensembles de árvores. O calibrador foi ajustado nos dados de validação e a avaliação final foi feita em um conjunto de teste separado para confirmar que não houve overfitting."

### Números para citar

| Métrica | Baseline LogReg | XGBoost Bruto | XGBoost Calibrado |
|---------|----------------|---------------|-------------------|
| AUC     | 0.8216         | 0.8676        | 0.8676            |
| KS      | 0.5012         | 0.5764        | 0.5764            |
| Brier   | 0.1545         | 0.0550        | 0.0488            |

### Mostrar

- `notebooks/03_xgboost.ipynb` — plot de 4 painéis (ROC, KS, calibração, matriz de confusão)
- Resultados no conjunto de teste no final

### 3d. SHAP (2 min)

"Toda predição vem com valores SHAP computados pelo TreeExplainer — valores de Shapley exatos em tempo O(TLD) onde T é o número de árvores, L é folhas e D é profundidade. Não é uma aproximação.

Os top 5 fatores de risco são retornados por requisição. O base value + soma de todos os SHAP values = predição do modelo no espaço de log-odds. Isso nos dá explicações legalmente defensáveis — o Artigo 20 da LGPD exige o direito à explicação para decisões automatizadas."

### Mostrar

- `notebooks/05_shap_analysis.ipynb` — summary plot (global) + waterfall (individual)
- JSON da resposta da API mostrando `shap_explanation` e `top_factors`

---

## 4. Análise Ética (5 min)

### 4a. Experimento com Features Emocionais (3 min)

"O desafio pede para usar dados emocionais. Eu levei isso a sério — gerei features emocionais sintéticas que são correlacionadas com comportamento financeiro (estresse correlaciona com inadimplência, impulsividade com utilização de crédito) mas ruidosas o suficiente para que R² < 0,30 contra as financeiras.

Resultado: o modelo emocional atingiu AUC **0.8668** vs AUC do financial-only de **0.8676**. Delta de **-0.0008** — as features emocionais pioraram ligeiramente. SHAP confirma: as features emocionais têm valores SHAP próximos de zero comparadas com past_due_90, revolving_utilization e age.

Minha recomendação: **não fazer deploy das features emocionais**. O custo regulatório e de privacidade é alto (LGPD Artigo 11 — dados sensíveis), o custo técnico é não-trivial (stream de sensores em tempo real, gestão de consentimento) e o benefício preditivo é zero."

### Mostrar

- `notebooks/04_emotional_features.ipynb` — tabela de comparação lado a lado
- Summary plot do SHAP mostrando features emocionais no fundo
- `docs/model_card.md` — seção de análise ética

### 4b. Fairness (2 min)

"Implementei análise de impacto disparatado usando a regra dos 4/5: a taxa de aprovação de qualquer subgrupo precisa ser pelo menos 80% da taxa do grupo com maior aprovação. Testei em coortes de idade e quartis de renda.

Idade: todos os coortes passam. Renda: Q1 está no limite com ~82% da taxa de Q4 — algo para monitorar em produção com dados reais. Também verifiquei a calibração por subgrupo: o modelo está bem calibrado em todos os coortes.

Isso não é apenas um checkbox — a InfinitePay opera sob regulação do BACEN, e a LGPD exige demonstração de fairness para decisões financeiras automatizadas."

### Mostrar

- `notebooks/06_fairness_analysis.ipynb` — gráficos de barras da regra dos 4/5
- Página de Fairness no dashboard Streamlit

---

## 5. Backend em Detalhe (5 min)

### 5a. Design da API (2 min)

"Sete endpoints, todos protegidos por HTTP Basic Auth com comparação em tempo constante (`secrets.compare_digest`). Pydantic v2 para toda validação de entrada/saída — os docs OpenAPI são gerados automaticamente em `/docs`.

O endpoint de avaliação de crédito faz: prever → calibrar → mapear para produto de crédito → gerar SHAP → criar oferta → persistir no banco → logar eventos de auditoria → responder. Tudo síncrono, ~50ms por requisição com modelos pré-carregados no startup.

Avaliação assíncrona disponível via rq para cargas batch. Aceitação da oferta dispara um job de deployment separado."

### Mostrar

- `http://localhost:8000/docs` — Swagger UI
- `src/api/schemas.py` — modelos CreditRequest, CreditResponse

### 5b. Banco de Dados (1 min)

"Sete tabelas: users, transactions, emotional_events, credit_offers, notifications, credit_evaluations, credit_events. Foreign keys e índices. A trilha de auditoria captura cada evento do ciclo de vida com timestamps."

### Mostrar

- Seção Database Schema no README com queries SQL de exemplo

### 5c. Observabilidade (1 min)

"Logging JSON estruturado via python-json-logger. Middleware X-Request-ID em toda requisição com method, path, status_code, duration_ms. O log_level é configurável via variável de ambiente."

### 5d. Docker (1 min)

"Quatro serviços no docker-compose: API, rq worker, Redis, dashboard Streamlit. Healthcheck na API e no Redis. Dockerfile com imagem slim."

---

## 6. Demo ao Vivo (3 min)

### Passos

1. **Iniciar**: `docker compose up --build` (ou mostrar já rodando)
2. **Health check**: `curl http://localhost:8000/health`
3. **Avaliação de crédito**:
```bash
curl -X POST http://localhost:8000/credit/evaluate \
  -u admin:changeme \
  -H "Content-Type: application/json" \
  -d '{"revolving_utilization":0.3,"age":45,"debt_ratio":0.2,"monthly_income":5000,"open_credit_lines":4,"past_due_30_59":0,"past_due_60_89":0,"past_due_90":0,"real_estate_loans":1,"dependents":2,"had_past_due_sentinel":0}'
```
4. **Mostrar resposta**: destacar decision, score, credit_limit, interest_rate, offer_id, shap_explanation, top_factors
5. **Aceitar oferta**: `curl -X POST http://localhost:8000/credit/offers/{offer_id}/accept -u admin:changeme`
6. **Stream emocional**: `curl -X POST http://localhost:8000/emotions/stream -u admin:changeme -H "Content-Type: application/json" -d '{"stress_level":0.7,"impulsivity_score":0.4}'`
7. **Dashboard**: abrir `http://localhost:8501` — mostrar páginas de Score Distribution e SHAP Explorer

---

## 7. Decisões de Design (2 min)

### O que falar

"Três trade-offs principais:

1. **SQLite ao invés de Postgres**: O desafio diz 'banco de dados à sua escolha'. SQLite nos dá transações ACID com zero ops. Em produção: Postgres com read replicas e row-level security.

2. **rq ao invés de Celery**: Uma variável de configuração (REDIS_URL) vs 4+ do Celery com modos de falha silenciosa. Mesma semântica, risco de integração dramaticamente menor. Em produção em escala: Kafka para event sourcing.

3. **Redis Pub/Sub ao invés de Kafka para stream emocional**: Kafka provê durabilidade e replay que Pub/Sub não tem. Mas adicionar um quarto componente de infraestrutura a um case study adiciona risco sem demonstrar nada novo arquiteturalmente. O código é idêntico — troca uma função no worker.py.

A meta-decisão: eu otimizei para **confiabilidade de entrega** ao invés de **impressionar pelo stack**. Cada componente funciona end-to-end. Nada está meio implementado."

---

## Fechamento

"Esse sistema avalia 150.000 tomadores de crédito com AUC 0.87, explica cada decisão com SHAP, prova experimentalmente que features emocionais não ajudam, implementa checks regulatórios de fairness e roda em Docker com um único comando. Perguntas?"

---

## Resumo de Timing

| Seção | Duração | Acumulado |
|-------|---------|-----------|
| Abertura | 2 min | 2 min |
| Arquitetura | 5 min | 7 min |
| Pipeline de ML | 8 min | 15 min |
| Análise Ética | 5 min | 20 min |
| Backend | 5 min | 25 min |
| Demo ao Vivo | 3 min | 28 min |
| Decisões de Design | 2 min | 30 min |
