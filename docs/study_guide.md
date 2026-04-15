# Guia de Estudo — Empathic Credit System

Preparação técnica para apresentação e perguntas do Pablo.

---

## 1. Fundamentos de ML

### 1.1 XGBoost

**O que é**: Ensemble de árvores de decisão treinadas sequencialmente, onde cada nova árvore corrige os erros residuais das anteriores (gradient boosting).

**Por que é bom para crédito**:
- Lida com missing values nativamente (aprende a direção ótima para dados ausentes)
- Robusto a outliers (divisões em árvores são baseadas em ranking, não em magnitude)
- Feature importance built-in
- Regularização L1/L2 nos pesos das folhas previne overfitting

**Hiperparâmetros que usei e por quê**:
- `max_depth=6`: Profundidade moderada. Muito raso (3-4) perde interações; muito fundo (>8) memoriza ruído
- `learning_rate=0.1`: Taxa de aprendizado padrão. Menor = mais árvores necessárias mas melhor generalização
- `n_estimators=300`: Quantidade de árvores. Suficiente para convergir sem overfitting com early stopping
- `scale_pos_weight=14`: Razão negativo/positivo (~93.3%/6.7% ≈ 14). Compensa o desbalanceamento
- `eval_metric=auc`: Otimiza diretamente para a métrica de interesse

**Perguntas que podem fazer**:
- *"Por que não Random Forest?"* — RF treina árvores independentes (bagging). XGBoost treina sequencialmente corrigindo erros. Em dados tabulares estruturados, boosting consistentemente supera bagging. Benchmark do paper original mostra isso em 70+ datasets.
- *"Por que não deep learning?"* — Para dados tabulares com <1M linhas, XGBoost/LightGBM superam redes neurais na maioria dos benchmarks. Deep learning brilha em dados não-estruturados (imagens, texto, áudio).

### 1.2 Métricas

**AUC-ROC (Area Under the Receiver Operating Characteristic)**
- Mede a capacidade do modelo de ranquear: dado um bom pagador e um mau pagador aleatórios, qual a probabilidade de o modelo atribuir um score maior ao mau?
- AUC = 0.5 → modelo aleatório. AUC = 1.0 → modelo perfeito.
- Para crédito: 0.75+ é decente, 0.80+ é bom, 0.85+ é excelente.
- **Nosso resultado**: 0.87 no teste.

**KS (Kolmogorov-Smirnov)**
- Máxima distância entre as distribuições acumuladas (CDFs) dos scores de bons e maus pagadores.
- Métrica padrão do mercado brasileiro de crédito (BACEN a menciona em guias de risco).
- KS > 30 → aceitável. KS > 40 → bom. KS > 50 → excelente.
- **Nosso resultado**: 0.58 (58 pontos) no teste.

**Brier Score**
- MSE entre a probabilidade prevista e o resultado real. Mede calibração.
- Menor = melhor. Um modelo pode ter AUC alto mas Brier ruim (ranqueia bem mas as probabilidades são descalibradas).
- **Nosso resultado**: 0.049 após calibração (vs 0.055 bruto).
- Importa porque usamos a probabilidade para definir limite de crédito e taxa de juros.

**Precision@base_rate**
- "Se eu pegar os top 6,68% com maior score de risco, quantos realmente são maus pagadores?"
- Simula a operação real: o negócio define uma taxa de rejeição e quer saber a qualidade dessa seleção.

### 1.3 Calibração

**O problema**: XGBoost produz scores que ranqueiam bem (AUC alto) mas não são probabilidades verdadeiras. Se o modelo diz 30% de risco, a frequência real de default pode ser 15% ou 45%.

**Por que importa**: Usamos a probabilidade para definir limite de crédito e taxa de juros. Se a probabilidade é descalibrada, os limites ficam errados.

**IsotonicRegression vs Platt Scaling**:
- Platt (sigmoide): assume relação linear no log-odds entre score bruto e probabilidade real. Funciona bem para SVMs.
- Isotônica: não assume formato funcional, apenas que a relação é monotônica. Melhor para ensembles de árvores onde a relação é irregular.
- Usei isotônica porque o XGBoost tem relação não-linear entre scores brutos e frequências reais.

