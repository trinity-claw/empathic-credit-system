# Guia de Demo — Empathic Credit System

**Objetivo**: Mostrar em ~8 minutos que o sistema é real, funciona end-to-end, e que cada decisão é explicável.

**Setup antes de começar**:
```bash
# Terminal 1 — API
uv run uvicorn src.api.main:app --reload

# Terminal 2 — Frontend
cd frontend && npm run dev
```

Abrir no browser: `http://localhost:3000`

---

## Roteiro — passo a passo

### 1. Dashboard (2 min)

**O que mostrar**: Prova que o sistema está vivo e conectado.

1. **Abrir o Dashboard (`/`)**
   - Apontar o **dot verde** no sidebar inferior esquerdo: "API online"
   - Apontar a versão do modelo embaixo: "xgboost_financial_calibrated"
   - Frase: *"O sidebar faz polling do `/health` a cada 30 segundos. Se a API cair, o dot fica vermelho."*

2. **KPI cards (top)**
   - Esses números vêm em tempo real de `GET /credit/evaluations/stats`
   - Se ainda não tem avaliações: mostrar o empty state ("Nenhuma avaliação ainda")
   - Frase: *"Total de avaliações, taxa de aprovação, score médio e ofertas aguardando — tudo computado do banco ao vivo."*

3. **Tiers de crédito (bottom)**
   - Apontar os 4 cards: Score 850+ → R$ 50k / 1,5% a.m.
   - Frase: *"O sistema mapeia o score diretamente para um produto de crédito real — limite, taxa e tipo de contrato."*

---

### 2. Avaliar Crédito — perfil de bom pagador (2 min)

**O que mostrar**: Fluxo completo de uma aprovação com SHAP.

1. **Navegar para `/evaluate`**

2. **Preencher com um perfil de baixo risco** (ou deixar os valores default e ajustar):
   ```
   Utilização rotativo: 0.15
   Idade: 52
   Renda mensal: 8000
   Índice de endividamento: 0.18
   Atrasos 30-59 dias: 0
   Atrasos 60-89 dias: 0
   Atrasos >90 dias: 0
   ```

3. **Clicar "Avaliar"**
   - Toast aparece: "Crédito aprovado — Score 780" (ou similar)
   - Resultado aparece à direita com:
     - Badge verde **APROVADO**
     - Score grande (ex: 780)
     - PD% (probabilidade de default)
     - Limite aprovado (ex: R$ 20.000) + taxa 2,5% a.m. + tipo "long term"
   - Frase: *"Isso é o que chega em 50ms. Score + decisão + produto de crédito + explicação SHAP — tudo em uma resposta."*

4. **Apontar o gráfico SHAP (barras horizontais)**
   - Verde = reduz o risco, Vermelho = aumenta o risco
   - Frase: *"Esses são os valores de Shapley exatos. Não é aproximação — é o TreeExplainer do SHAP, O(TLD). Isso é o que garante compliance com o Art. 20 da LGPD: o cliente tem direito a explicação para decisões automatizadas."*
   - Apontar o fator mais importante (provavelmente `age` ou `revolving_utilization`)

5. **Clicar "Aceitar Oferta de Crédito"** (botão verde que aparece após aprovação)
   - Toast: "Oferta aceita! O crédito está sendo processado."
   - Frase: *"Aqui entra o rq — enfileira um job assíncrono que processa o deploy do crédito no background. A API respondeu imediatamente, o worker consome na fila do Redis."*

6. **Apontar Request ID e Modelo no rodapé do card**
   - Frase: *"Request ID rastreável — esse mesmo ID aparece nos logs estruturados JSON e na tabela de audit trail do banco."*

---

### 3. Avaliar Crédito — perfil de alto risco + features emocionais (1 min)

**O que mostrar**: Nega crédito com justificativa + demonstra o experimento emocional.

1. **Ainda na página `/evaluate`, trocar os campos**:
   ```
   Utilização rotativo: 0.95
   Atrasos >90 dias: 3
   Atrasos 30-59 dias: 2
   Renda mensal: 1500
   ```

2. **Clicar "Avaliar"**
   - Badge vermelho **NEGADO**, score baixo (ex: 280)
   - Frase: *"Mesmo negando, o sistema explica o motivo — `past_due_90` e `revolving_utilization` são os drivers. Isso é o que diferencia uma decisão auditável de uma caixa preta."*

