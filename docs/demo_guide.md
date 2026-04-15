# Guia de Demo — Empathic Credit System

**Objetivo**: 8 minutos. Mostrar que o sistema é real, funciona ponta-a-ponta, e que cada decisão é explicável.

**Subir tudo de uma vez**:
```bash
./start.sh
```

Abre `http://localhost:3000` e `http://localhost:8000/docs` em abas separadas.

---

## PARTE 1 — O que o modelo realmente aprende (entender antes de mostrar)

### De onde vêm os dados de treinamento

O modelo foi treinado no dataset **"Give Me Some Credit"** (Kaggle/OpenML, ID 46929).

- **150.000 tomadores de crédito reais** dos EUA, observados entre 2005–2007
- **Target**: `SeriousDlqin2yrs` — o tomador teve atraso grave (90+ dias) nos 2 anos seguintes? (sim/não)
- **Taxa de default**: 6,68% — dataset desbalanceado, tratado com `class_weight` no baseline e `scale_pos_weight` no XGBoost

Não existe mock de banco/transações como backend dos dados. O que existe:
- **`data/raw/cs-training.csv`** — o dataset original baixado via OpenML
- **`data/processed/{train,val,test}.parquet`** — splits estratificados (70/15/15)
- **`data/ecs.db`** — SQLite que guarda cada avaliação feita pela API em runtime (isso sim é "ao vivo")

Quando a API recebe um `POST /credit/evaluate`, ela pega os campos do request, passa pelo modelo treinado, e salva o resultado no SQLite. As tabelas de `users` e `transactions` existem no schema como estrutura de suporte futuro, mas não são alimentadas no fluxo atual — a avaliação de crédito é autossuficiente.

---

### Por que cada feature importa (SHAP na prática)

**Hierarquia real de importância** (confirmada pelos SHAP values no test set):

| Posição | Feature | Lógica |
|---------|---------|--------|
| 1ª | `past_due_90` — atrasos graves >90 dias | Histórico de inadimplência grave é o sinal mais forte de comportamento futuro. Quem já atrasou 90+ dias tem chance muito maior de repetir. |
| 2ª | `revolving_utilization` — % do limite do cartão usado | Se a pessoa usa 90% do limite todo mês, está no limite financeiro. Quanto maior, maior o risco. |
| 3ª | `past_due_30_59` — atrasos leves 30–59 dias | Atrasos curtos também predizem, mas com força menor que os graves. |
| 4ª | `age` — idade | Pessoas mais velhas têm histórico mais longo de pagamento e estabilidade. Jovens são mais arriscados estatisticamente. |
| 5ª+ | `debt_ratio`, `monthly_income`, `open_credit_lines` | Contribuição **pequena** — explicado abaixo. |

---

### Por que renda=1300 e debt_ratio=0.7 ainda aprovam com score alto

Esta é a pergunta certa. A resposta direta:

**O modelo aprendeu os padrões dos dados históricos. E nesses dados, o que de fato previu default foi o histórico de atrasos — não renda ou dívida.**

Verificação empírica (rodada no próprio dataset):

```
Perfil: renda=1300, debt_ratio=0.7, sem nenhum atraso
→ PD = 4,4%  | Score = 956  ✅ APROVADO

Mesmo perfil + past_due_90=3, sentinel=1
→ PD = 44,4% | Score = 556  ❌ NEGADO
```

A diferença do score com apenas o histórico de atrasos: **-400 pontos**. Uma variação de renda de 500 a 20.000 move o score em **menos de 20 pontos**.

**Por que o dataset funciona assim?**

1. `debt_ratio` nesse dataset tem outliers extremos (alguns valores acima de 3000). O modelo aprendeu a ignorar essa feature em boa parte dos casos porque ela é ruidosa.
2. `monthly_income` tem ~20% de valores ausentes (imputados pela mediana). O modelo viu muita incerteza nessa feature durante o treino.
3. Historicamente, pessoas com renda baixa mas sem histórico de atraso **de fato não defaultaram** na mesma taxa que quem tinha histórico ruim. O modelo captura isso fielmente.

**O que falta em produção real (e é importante dizer isso ao Pablo):**

Um sistema completo teria duas camadas:
- **Camada ML** (o que construímos): captura padrões estatísticos de comportamento
- **Camada de regras de negócio** (política de crédito): cortes duros — renda mínima, DTI máximo, score de bureau obrigatório

O modelo não substitui a política de crédito; ele a complementa. Construir o modelo sem as regras é a primeira entrega — as regras são decisão de negócio, não de ML.

---

### O que os valores SHAP mostram no gráfico

Quando você vê o gráfico de barras no frontend:

- **Barra verde** = essa feature **reduziu** a probabilidade de default para esse tomador específico
- **Barra vermelha** = essa feature **aumentou** a probabilidade de default
- **Comprimento da barra** = magnitude do impacto (quanto ela moveu o score)
- **Base** = probabilidade média de default do dataset (6,68%)