**Cuidado com data leakage**: O calibrador foi ajustado nos dados de validação, e a avaliação final foi feita no conjunto de teste. Se calibrar e avaliar no mesmo set, o Brier score fica otimista.

---

## 2. SHAP (SHapley Additive exPlanations)

### 2.1 Teoria

- Baseado nos valores de Shapley da teoria dos jogos cooperativos (Lloyd Shapley, Nobel 1962).
- Pergunta: "Quanto cada feature contribuiu para mover a predição deste indivíduo em relação à média?"
- Propriedades matemáticas únicas: eficiência (soma dos SHAP = diferença entre predição e base), simetria, linearidade, dummy.
- TreeExplainer: algoritmo exato em O(TLD) — não é amostragem ou aproximação.

### 2.2 Como usamos

- `base_value` (valor base) = log-odds médio do target no dataset de treino.
- `shap_values[i]` = contribuição da feature i para a predição.
- `base_value + sum(shap_values) = predição do modelo` (no espaço de log-odds).
- Na API, retornamos os top 5 fatores em linguagem natural: "revolving_utilization: +0.42 (aumenta risco)".

### 2.3 Visualizações

- **Summary plot** (global): Mostra a importância e direção de todas as features para todo o dataset.
- **Waterfall** (individual): Mostra como uma predição específica foi construída feature por feature.
- **Dependence plot**: Mostra a relação entre o valor de uma feature e sua contribuição SHAP. Útil para detectar não-linearidades e interações.

### 2.4 Perguntas que podem fazer

- *"SHAP é lento demais para produção?"* — TreeExplainer é exato e rápido para modelos de árvore. Para nosso modelo com ~300 árvores e 10 features, leva <5ms por predição. Já está na resposta da API.
- *"E se o cliente não entender valores SHAP?"* — A API traduz para linguagem natural: "Seu score foi reduzido principalmente por: histórico de atrasos >90 dias (impacto: +0.42 de risco)". O dashboard Streamlit visualiza isso graficamente.
- *"SHAP substitui regulação?"* — Não. SHAP é uma ferramenta de explicabilidade. A LGPD (Art. 20) exige o direito à explicação, mas não especifica o método. SHAP é um dos mais aceitos academicamente e regulatoriamente.

---

## 3. Risco de Crédito

### 3.1 Conceitos fundamentais

**PD (Probability of Default)**: Probabilidade de o cliente não pagar. É exatamente o que nosso modelo estima.

**LGD (Loss Given Default)**: Quanto o banco perde quando o cliente não paga (geralmente 40-60% do valor emprestado). Nosso sistema não modela LGD diretamente — assume LGD fixo para simplificação.

**EAD (Exposure at Default)**: Quanto o banco tem exposto quando ocorre o default. É o limite de crédito concedido.

**Expected Loss = PD × LGD × EAD**: Fórmula central de risco de crédito. O pricing do produto (taxa de juros) precisa cobrir o expected loss + custos operacionais + margem.

### 3.2 Nossa implementação de produto de crédito

Mapeamos o score (0-1000) para tiers:

| Score  | Limite     | Taxa mensal | Tipo       |
|--------|-----------|-------------|------------|
| 850+   | R$ 50.000 | 1,5%        | Longo prazo |
| 700-849| R$ 20.000 | 2,5%        | Longo prazo |
| 550-699| R$ 8.000  | 4,0%        | Curto prazo |
| <550   | R$ 2.000  | 6,0%        | Curto prazo |

**Por que essa estrutura**: Clientes de menor risco recebem mais crédito a taxas menores — incentivo correto. Clientes de maior risco recebem crédito limitado a taxas maiores — o spread compensa o risco. Abaixo do threshold, o crédito é negado.

### 3.3 Regulação brasileira