3. **Expandir o toggle "Features emocionais"**
   - Preencher `stress_level: 0.8`, `impulsivity_score: 0.6`, `emotional_stability: 0.3`, `financial_stress_events_7d: 5`
   - Clicar "Avaliar" novamente
   - Frase: *"Com features emocionais preenchidas, o modelo emocional entra. Mas olha o resultado — o score quase não muda. Isso confirma o que encontrei no notebook 04: delta AUC de -0.0008. As features emocionais não agregam valor preditivo. Recomendei não deployar — custo regulatório da LGPD Art. 11 (dados sensíveis) supera o benefício."*

---

### 4. Histórico (1.5 min)

**O que mostrar**: Que as avaliações são persistidas e podem ser auditadas.

1. **Clicar no link "Ver no histórico"** (aparece no resultado do evaluate)
   — ou navegar diretamente para `/history`

2. **Tabela com todas as avaliações**
   - Mostrar as colunas: ID, Decisão (badge colorido), Score (barra visual), PD%, Modelo, Data
   - Frase: *"Toda avaliação fica registrada com timestamp, modelo usado e payload completo. Trilha de auditoria integral."*

3. **Usar os filtros**: clicar em "Aprovadas", depois "Negadas"
   - Frase: *"Filtro client-side — pode ver só as negações, útil para auditoria de disparidade."*

4. **Clicar em uma linha** para expandir
   - O painel mostra: SHAP chart do registro histórico + features de entrada + todos os valores SHAP
   - Frase: *"Cada registro guarda o SHAP completo. Posso reproduzir a explicação de qualquer decisão passada, mesmo que o modelo seja atualizado depois."*

---

### 5. Analytics — aba Operacional (45 seg)

**O que mostrar**: Que a aba operacional reflete dados reais.

1. **Navegar para `/analytics`**
2. **A aba "Operacional" está selecionada por default**
   - Mostrar o gráfico de distribuição por tier com dados reais
   - KPI cards com os números atuais
   - Frase: *"Essa aba busca os dados do backend ao vivo. Distribuição real dos scores processados, taxa de aprovação e ofertas pendentes."*

3. **Clicar nas outras abas** (Curva ROC, Calibração, Modelos)
   - Frase: *"Essas abas mostram os resultados do treino — são fixos porque vêm do notebook, não mudam em runtime. O que muda é a aba operacional."*

---

### 6. Fairness (30 seg)

**O que mostrar**: Que o sistema pensa em ética e regulação.

1. **Navegar para `/fairness`**
2. **Apontar os dois gráficos** (Idade e Renda)
   - Linha vermelha = 0.80 (limite da regra dos 4/5)
   - Barra amarela no Q1 de Renda = ~0.82 (no limite)
   - Frase: *"Regra dos 4/5 da EEOC adaptada para crédito. Todos os coortes de idade passam. Q1 de renda está no limite — isso é um flag para monitoramento em produção."*

3. **Rolar para baixo** — seção "Features Emocionais — Análise de Risco Regulatório"
   - Mostrar os dois cards: Risco LGPD Art. 11 (vermelho) + Decisão: Não fazer deploy (verde)
   - Frase: *"Essa é a decisão mais importante do projeto. Provei experimentalmente que não funciona, e documentei o porquê de não deployar. Isso é engineering com responsabilidade."*

---

## Frases para perguntas do Pablo

| Pergunta | Resposta de 1 frase |
|----------|---------------------|
| "Quanto tempo levou?" | "4 dias: 1 de análise, 1 de ML, 1 de backend, 1 de frontend." |
| "O que você faria diferente?" | "Validação temporal — split por data ao invés de aleatório, para simular uso real em produção." |
| "Por que SQLite?" | "Zero ops. O desafio diz 'banco à sua escolha'. Migrar para Postgres é uma variável de config — `DATABASE_URL`." |
| "Por que não usou as features emocionais?" | "Usei. Provei que não funcionam. Delta AUC = -0.0008. Custo regulatório supera o benefício." |
| "O SHAP é preciso?" | "Exato. TreeExplainer calcula valores de Shapley exatos, não é amostragem. Cada explicação é matematicamente garantida." |
| "Como você escala isso?" | "API stateless → horizontal scaling. Workers rq → mais instâncias. Gargalo é o banco: SQLite → Postgres na config." |

---

## Sequência de telas para gravar (se precisar de vídeo)

1. `/` — Dashboard com dados reais (fazer umas 3-4 avaliações antes para ter dados)
2. `/evaluate` — Aprovação com SHAP → aceitar oferta
3. `/evaluate` — Negação com justificativa
4. `/history` — Expandir uma linha com SHAP completo
5. `/analytics` → aba Operacional + aba Calibração
6. `/fairness` — Gráficos + seção emocional