Exemplo concreto: se `revolving_utilization` aparece verde com valor 0.15 (15% do limite), o SHAP está dizendo "esse tomador usa pouco do limite, o que reduz o risco dele em relação à média do dataset".

---

## PARTE 2 — Roteiro de demo (passo a passo)

### 1. Dashboard (1.5 min)

1. Abrir `/` — apontar o **dot verde** no canto inferior do sidebar: "API online"
   - *"O sidebar chama `GET /health` a cada 30 segundos. Se a API cair, fica vermelho automaticamente."*

2. Apontar os KPI cards — vêm de `GET /credit/evaluations/stats` ao vivo
   - *"Total de avaliações, taxa de aprovação, score médio — computados do banco em tempo real."*

3. Apontar os 4 cards de tier — Score 850+ → R$ 50k / 1,5% a.m.
   - *"O score é mapeado diretamente para um produto de crédito. Isso é o que a API devolve: não só a decisão, mas o produto aprovado."*

---

### 2. Avaliar Crédito — perfil de alto risco → NEGADO (1.5 min)

**Preencher com esse perfil** (melhor começar pela negação — mais fácil de explicar):

```
Utilização rotativo: 0.92
Idade: 28
Renda mensal: 3000
Índice de endividamento: 0.45
Linhas de crédito abertas: 8
Atrasos 30–59 dias: 2
Atrasos 60–89 dias: 1
Atrasos >90 dias: 3
Flag sentinela: 1
```

- Resultado: **NEGADO**, score ~250–350
- Apontar o SHAP: `past_due_90` e `revolving_utilization` são as barras vermelhas maiores
- *"O sistema não só nega — ele explica qual feature foi determinante. Isso é o Art. 20 da LGPD: direito à explicação de decisões automatizadas."*

---

### 3. Avaliar Crédito — perfil limpo → APROVADO + aceitar oferta (2 min)

**Preencher com:**

```
Utilização rotativo: 0.08
Idade: 48
Renda mensal: 12000
Índice de endividamento: 0.12
Atrasos 30–59 dias: 0
Atrasos 60–89 dias: 0
Atrasos >90 dias: 0
Flag sentinela: 0
```

- Resultado: **APROVADO**, score 970+, limite R$ 50.000, taxa 1,5%
- Apontar gráfico SHAP — todas as barras verdes
- Clicar **"Aceitar Oferta de Crédito"**
  - *"Aqui o fluxo assíncrono entra: a API enfileira um job no Redis via rq. O worker processa em background e registra a notificação. A API respondeu imediatamente — não travou esperando o deploy."*
- Apontar Request ID e modelo no rodapé
  - *"Esse Request ID aparece nos logs JSON estruturados e no audit trail do banco. Rastreabilidade completa."*

---

### 4. Toggle emocional — demonstrar a decisão de não deployar (1 min)

No mesmo formulário, expandir **"Features emocionais"**:

```
Stress level: 0.8
Impulsivity score: 0.6
Emotional stability: 0.3
Financial stress events 7d: 5
```

- Clicar Avaliar
- Score muda em **pouquíssimo** (< 5 pontos geralmente)
- *"Isso confirma o notebook 04. Delta AUC = -0.0008. O modelo emocional não aprende nada que o financeiro já não sabe. E essas são features sensíveis — Art. 11 da LGPD, dado sobre saúde mental e emocional. Custo regulatório muito maior que o ganho preditivo. Decidi não deployar."*

---

### 5. Histórico (1 min)

- Clicar "Ver no histórico" ou navegar para `/history`
- Filtrar por **"Negadas"** — mostrar só as negações
- Expandir uma linha — painel abre com SHAP completo
- *"Cada avaliação persiste o SHAP inteiro. Posso reproduzir a explicação de qualquer decisão passada, mesmo depois de retraining."*

---

### 6. Fairness (30 seg)

- Navegar para `/fairness`
- Gráfico de idade: todas as barras acima da linha vermelha 0.80
  - *"Regra dos 4/5 da EEOC. Nenhum grupo etário é penalizado desproporcionalmente."*
- Gráfico de renda: Q1 em ~0.82 — no limite
  - *"Pessoas de baixa renda recebem aprovações a 82% da taxa do grupo de alta renda. No limite, mas passa. Isso é um flag para monitoramento contínuo."*

---

## PARTE 3 — Perguntas difíceis do Pablo

### Modelo e dados

**"Por que renda baixa e dívida alta ainda aprovam?"**
> "Porque o modelo aprendeu com dados históricos reais onde o melhor preditor de inadimplência foi o comportamento passado — atrasos, não renda. Em produção real, você adiciona uma camada de regras de negócio por cima: renda mínima, DTI máximo. O modelo e a política de crédito são duas coisas separadas. Construí o modelo — as regras são decisão do negócio."