- **BACEN (Banco Central)**: Regula instituições financeiras. Resolução 4.557/2017 exige gestão de risco de crédito.
- **LGPD (Lei Geral de Proteção de Dados)**: Art. 20 — direito à revisão de decisões automatizadas. Art. 11 — dados sensíveis (emocionais se enquadram) exigem consentimento específico e finalidade comprovada.
- **Código de Defesa do Consumidor**: Art. 43 — direito de acesso às informações de cadastro e scores.
- **Cadastro Positivo (Lei 12.414/2011)**: Regulamenta o uso de dados de histórico de crédito para scoring.

---

## 4. Fairness e Ética

### 4.1 Regra dos 4/5

- Definição: A taxa de aprovação de qualquer subgrupo protegido deve ser pelo menos 80% da taxa de aprovação do grupo com maior taxa.
- Origem: EEOC (Equal Employment Opportunity Commission) dos EUA, adaptada para crédito.
- Aplicação no Brasil: Não é regulamentação explícita, mas é considerada boa prática regulatória pelo BACEN e pode ser exigida em auditorias.

### 4.2 Nossos resultados

- **Por idade**: Todos os coortes passam na regra dos 4/5.
- **Por renda**: Q1 (menor renda) está no limite com ~82% da taxa de Q4 (maior renda). Passa por pouco. Em produção, implementar monitoramento contínuo.

### 4.3 Features emocionais — por que não usar

1. **Sem ganho preditivo**: AUC cai 0.0008 com features emocionais. SHAP confirma contribuição desprezível.
2. **Risco regulatório**: LGPD Art. 11 classifica dados emocionais como sensíveis. Necessidade de consentimento explícito e finalidade comprovada.
3. **Risco de proxy**: Features emocionais podem servir como proxies para condições de saúde mental, criando discriminação indireta.
4. **Custo técnico sem retorno**: Infraestrutura de sensores, streaming em tempo real, gestão de consentimento — investimento pesado sem benefício.
5. **Recomendação**: Não fazer deploy. Documentar o experimento. Se dados emocionais reais (não sintéticos) estiverem disponíveis no futuro, reavaliar com o mesmo framework experimental.

### 4.4 Perguntas que podem fazer

- *"Mas o desafio pede para usar dados emocionais. Por que não usou?"* — "Eu implementei, experimentei e provei que não agrega valor. Entregar um sistema que usa dados sensíveis sem benefício preditivo não é ético nem regulatoriamente defensável. O experimento está documentado e reproduzível."
- *"E se os dados emocionais fossem reais e não sintéticos?"* — "Exatamente por isso documentei o framework experimental. Com dados reais, rodaríamos o mesmo pipeline: treinar com e sem, comparar métricas, analisar SHAP, verificar fairness. Se houver ganho real, implementamos com as proteções de privacidade adequadas."

---

## 5. Design do Sistema

### 5.1 Padrões arquiteturais

**Middleware de correlação**: Toda requisição recebe um X-Request-ID único. Esse ID acompanha o request através de logs, banco de dados e respostas. Permite rastreamento end-to-end.

**Event sourcing (simplificado)**: A tabela `credit_events` registra cada transição de estado: `EVALUATION_STARTED`, `EVALUATION_COMPLETED`, `OFFER_CREATED`, `OFFER_ACCEPTED`. Trilha de auditoria completa.

**Task queue pattern**: Operações pesadas (deploy de crédito) são enfileiradas no Redis e processadas pelo worker assíncrono. A API responde imediatamente com o job_id.

**Pub/Sub para streaming**: Eventos emocionais são publicados no Redis Pub/Sub para consumidores downstream. Desacoplamento entre ingestão e processamento.

### 5.2 Trade-offs que fiz

| Decisão | Por quê | Em produção |
|---------|---------|-------------|
| SQLite | Zero ops, ACID, suficiente para demonstração | Postgres com read replicas e RLS |
| rq | 1 config var vs 4+ do Celery, mesma semântica | Kafka para event sourcing em escala |
| Redis Pub/Sub | Simples, suficiente para demo | Kafka para durabilidade e replay |
| HTTP Basic Auth | Demonstra conceito de autenticação | OAuth2/JWT com RBAC |
| Modelos pré-carregados no startup | ~50ms por predição em vez de ~2s | Model serving separado (MLflow/Seldon) |

### 5.3 Perguntas que podem fazer

- *"Por que não usou Kafka?"* — "Kafka adiciona complexidade operacional (ZooKeeper/KRaft, topic management, consumer groups) sem demonstrar nada arquiteturalmente diferente neste contexto. Redis Pub/Sub prova o padrão. A migração é trocar uma função: `redis.publish()` → `kafka.send()`. O custo de risco de infraestrutura não justifica em um case study."
- *"Como escala?"* — "API é stateless — escala horizontal com load balancer. Workers rq escalam adicionando instâncias. O gargalo é o banco: SQLite → Postgres com read replicas resolve. Modelos ficam em memória no worker — cada worker carrega ~50MB."
- *"E monitoramento em produção?"* — "Adicionaria: métricas Prometheus (latência, taxa de erro, distribuição de scores), alertas para drift (PSI/CSI monitorando distribuição de features e scores), retreino automático quando drift > threshold, A/B testing para novos modelos."

---

## 6. LGPD — Pontos Críticos

### 6.1 Artigos relevantes

- **Art. 7**: Bases legais para tratamento. Para crédito: "proteção do crédito" (inciso X) é base legal, mas dados emocionais não se enquadram aqui.
- **Art. 11**: Dados sensíveis (saúde, dados biométricos — emocionais se enquadram). Tratamento apenas com consentimento específico e informado ou para finalidades específicas listadas.
- **Art. 18**: Direitos do titular — acesso, correção, portabilidade, eliminação.
- **Art. 20**: Direito à revisão de decisões automatizadas. O titular pode pedir explicação e revisão humana.
- **Art. 46**: Medidas de segurança — criptografia, pseudonimização, controle de acesso.

### 6.2 Como nosso sistema endereça LGPD

- **Explicabilidade (Art. 20)**: SHAP em toda resposta. Top fatores em linguagem natural.
- **Trilha de auditoria (Art. 46)**: Tabela `credit_events` com timestamps e payloads.
- **Pseudonimização (Art. 46)**: IDs de correlação ao invés de PII nas análises.
- **Consentimento para emocionais (Art. 11)**: Recomendação de não usar. Se usar, exigir consentimento explícito.
- **Minimização de dados (Art. 6, III)**: Apenas 10 features financeiras. Sem coleta excessiva.

---

## 7. Python / FastAPI — Pontos Técnicos

### 7.1 Pydantic v2

- Validação em tempo de compilação via Rust (pydantic-core). 5-50x mais rápido que v1.
- `model_validator` para validação cross-field (ex: `has_emotional_data` verifica se pelo menos uma feature emocional foi fornecida).
- JSON Schema automático para docs OpenAPI.

### 7.2 Padrões que usei

- **Dependency injection**: `Depends(require_auth)` para autenticação.
- **Background tasks**: rq para operações assíncronas. Worker carrega modelo no import.
- **Middleware**: `request_id_middleware` injeta X-Request-ID e loga duration_ms.
- **Structured logging**: `python-json-logger` — todo log é JSON parseável. Nunca `print()`.
- **Settings via Pydantic-Settings**: Variáveis de ambiente com valores default e validação.

### 7.3 Perguntas que podem fazer

- *"Por que FastAPI e não Flask/Django?"* — "Async nativo, validação Pydantic integrada, docs OpenAPI automáticos, performance superior para I/O bound. Para um serviço de ML que serve predições, é a escolha canônica."
- *"Por que não async no endpoint de predição?"* — "A predição XGBoost é CPU-bound (~5ms). Async beneficia I/O bound. Para CPU bound, adicionaríamos `run_in_executor()` ou serviríamos via um processo dedicado. No nosso volume, não é gargalo."

---

## 8. Docker

### 8.1 Composição dos serviços

```
api (FastAPI + Uvicorn) ─── porta 8000
worker (rq) ─────────────── sem porta (consome jobs do Redis)
redis ────────────────────── porta 6379
dashboard (Streamlit) ────── porta 8501
```