**"Você treinou um modelo de ML do zero?"**
> "Sim. Dataset Give Me Some Credit, 150k tomadores. Baseline Regressão Logística (AUC 0.80), depois XGBoost financeiro (AUC 0.87), depois experimento com features emocionais (AUC 0.869 — pior). Calibração isotônica para garantir que as probabilidades sejam reais, não só ranqueamento."

**"O que é calibração? Por que importa?"**
> "Um modelo pode ranquear bem — colocar os ruins antes dos bons — mas ter as probabilidades erradas. Se ele diz 'PD = 10%' mas na realidade 30% dessas pessoas defaultaram, as decisões de pricing estão erradas. Calibração isotônica ajusta a curva de probabilidade para que o '10%' realmente signifique 10%. Brier score passou de 0.053 para 0.049 depois da calibração."

**"Por que não usou features emocionais?"**
> "Testei. Delta AUC = -0.0008 — o modelo emocional foi *pior* que o financeiro puro, estatisticamente. E essas features seriam dados sensíveis pela LGPD Art. 11 — categoria que exige consentimento explícito, base legal específica, e enorme custo de conformidade. Receita zero, risco regulatório alto. Não faz sentido negocial."

**"O SHAP é exato ou aproximado?"**
> "Exato para tree models. TreeExplainer usa o algoritmo O(TLD) que calcula os valores de Shapley exatos percorrendo as árvores diretamente — não é sampling, não é LIME. Cada barra no gráfico é matematicamente garantida."

### Domínio e simplificações do case

**"Cadê o usuário? O user_id é None em tudo."**
> "O sistema é request-centric por design neste case. Em produção, o `user_id` viria do token de autenticação (JWT/OAuth) — o request chegaria já identificado. As tabelas de `User` existem no schema como ponto de integração — a estrutura está pronta, mas não construí autenticação de usuário porque não estava no escopo do desafio."

**"O fluxo de aceite de oferta é um produto real?"**
> "É um recorte de lifecycle para demonstrar arquitetura orientada a eventos — separação entre decisão (síncrona) e deploy (assíncrono via fila). Não é um fluxo operacional completo. Em produção, teria validação de conta, compliance check, e integração com o core banking."

**"O path assíncrono persiste avaliação?"**
> "Não. O path async serve para demonstrar a arquitetura de fila com rq — o fluxo principal e auditado é o síncrono. Em produção, o worker também persistiria, mas para o case priorizei robustez no fluxo principal ao invés de duplicar lógica no worker."

### Arquitetura e decisões técnicas

**"Por que SQLite e não Postgres?"**
> "Zero ops para o case. O desafio diz 'banco à sua escolha'. Trocar para Postgres é uma linha de config — `DATABASE_URL` no `.env`. O código não muda."

**"Como escala?"**
> "API FastAPI é stateless — sobe quantas instâncias quiser atrás de um load balancer. Workers rq escalam horizontalmente também. O gargalo em escala seria o SQLite — aí sim troca para Postgres. Mas o design já está preparado para isso."

**"Por que rq e não Celery?"**
> "Celery é mais poderoso, mas tem configuração complexa — brokers, backends, serializers, concurrency models. Para esse case, rq resolve em 50 linhas de código. Seria Celery se precisasse de tasks periódicas, retry com backoff, múltiplas filas prioritárias — coisas que não estão no escopo."

**"Tempo de resposta da API?"**
> "~50ms para avaliação síncrona — inclui inferência XGBoost + cálculo SHAP exato + escrita no SQLite. Latência de SHAP TreeExplainer é O(TLD) onde T=número de árvores, L=profundidade máxima, D=features. Com 100 árvores, depth 6, 11 features — é rápido."

### Sobre você

**"Por que você não tinha treinado um modelo antes?"**
> "Nunca tive o contexto certo para ir além do uso de APIs de modelo. Quando surgiu a oportunidade de fazer isso do zero — dataset, pipeline, validação, deploy — fiz. E foi o projeto que mais aprendi em menos tempo. A curiosidade estava lá, faltava o gatilho."

**"Você entende o que está apresentando?"**
> "Cada número. AUC 0.87 significa que em 87% dos pares aleatórios de bom/mau pagador, o modelo ranqueia o mau antes do bom. KS 0.53 é a maior separação entre as distribuições de score de bons e maus. Brier 0.049 é o MSE entre probabilidade prevista e realizada. Posso derivar qualquer desses de primeiro princípio."

---

## PARTE 4 — Sequência recomendada para o vídeo

1. `./start.sh` — mostrar o terminal subindo tudo em ~20 segundos
2. Abrir `http://localhost:3000`
3. Dashboard → KPIs ao vivo
4. Evaluate → perfil NEGADO com SHAP (explicar as barras)
5. Evaluate → perfil APROVADO → aceitar oferta
6. Toggle emocional → mostrar que não muda o score
7. Histórico → expandir linha com SHAP
8. Analytics → aba Operacional
9. Fairness → gráficos + decisão emocional

**Antes de gravar**: fazer pelo menos 5 avaliações (mix de aprovações e negações) para o Dashboard e Analytics terem dados reais.