### 8.2 Perguntas que podem fazer

- *"Como faz deploy disso em produção?"* — "Docker Compose é para dev/demo. Em produção: Kubernetes (EKS/GKE) com Helm charts, ou ECS Fargate se quiser managed. API como Deployment com HPA (horizontal pod autoscaler), worker como Deployment separado, Redis como ElastiCache/Memorystore."
- *"E CI/CD?"* — "GitHub Actions: lint (ruff) → test (pytest) → build image → push para registry → deploy. Branch protection no main, PR obrigatório, code review."

---

## 9. Perguntas-Armadilha e Respostas

### Estilo Pablo — diretas, sem bullshit

**P: "Explica esse sistema em uma frase para um empreendedor."**
R: "Ele analisa o histórico financeiro do cliente, calcula o risco de inadimplência e diz exatamente quanto de crédito dar, a qual taxa, e explica o porquê — tudo em menos de 1 segundo."

**P: "Quanto de receita isso geraria?"**
R: "Depende do portfólio. Com uma base de 100k clientes, taxa média de aprovação de 60% e spread de 2-4% ao mês sobre o capital emprestado, a receita bruta de juros é significativa. O modelo reduz a inadimplência porque identifica melhor quem não vai pagar, então o spread pode ser menor mantendo a margem — vantagem competitiva."

**P: "Por que você não tinha treinado um modelo de ML antes?"**
R: "Porque meu foco era backend e infraestrutura. Agora que fiz, ficou claro que o pipeline é engenharia de software — versionamento de dados, reprodutibilidade, testes automatizados — não é mágica. A base de software engineering se aplica diretamente."

**P: "O que você faria diferente se tivesse mais tempo?"**
R: "Três coisas: (1) Validação temporal — dividir por tempo ao invés de aleatório para simular produção real. (2) Monitoramento de drift — PSI/CSI para detectar quando o modelo degrada. (3) A/B testing framework — comparar modelo novo vs atual em produção com métricas de negócio."

**P: "Dados emocionais são bullshit?"**
R: "Os sintéticos que eu gerei, sim — são redundantes com os financeiros. Dados emocionais reais coletados por wearables podem ter sinal preditivo genuíno, mas o custo regulatório (LGPD Art. 11) e de infraestrutura é alto. A abordagem correta é experimentar com rigor e só fazer deploy se houver ganho comprovado. Eu provei que no cenário atual não há."

**P: "Como você sabe que o modelo não está discriminando?"**
R: "Implementei a regra dos 4/5 — análise de impacto disparatado por coortes de idade e renda. Todos os coortes passam, com o Q1 de renda no limite. Em produção, isso precisa ser monitoramento contínuo, não uma análise one-shot."

**P: "Se eu te contratar amanhã, o que você entrega na primeira semana?"**
R: "Primeiro: entendo o problema de negócio. Segundo: mapeo os dados disponíveis. Terceiro: entrego um baseline funcional com métricas claras. Quarta semana é iteração. Minha abordagem é sempre: algo funcionando rápido, depois melhoro."

**P: "Qual a limitação mais grave desse sistema?"**
R: "O dataset não tem dimensão temporal. Em produção real, preciso de split temporal para validar que o modelo funciona em dados futuros, não só em dados aleatoriamente separados. Sem isso, o AUC de 0.87 pode ser otimista."

---

## 10. Checklist Pré-Apresentação

- [ ] Docker compose roda sem erros
- [ ] `curl` na API retorna resposta completa com SHAP
- [ ] Dashboard Streamlit abre e mostra dados
- [ ] Saber de cor: AUC 0.87, KS 0.58, Brier 0.049
- [ ] Saber explicar SHAP em 30 segundos
- [ ] Saber explicar por que features emocionais não agregam valor
- [ ] Ter resposta pronta para "explica em uma frase"
- [ ] Ter resposta pronta para "o que faria diferente"
- [ ] Revisar o Model Card antes da apresentação
- [ ] Testar todos os endpoints da demo ao vivo
