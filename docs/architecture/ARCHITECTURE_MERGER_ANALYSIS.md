# CS2 Analyzer × V1 Bot: Definitive Architecture Merger Analysis

## Document Purpose and Scope

This document represents the definitive architectural analysis and merger blueprint for adapting the Macena CS2 Analyzer codebase — a production-grade Counter-Strike 2 coaching AI system comprising approximately 63,000 lines of Python across 80+ modules — into a next-generation XAUUSD (Gold) trading intelligence system. This is not a surface-level comparison or a simple mapping exercise. This document provides exhaustive, code-level analysis of every significant module in the CS2 Analyzer, cross-references each component against the mathematical foundations documented in the V1 Bot's 14 technical documents (totaling over 6,000 lines of mathematical specification), and prescribes the precise transformations, adaptations, and integrations required to produce a trading system that inherits the CS2 Analyzer's architectural excellence while incorporating the V1 Bot's quantitative finance rigor.

The CS2 Analyzer was chosen as the architectural foundation for several critical reasons. First, it solves a fundamentally analogous problem: analyzing sequential temporal data (game ticks at 64Hz) to produce actionable coaching recommendations under uncertainty — precisely what a trading system must do with market ticks. Second, it implements state-of-the-art neural architectures (JEPA, Mixture of Experts, Liquid Time-Constants, Hopfield Associative Memory) that are directly applicable to financial time series. Third, it provides production-grade infrastructure (maturity gating, multi-scale analysis, experience banking, feedback loops) that typically takes months to build from scratch. Fourth, its modular architecture — with clear separation between perception, memory, strategy, and communication layers — maps naturally onto the trading domain's separation between data ingestion, state estimation, signal generation, and order execution.

This document is organized into seven major parts. Part I analyzes the V1 Bot's mathematical foundations and architectural vision in exhaustive detail. Part II performs a deep-dive into every significant module of the CS2 Analyzer, explaining not just what each module does but how it does it at the implementation level. Part III provides the complete merger specification — how each CS2 component transforms into its trading equivalent, with attention to the mathematical transformations required. Part IV addresses the knowledge synthesis — how the V1 Bot's 200+ equations integrate into the adapted architecture. Part V covers the data pipeline transformations. Part VI addresses the training and deployment lifecycle. Part VII provides the implementation roadmap.

---

## Part I: V1 Bot Mathematical Foundations — Deep Analysis

### 1.1 The 8-Stage Pipeline Architecture

The V1 Bot's core architecture is an 8-stage sequential pipeline that processes raw market data into actionable trading signals. Understanding this pipeline in detail is essential because it defines the functional requirements that the merged system must satisfy.

**Stage 1: Feature Engineering** — The V1 Bot computes over 40 technical indicators incrementally, meaning each new price bar triggers an update rather than a full recomputation. This is a critical design decision for live trading where latency matters. The indicators span five categories: trend indicators (SMA, EMA, DEMA, TEMA, WMA, HMA, KAMA — each with distinct smoothing characteristics), momentum oscillators (RSI, Stochastic RSI, MACD, CCI, Williams %R, ROC, MFI — each measuring different aspects of price momentum), volatility measures (Bollinger Bands, ATR, Keltner Channels, Donchian Channels, Standard Deviation, Chaikin Volatility, RVI — each capturing different dimensions of market uncertainty), volume indicators (OBV, VWAP, CMF, Chaikin Oscillator, Force Index, EMV, Klinger Volume Oscillator — each measuring different aspects of volume-price relationships), and composite indicators (Ichimoku Cloud with five sub-components, Fibonacci retracement levels, Elliott Wave ratios). The mathematical foundations document specifies exact formulas for each: for example, RSI is computed as 100 - 100/(1 + RS) where RS = EMA(gains, n)/EMA(losses, n), and the V1 Bot uses n=14 as the default period with an EMA smoothing factor of 1/(1+n). The incremental update for EMA is EMA_new = α × price + (1-α) × EMA_old, which avoids the O(n) full window recomputation. This incrementality is a design pattern that must be preserved in the merged system.

**Stage 2: Regime Classification** — The V1 Bot implements three parallel regime classifiers, each providing a different perspective on market state. The rule-based classifier uses threshold logic on volatility (ATR/price ratio), trend strength (ADX > 25 = trending, ADX < 20 = ranging), and momentum divergence. The Hidden Markov Model (HMM) classifier models the market as a latent state machine with typically 3-5 hidden states, using the Baum-Welch algorithm for parameter estimation and the Viterbi algorithm for most-likely-state-sequence decoding. The mathematical specification defines the HMM as λ = (A, B, π) where A is the state transition matrix, B is the observation probability matrix, and π is the initial state distribution. The forward-backward algorithm computes α_t(i) = P(o_1...o_t, q_t = s_i | λ) and β_t(i) = P(o_{t+1}...o_T | q_t = s_i, λ), and the posterior probability γ_t(i) = α_t(i)β_t(i) / Σ_j α_t(j)β_t(j) gives the probability of being in state i at time t. The k-means classifier operates on a feature space of (returns, volatility, volume_change, spread) and clusters historical periods into distinct regimes. The ensemble of these three classifiers — rule-based as the fast path, HMM for probabilistic inference, k-means for data-driven clustering — is a pattern that the merged system should preserve because each classifier captures different aspects of market structure.

**Stage 3: Strategy Router** — Based on the detected regime, the pipeline selects one of several strategy branches. In trending markets, momentum-following strategies are activated. In ranging markets, mean-reversion strategies take precedence. In volatile markets, options-like protective strategies (or reduced position sizing) are engaged. The routing logic is not a simple switch statement — it includes transition probabilities between regimes to avoid whipsawing on regime boundaries. When the regime classifier outputs conflicting signals (e.g., rule-based says trending, HMM says ranging), the router uses a confidence-weighted voting mechanism.

**Stage 4: ML Inference** — The V1 Bot specifies multiple neural network architectures for price prediction and signal generation. The LSTM architecture uses the standard gates: forget gate f_t = σ(W_f · [h_{t-1}, x_t] + b_f), input gate i_t = σ(W_i · [h_{t-1}, x_t] + b_i), candidate cell state C̃_t = tanh(W_C · [h_{t-1}, x_t] + b_C), cell state C_t = f_t ⊙ C_t-1 + i_t ⊙ C̃_t, and output gate o_t = σ(W_o · [h_{t-1}, x_t] + b_o), yielding hidden state h_t = o_t ⊙ tanh(C_t). The Transformer architecture implements multi-head self-attention where Attention(Q,K,V) = softmax(QK^T / √d_k)V, with positional encoding PE(pos, 2i) = sin(pos/10000^{2i/d}) and PE(pos, 2i+1) = cos(pos/10000^{2i/d}). The Temporal Fusion Transformer (TFT) extends this with variable selection networks, gated residual networks (GRN), and interpretable multi-head attention. The specification also covers Graph Neural Networks for multi-asset correlation modeling, where the graph convolution is H^{(l+1)} = σ(D̃^{-1/2}ÃD̃^{-1/2}H^{(l)}W^{(l)}) with à = A + I_N being the adjacency matrix with self-loops and D̃ being the degree matrix.

**Stage 5: Confidence Gating** — This is one of the most critical stages and directly parallels the CS2 Analyzer's MaturityObservatory. The V1 Bot specifies three confidence gates. The maturity gate prevents the system from trading when the model has insufficient training data — it tracks the number of training episodes and the stability of model weights over recent updates. The drift gate monitors for concept drift using the Page-Hinkley test: U_t = Σ_{i=1}^{t} (x_i - x̄_t - δ), where the test statistic m_t = U_t - min_{j≤t} U_j triggers an alarm when m_t > λ (threshold). The CUSUM test is also specified: S_t^+ = max(0, S_{t-1}^+ + (x_t - μ_0 - k)) and S_t^- = max(0, S_{t-1}^- - (x_t - μ_0 + k)), where an alarm fires when max(S_t^+, S_t^-) > h. The silence gate suppresses trading during periods of insufficient market activity or data quality issues.

**Stage 6: 4-Tier Decision Engine** — The V1 Bot implements a cascading fallback mechanism: COPER (Context Optimized with Prompt, Experience, and Replay) as the primary decision maker, ML-based prediction as the secondary, pure Technical Analysis as the tertiary, and a Conservative baseline (no trade or minimal position) as the final fallback. Each tier has a minimum confidence threshold, and the system cascades down the tiers when upper tiers fail to produce sufficiently confident signals. This cascading pattern is directly mirrored in the CS2 Analyzer's CoachingService, which implements COPER → Hybrid → RAG → Legacy as its 4-mode pipeline.

**Stage 7: Risk Check** — The mathematical foundations document specifies extensive risk management mathematics. Value at Risk (VaR) at confidence level α is defined as VaR_α = -inf{x ∈ ℝ : P(L ≤ x) ≥ α}, and the parametric form for a normal distribution is VaR_α = μ + σΦ^{-1}(α). Conditional Value at Risk (CVaR) is CVaR_α = E[L | L > VaR_α] = (1/(1-α))∫_α^1 VaR_u du. The Kelly Criterion for optimal position sizing is f* = (bp - q) / b where b is the odds, p is the probability of winning, and q = 1-p. The document also specifies maximum drawdown calculations: MDD = max_{t∈[0,T]} (max_{s∈[0,t]} P(s) - P(t)) / max_{s∈[0,t]} P(s), and various volatility estimators including Parkinson's (using high-low range), Garman-Klass (using OHLC), and Yang-Zhang (combining overnight and intraday volatility).

**Stage 8: Signal Emission** — The final stage produces a structured signal containing: direction (BUY/SELL/HOLD), confidence score (0-1), entry price, stop-loss level, take-profit level, position size (from Kelly Criterion), regime label, and an explainability payload showing which indicators and model components contributed to the decision.

### 1.2 Advanced Mathematical Domains

Beyond the 8-stage pipeline, the V1 Bot's mathematical foundations cover several advanced domains that inform the merged system's design.

**Stochastic Calculus** — The document specifies Geometric Brownian Motion dS = μS dt + σS dW as the base model for price dynamics, with Itô's Lemma df = (∂f/∂t + μS ∂f/∂S + ½σ²S² ∂²f/∂S²)dt + σS ∂f/∂S dW for transforming this into different functional forms. Black-Scholes pricing is included for options-aware risk management. These mathematical foundations inform the merged system's volatility modeling and position sizing.

**Time Series Analysis** — ACF/PACF for model identification, ARIMA(p,d,q) with Box-Jenkins methodology, GARCH(p,q) for volatility modeling where σ²_t = ω + Σα_i ε²_{t-i} + Σβ_j σ²_{t-j}, Kalman Filter for state estimation with prediction step x̂_{t|t-1} = F x̂_{t-1|t-1} and update step x̂_{t|t} = x̂_{t|t-1} + K_t(z_t - H x̂_{t|t-1}), and cointegration testing for pairs trading using the Engle-Granger two-step method.

**Reinforcement Learning** — The specification defines the trading problem as a Markov Decision Process (S, A, P, R, γ) where states include price history and portfolio state, actions include buy/sell/hold with position sizing, transition probabilities are determined by market dynamics, rewards are risk-adjusted returns (differential Sharpe ratio dS_t/dη = (B_{t-1}ΔA_t - A_{t-1}ΔB_t) / (B_{t-1} - A²_{t-1})^{3/2}), and the discount factor γ determines the time horizon. The document covers Q-learning, Deep Q-Networks (DQN), and Soft Actor-Critic (SAC) with entropy regularization J(π) = Σ E[r(s_t, a_t) + αH(π(·|s_t))].

**Market Microstructure** — VPIN (Volume-Synchronized Probability of Informed Trading) for detecting informed flow, Order Book Imbalance OBI = (V_bid - V_ask) / (V_bid + V_ask) for short-term direction prediction, Kyle's Lambda for measuring price impact, Hawkes Processes for modeling event clustering (self-exciting point processes where λ(t) = μ + Σ α·e^{-β(t-t_i)}), and the Almgren-Chriss model for optimal execution.

**Information Theory** — Shannon Entropy H(X) = -Σ p(x) log p(x) for measuring uncertainty, KL Divergence D_KL(P||Q) = Σ P(x) log(P(x)/Q(x)) for distribution comparison, Mutual Information I(X;Y) = H(X) - H(X|Y) for feature selection, and wavelet transforms for multi-resolution signal decomposition.

---

## Part II: CS2 Analyzer Codebase — Exhaustive Module Analysis

### 2.1 Architecture Overview

The CS2 Analyzer is organized into a layered architecture with clear responsibilities at each level. The top-level entry point is `moneymaker.py` (282 lines), a CLI orchestrator that dispatches commands to the appropriate subsystems. Below this, the application is structured into several major subsystems:

- **Neural Network Layer** (`backend/nn/`) — Contains all model definitions, training logic, and inference infrastructure
- **Analysis Layer** (`backend/analysis/`) — Contains game-theoretic and statistical analysis modules
- **Knowledge Layer** (`backend/knowledge/`) — Contains the experience bank and RAG knowledge retrieval system
- **Coaching Layer** (`backend/coaching/`) — Contains the hybrid coaching engine that synthesizes ML and knowledge
- **Services Layer** (`backend/services/`) — Contains the orchestration services that coordinate all other layers
- **Processing Layer** (`backend/processing/`) — Contains feature engineering, state reconstruction, and data pipelines
- **Storage Layer** (`backend/storage/`) — Contains database models and data access

The data flow through the system follows a well-defined path: raw demo files are parsed into tick-level data, which flows through the processing layer for feature extraction, then into the neural network layer for model inference, through the analysis layer for game-theoretic insights, into the knowledge layer for experience matching, and finally through the services layer for synthesis into coaching recommendations.

### 2.2 Neural Network Layer — Deep Analysis

#### 2.2.1 JEPA Model (jepa_model.py — 846 lines)

The Joint-Embedding Predictive Architecture (JEPA) model is the cornerstone of the CS2 Analyzer's learning system. Understanding its implementation in detail is critical because it will become the core of the trading system's predictive engine.

**JEPAEncoder (lines 30-85):** The encoder is implemented as a multi-layer perceptron with the architecture input_dim → 512 → ReLU → 256 → ReLU → latent_dim. This is not a trivial choice — the funnel architecture (wide-to-narrow) forces information compression, which acts as a bottleneck that extracts only the most informative features from the input. The encoder uses standard PyTorch `nn.Linear` layers with ReLU activations. For the trading adaptation, the input_dim will change from the CS2 tick features to market features (OHLCV + technical indicators), but the funnel architecture should be preserved because it serves the same information-compression purpose.

**JEPAPredictor (lines 87-140):** The predictor takes two latent vectors (context and target representations) concatenated together, and predicts the target from the context. Its architecture is (latent_dim × 2) → 512 → ReLU → 256 → ReLU → latent_dim. This concatenation-then-prediction pattern is the heart of JEPA — it learns to predict the latent representation of a future state from the latent representation of the current state. In the CS2 domain, this means predicting How the game will evolve from the current situation. In the trading domain, this directly translates to predicting the latent representation of future market state from the current market state — essentially learning the dynamics of the market in latent space rather than in raw price space.

**Context and Target Encoders (lines 142-200):** The model maintains two copies of the encoder — a context encoder (online, receives gradients) and a target encoder (momentum-updated, no gradients). The target encoder is updated via exponential moving average: for each parameter θ_target, the update rule is θ_target = τ × θ_target + (1-τ) × θ_context, where τ = 0.996 (a high momentum value that ensures the target encoder changes slowly). This EMA mechanism is borrowed from BYOL (Bootstrap Your Own Latent) and serves a critical purpose: it prevents representation collapse. Without the momentum update, the context and target encoders could converge to trivial constant representations. The slow-moving target provides a stable learning signal. For trading, this mechanism is directly applicable — it ensures that the model's market state representations remain meaningful rather than collapsing into degenerate features.

**InfoNCE Pre-training Loss (lines 202-280):** The `forward_jepa_pretrain` method implements contrastive self-supervised learning. Given a context window x_context and a target window x_target, the model encodes both, uses the predictor to predict the target from the context, and then computes the InfoNCE loss: L = -log(exp(sim(z_pred, z_target)/τ) / Σ_j exp(sim(z_pred, z_j)/τ)), where sim is cosine similarity and τ is a temperature parameter. The negative samples z_j come from other examples in the batch. This loss encourages the model to learn representations where temporally adjacent states are similar and temporally distant states are dissimilar — exactly the kind of temporal coherence that is useful for market prediction.

**Coaching Head with MoE (lines 282-450):** After pre-training, the JEPA model is extended with a coaching head that uses Mixture of Experts (MoE). The implementation creates num_experts (default 3) independent expert networks, each being a two-layer MLP (latent_dim → hidden_dim → output_dim). A gating network (latent_dim → num_experts with softmax) determines the weight of each expert's contribution. The final output is the weighted sum of expert outputs: y = Σ_i g_i × expert_i(x), where g_i are the gate weights. This MoE architecture is critical for the trading domain because different market regimes require different prediction strategies — one expert might specialize in trending markets, another in ranging markets, and a third in volatile/crisis markets.

**Role-Biased Gating (lines 452-530):** The CS2 model includes role-specific bias vectors for 5 player roles (Entry, AWP, Support, Lurk, IGL). When a role_id is provided, the corresponding bias vector is added to the gate network's input, biasing the expert selection toward role-appropriate strategies. For trading, this maps to asset-class or timeframe gating — different bias vectors for different instruments (Gold, Forex, Crypto) or different timeframes (scalping, swing, position).

**Selective Decoding (lines 532-600):** The model implements a confidence-based selection mechanism where only the top-k most confident predictions are output, and the rest are masked. This is implemented by computing a confidence score for each output dimension, sorting by confidence, and zeroing out everything below the k-th highest confidence. For trading, this translates directly to confidence-filtered signal emission — only emit trading signals when the model is sufficiently confident.

**LSTM Temporal Processing (lines 602-680):** An LSTM layer sits between the encoder and the coaching head, processing sequences of encoded representations to capture temporal dependencies. The LSTM has hidden_dim units and processes the sequence of latent vectors to produce a temporally-aware hidden state. This is essential for trading because market state depends on the sequence of recent states, not just the current state — patterns like "head and shoulders" or "double bottom" are inherently sequential.

#### 2.2.2 RAP Coach Model (model.py — 100 lines)

The RAP (Reasoning, Analysis, Prediction) Coach Model is the integrative neural architecture that combines all sub-modules into a coherent inference pipeline. Its `__init__` method instantiates five sub-networks and two output heads:

```python
self.perception = RAPPerception()                    # Visual feature extraction
self.memory = RAPMemory(perception_dim, metadata_dim, hidden_dim)  # Temporal state tracking
self.strategy = RAPStrategy(hidden_dim, output_dim, context_dim=metadata_dim)  # Decision making
self.pedagogy = RAPPedagogy(hidden_dim)              # Value estimation
self.attributor = CausalAttributor(hidden_dim)       # Explainability
self.position_head = nn.Linear(hidden_dim, 3)        # Position recommendation
```

The forward pass follows a strict sequential flow: Perception extracts spatial features from visual inputs → Memory maintains a running belief state using LTC dynamics and Hopfield pattern recall → Strategy uses MoE to produce action recommendations → Pedagogy estimates the value of the current state → the Attributor explains which factors contributed to the recommendation → the position head outputs a 3D position vector. The model also computes a sparsity loss term using L1 regularization on the strategy layer's gate activations to encourage expert specialization.

The output dictionary contains: `advice_probs` (the action probability distribution from strategy), `belief_state` (the hidden state from memory), `value_estimate` (V(s) from pedagogy), `gate_weights` (the MoE routing weights for interpretability), `optimal_pos` (the 3D position recommendation), and `attribution` (the causal attribution scores across 5 concepts).

For the trading adaptation, this model structure maps as follows: Perception becomes the market feature encoder (processing OHLCV + indicators instead of video frames), Memory maintains the running market belief state (using LTC for continuous-time dynamics between irregularly-spaced ticks and Hopfield for recalling similar historical patterns), Strategy becomes the regime-aware signal generator (with 4 experts for trend/range/volatile/crisis), Pedagogy becomes the portfolio value estimator (V(s) = expected risk-adjusted return), the Attributor explains which market factors (trend, momentum, volatility, volume, correlation) drove the signal, and the position head outputs position sizing (long/short/flat with magnitude).

#### 2.2.3 RAPPerception — Visual Feature Extraction (perception.py — 73 lines)

The perception module implements a three-stream convolutional architecture designed to extract different types of spatial information from the game state. The view backbone uses a ResNet-style architecture with block configurations [3, 4, 6, 3] — meaning 3 blocks in the first stage, 4 in the second, 6 in the third, and 3 in the fourth. Each ResNet block implements the standard residual connection: output = F(x) + x, where F is a sequence of Conv2d → BatchNorm → ReLU → Conv2d → BatchNorm. The identity shortcut x is adjusted with a 1×1 convolution when dimensions change. The view backbone processes 3-channel (RGB) input images and produces 64-channel feature maps, which are then globally average-pooled via AdaptiveAvgPool2d(1) to produce a 64-dimensional feature vector.

The map backbone uses a lighter ResNet with configuration [2, 2] — fewer blocks because the tactical map is simpler than the first-person view. It processes 3-channel input and produces 32-dimensional features.

The motion convolution processes the difference between consecutive frames (motion vectors) through a single convolutional layer that maps 3 input channels to 32 output channels, followed by ReLU and global average pooling.

The three streams are concatenated to produce a 128-dimensional perception vector (64 + 32 + 32).

**Trading Adaptation:** The perception module undergoes the most dramatic transformation. Instead of processing 2D images, the trading version processes 1D temporal sequences. The three streams become: (1) a Price Stream using 1D convolutions on OHLCV data with the same ResNet residual pattern [3,4,6,3], (2) an Indicator Stream using lighter 1D convolutions [2,2] on pre-computed technical indicators (RSI, MACD, Bollinger, etc.), and (3) a Momentum/Change Stream processing the first differences (returns, volume changes, indicator deltas). The concatenated output remains a 128-dimensional perception vector, preserving the downstream interface.

#### 2.2.4 RAPMemory — Temporal State Tracking (memory.py — 69 lines)

The memory module is perhaps the most architecturally innovative component of the RAP Coach and the most directly valuable for trading. It combines two complementary memory mechanisms:

**Liquid Time-Constant (LTC) Network:** The LTC layer implements continuous-time neural dynamics governed by the differential equation dh/dt = -(1/τ_i) · h_i + (1/τ_i) · f_θ(x, h), where τ_i is a learnable time constant for each neuron and f_θ is a nonlinear function. Unlike standard RNNs that process data at fixed time intervals, LTC networks naturally handle irregularly-spaced observations because the time constant τ controls how quickly each neuron responds to input. The CS2 implementation uses AutoNCP (Automatic Neural Circuit Policy) wiring with units = hidden_dim + 32, which creates a structured connectivity pattern inspired by biological neural circuits. The AutoNCP wiring divides neurons into sensory inputs, inter-neurons, command neurons, and motor outputs, creating a structured information flow.

For trading, this is exceptionally valuable because market data arrives at irregular intervals — ticks may come milliseconds apart during volatile periods and seconds apart during quiet periods. The LTC's continuous-time dynamics naturally handle this irregularity without the artificial resampling that standard LSTMs require. The time constant τ_i for each neuron will learn to respond at different speeds — some neurons will track fast-moving microstructure signals while others will track slow-moving trend signals, creating an automatic multi-timescale representation.

**Hopfield Associative Memory:** Complementing the LTC's temporal dynamics, the Hopfield layer implements a modern Continuous Hopfield Network (also known as Dense Associative Memory). The implementation in `hflayers.py` (97 lines) uses 512 learnable memory slots represented as key-value pairs: `self.memory_keys = nn.Parameter(torch.randn(512, stored_pattern_size * num_heads) * 0.02)` and `self.memory_values = nn.Parameter(torch.randn(512, stored_pattern_size * num_heads) * 0.02)`. The retrieval mechanism uses dot-product attention: scores = query @ memory_keys.T / √d_k, attention_weights = softmax(scores), retrieved = attention_weights @ memory_values. With 4 attention heads, the model can retrieve from memory using 4 different query patterns simultaneously.

For trading, the 512 memory slots will learn to store canonical market patterns — breakout formations, reversal patterns, consolidation structures, volatility clusters, liquidity events, etc. When the current market state is encoded and used as a query, the Hopfield layer retrieves the most similar stored patterns, providing historical context that informs the strategy layer's decisions. This is directly analogous to the "FAISS for approximate nearest neighbor search" specified in the V1 Bot's mathematical foundations, but integrated as a differentiable neural layer rather than an external index.

**Belief Head and Residual Combination:** The memory module's belief head is a two-layer MLP (hidden_dim → SiLU → 64) that projects the combined LTC+Hopfield state into a compact "belief" vector. The LTC output and Hopfield retrieval are combined via residual addition before being passed to the belief head. This belief vector represents the model's compressed understanding of the current situation given its temporal context and historical pattern matching.

#### 2.2.5 RAPStrategy — Decision Making with Mixture of Experts (strategy.py — 69 lines)

The strategy module implements the decision-making layer using a Mixture of Experts (MoE) architecture where each expert is a SuperpositionLayer. The implementation creates 4 expert networks, each being a SuperpositionLayer(hidden_dim, output_dim, context_dim=metadata_dim), and a gate network that routes decisions to the appropriate experts.

**Contextual Attention:** Before the MoE routing, a ContextualAttention module computes feature saliency scores using a learned query-key mechanism. This determines which aspects of the hidden state are most relevant for the current decision, producing an attention-weighted hidden state that emphasizes the most decision-relevant features.

**Gate Network:** The gate network is a linear layer (hidden_dim → num_experts) followed by softmax, producing a probability distribution over experts: g = softmax(W_g · h + b_g). The final output is the weighted combination of expert outputs: y = Σ_i g_i · expert_i(h, context).

**SuperpositionLayer Detail:** Each expert is a SuperpositionLayer that implements context-dependent gating. The layer computes: (1) a standard linear transformation out = W · x + b, (2) a context-dependent gate gate = sigmoid(W_context · context), and (3) the gated output result = out ⊙ gate. The sigmoid gating means each output dimension is independently modulated by the context — some dimensions are "opened" (gate ≈ 1) while others are "closed" (gate ≈ 0) depending on the match context (economy state, round phase, etc.). The layer also computes an L1 sparsity loss on the gate activations to encourage specialization: sparsity_loss = mean(|gate|). This loss is added to the total training loss with a small weight to encourage experts to develop distinct activation patterns.

For trading, the 4 experts map to 4 market regime specialists: (1) Trend Expert — activated when the market exhibits strong directional movement (high ADX, aligned moving averages), (2) Range Expert — activated during consolidation periods (low ADX, mean-reverting behavior), (3) Volatility Expert — activated during high-uncertainty periods (expanding Bollinger Bands, clustered large moves), and (4) Crisis Expert — activated during market dislocations (extreme VIX/VVIX, flash crashes, liquidity crises). The SuperpositionLayer's context-dependent gating allows each expert to dynamically adjust its behavior based on the specific market context — for example, the Trend Expert might behave differently depending on whether the trend is accelerating or decelerating, as captured by the context vector.

#### 2.2.6 RAPPedagogy — Value Estimation and Causal Attribution (pedagogy.py — 98 lines)

This module contains two classes that serve complementary roles in the system's output layer.

**RAPPedagogy (Critic Head):** Implements a state-value function V(s) using a two-layer MLP: hidden_dim → 64 → ReLU → 1. This estimates the "value" of the current state — in CS2, this is the expected probability of winning from the current game state. The module also includes a skill_adapter (a linear projection from a 10-dimensional skill vector to hidden_dim) that biases the value estimation based on the player's skill level. The advantage gap A_t = actual_outcome - V(s) represents the "coaching gap" — how much better or worse the outcome was compared to expectation.

For trading, V(s) becomes the expected risk-adjusted return from the current portfolio state. The skill_adapter becomes a strategy-profile adapter — different trading strategies (momentum, mean-reversion, statistical arbitrage) have different expected return profiles, and the adapter biases the value estimate accordingly. The advantage gap A_t = realized_return - V(s) directly measures whether a trade performed better or worse than expected, providing the signal for strategy improvement.

**CausalAttributor (Explainability Head):** This is the explainability engine. It maintains 5 concept categories (in CS2: Positioning, Crosshair Placement, Aggression, Utility, Rotation) and computes attribution scores for each. The implementation uses two fusion sources: (1) Neural relevance — a learned head (hidden_dim → 32 → ReLU → 5 → Sigmoid) that computes context-dependent concept relevance, and (2) Mechanical deltas — the magnitude of the recommended position/view changes, which serve as heuristic proxies for each concept's importance. The final attribution scores are the element-wise product of neural relevance and mechanical errors: attribution = context_weights ⊙ mechanical_errors.

For trading, the 5 concepts become: (1) Trend — did trend alignment contribute to the signal? (2) Momentum — did momentum indicators contribute? (3) Volatility — did volatility conditions influence the decision? (4) Volume — did volume confirmation affect the signal? (5) Correlation — did cross-asset or cross-timeframe correlations contribute? The mechanical deltas become the actual indicator values (trend strength, RSI deviation from 50, volatility z-score, volume vs. average, correlation coefficient), and the neural relevance head learns which factors are most important in the current market context.

#### 2.2.7 RAPCommunication — Skill-Conditioned Output (communication.py — 61 lines)

The communication module translates neural network outputs into human-readable advice using a template system stratified by skill level. Three tiers of templates exist: low (levels 1-3: direct, concrete advice), mid (levels 4-7: pattern-based analysis), and high (levels 8-10: strategic/abstract recommendations). A confidence gate at 0.7 suppresses output when model confidence is insufficient.

For trading, this module becomes the Signal Explanation Generator. The three tiers map to different levels of trading report detail: (1) Low tier — simple action recommendations ("Buy XAUUSD at 2050, stop at 2040, target 2070"), (2) Mid tier — pattern-based analysis ("RSI divergence on 4H chart supports long entry; ADX rising from 18 suggests emerging trend"), (3) High tier — strategic reasoning ("Current market microstructure shows VPIN declining while institutional flow increases — suggests accumulation phase before breakout. Historical pattern match (87% similarity) to March 2024 setup which resolved with 3.2% upside over 5 days"). The confidence gate is preserved and potentially raised to 0.75-0.80 for trading to ensure higher signal quality.

#### 2.2.8 Chronovisor Scanner — Multi-Scale Critical Moment Detection (chronovisor_scanner.py — 370 lines)

The Chronovisor is one of the most architecturally sophisticated modules in the CS2 Analyzer. It performs multi-scale temporal analysis to identify "critical moments" — points in time where the model's value estimate changes dramatically, indicating a pivotal decision point.

**Multi-Scale Configuration:** Three analysis scales are defined, each with distinct parameters:

- Micro scale: window=64 ticks (~1 second), lag=16, threshold=10% — detects sub-second engagement decisions
- Standard scale: window=192 ticks (~3 seconds), lag=64, threshold=15% — detects engagement-level critical moments  
- Macro scale: window=640 ticks (~10 seconds), lag=128, threshold=20% — detects strategic shifts

The analysis algorithm works by: (1) computing the model's value estimate V(s_t) at each tick using the trained RAPCoachModel, (2) computing the delta Δ_t = V(s_{t}) - V(s_{t-lag}) at each scale, (3) detecting peaks where |Δ_t| exceeds the scale's threshold, (4) clustering adjacent peaks into single events by finding the maximum delta within each event window, and (5) cross-scale deduplication that preserves the finer-grained detection when multiple scales detect the same event (priority: micro > standard > macro).

**ScanResult Structure:** The scanner returns a structured result that distinguishes between success and failure states, tracks the number of ticks analyzed, and includes the model's loaded status. Each CriticalMoment contains: match_id, start_tick, peak_tick, end_tick, severity (0-1), type ("mistake" or "play"), description, scale label, and context_ticks for review.

**Trading Adaptation:** This becomes the Multi-Timeframe Signal Detector. The three scales map naturally to trading timeframes:

- Micro (1-minute): tick-level execution signals, scalping entries/exits
- Standard (15-minute): intraday swing points, entry/exit confirmations
- Macro (4-hour): strategic regime shifts, trend changes

The delta computation becomes: Δ_t = V(portfolio_{t}) - V(portfolio_{t-lag}), and critical moments become "significant portfolio value changes" — identifying the exact market conditions that led to sharp PnL movements (either positive for learning or negative for mistake analysis). The cross-scale deduplication ensures that a trend change detected on both 15-minute and 4-hour timeframes is reported once at the finer resolution, preventing duplicate signals.

#### 2.2.9 Maturity Observatory — Model Confidence Tracking (maturity_observatory.py — 325 lines)

The MaturityObservatory is the CS2 Analyzer's self-assessment system. It continuously monitors 5 signals that indicate whether the neural network has learned enough to provide reliable recommendations:

1. **Belief Entropy** — Computes Shannon entropy H = -Σ p_i log p_i of the memory module's belief state distribution. High entropy means the model is uncertain about the current state. As training progresses, belief entropy should decrease as the model develops more refined state representations.

2. **Gate Specialization** — Measures the variance of the MoE gate weights across the batch. If all experts receive equal weight (gate_variance ≈ 0), the experts haven't specialized. If gate weights are highly concentrated (gate_variance is high), experts have developed distinct specializations. The implementation computes: specialization = Var(softmax(gate_logits)).

3. **Concept Focus** — Measures the concentration of the CausalAttributor's concept scores. Early in training, attribution scores tend to be uniformly distributed across all concepts. As the model matures, it develops sharper attributions, focusing on the most relevant concepts for each situation. Measured as: focus = max(attribution) / (mean(attribution) + ε).

4. **Value Accuracy** — Tracks the running error of the pedagogy head's value predictions V(s) against actual outcomes. Computed as the exponential moving average of |V(s) - actual_outcome|. Lower error indicates more accurate value estimation.

5. **Role Stability** — Measures the consistency of the role classification head's predictions across similar situations. Computed as the entropy of role predictions over a sliding window — low entropy means consistent role classification.

These 5 signals are combined into a single conviction index using a weighted average, and the conviction index determines the model's maturity state:

- **DOUBT** (conviction < 0.2): Model is confused, predictions unreliable
- **CRISIS** (conviction 0.2-0.4): Model in transition, conflicting signals
- **LEARNING** (conviction 0.4-0.6): Model improving, moderate reliability
- **CONVICTION** (conviction 0.6-0.8): Model confident, good reliability
- **MATURE** (conviction > 0.8): Model fully trained, maximum reliability

All metrics are logged to TensorBoard for monitoring.

**Trading Adaptation:** This module translates almost directly. The 5 signals become:

1. Prediction Uncertainty — entropy of the model's output distribution
2. Regime Detector Confidence — specialization of the MoE gate weights (are regime experts distinct?)
3. Feature Importance Stability — consistency of feature attributions over time
4. PnL Prediction Accuracy — running error of V(s) against realized returns
5. Strategy Consistency — stability of the decision engine's choices in similar market conditions

The conviction index and maturity states serve the same purpose: preventing the system from trading with an under-trained or destabilized model. The maturity gate (currently set at the CALIBRATING/LEARNING/MATURE tier system in coach_manager.py) controls position sizing — CALIBRATING models trade paper or with minimal size, LEARNING models trade with reduced size, and MATURE models trade at full capacity.

#### 2.2.10 Training Orchestrator (training_orchestrator.py — 324 lines)

The TrainingOrchestrator manages the training lifecycle with the following features:

- **Epoch Control:** Configurable number of epochs with progress reporting
- **Batch Processing:** Configurable batch size with support for variable-length sequences via the FeatureExtractor
- **Early Stopping:** Monitors validation loss with a patience parameter — if validation loss hasn't improved for `patience` consecutive epochs, training stops to prevent overfitting
- **Best-Model Checkpointing:** Saves the model weights whenever validation loss reaches a new minimum, ensuring the best model is always preserved even if subsequent training degrades performance
- **Dashboard Reporting:** Sends progress updates (current epoch, loss, validation metrics) to a monitoring dashboard

The orchestrator uses a unified FeatureExtractor to ensure that training and inference use exactly the same feature computation pipeline — this prevents the common and dangerous bug of training/inference feature mismatch.

For trading, this module is reusable almost without modification. The only changes required are: (1) replacing the CS2-specific dataset loading with market data loading, (2) adjusting the validation strategy from random validation splits to walk-forward validation (where the model is always validated on data that comes after the training data chronologically), and (3) adding trading-specific metrics to the dashboard reporting (Sharpe ratio, max drawdown, win rate, etc.).

#### 2.2.11 Coach Training Manager (coach_manager.py — 732 lines)

The CoachTrainingManager is the highest-level training coordinator. It implements the "Global Wisdom + Local Adaptation" training cycle:

**Maturity Tier System:**

- CALIBRATING (0-49 demos processed): 50% confidence multiplier — system is learning, low confidence
- LEARNING (50-199 demos processed): 80% confidence multiplier — system is improving, medium confidence
- MATURE (200+ demos processed): 100% confidence multiplier — full coaching capability

**Training Phases:**

1. JEPA Pre-training on pro data (self-supervised representation learning)
2. RAP Behavioral Training (supervised coaching prediction)
3. Role Head Training (specialized role classification)

**Dataset Split Strategy:** Chronological 70/15/15 split (train/validation/test) with explicit prevention of temporal data leakage — the model never sees future data during training. Pro and user matches are split independently to maintain class balance. All matches are re-assigned to splits each cycle so boundaries shift as new data arrives.

**10/10 Rule:** Minimum 10 pro demos + 10 user demos before any training begins. This prevents the model from training on insufficient data.

**Feature Specification:** Two feature sets are defined:

- TRAINING_FEATURES (tick-level, 19 dimensions): health, armor, has_helmet, has_defuser, equipment_value, is_crouching, is_scoped, is_blinded, enemies_visible, x, y, z, round_time, weapon_class, ammo_percent, alive_teammates, alive_enemies, flash_remaining, smoke_remaining
- MATCH_AGGREGATE_FEATURES (match-level, 25 dimensions): avg_kills, avg_deaths, avg_adr, avg_hs, avg_kast, kill_std, adr_std, kd_ratio, impact_rounds, accuracy, avg_equipment_value, avg_flash_assists, rounds_played, rating_2_0, rating_impact, rating_kast, rating_survival, clutch_win_pct, opening_duel_win_pct, utility_blind_time, utility_enemies_blinded, utility_damage, positional_aggression_score, avg_saving_rate, avg_plant_rate

For trading, the maturity tier system translates directly: CALIBRATING (0-200 training episodes) → paper trading only, LEARNING (200-1000 episodes) → reduced position sizing, MATURE (1000+ episodes) → full position sizing. The training phases become: (1) JEPA self-supervised pre-training on historical market data, (2) Supervised trading signal prediction, (3) Regime-specific head training.

---

### 2.3 Analysis Engine Layer — Deep Analysis

The analysis engine layer contains six specialized modules that perform game-theoretic, statistical, and behavioral analysis. Each module is designed to produce a specific type of insight that feeds into the coaching pipeline. In the trading domain, these modules transform into market analysis engines that detect patterns, anomalies, and behavioral signals in price data. This section examines each module with enough depth to specify the exact transformations required.

#### 2.3.1 Game Tree — Expectiminimax Search (game_tree.py — 446 lines)

The game tree module implements an Expectiminimax search algorithm, which is a generalization of the minimax algorithm that handles chance nodes (stochastic events). This is a sophisticated decision-theoretic approach that evaluates all possible future game states to determine the optimal current action.

**Search Architecture:** The tree alternates between three node types: MAX nodes (the player's decisions, where the best outcome is selected), MIN nodes (the opponent's decisions, where the worst outcome is assumed), and CHANCE nodes (stochastic events like grenades, random spray patterns, etc., where outcomes are weighted by probability). The search is depth-limited with a configurable node budget (default 1000 nodes) to ensure real-time performance.

**OpponentModel — Adaptive Action Probabilities:** The most sophisticated sub-component is the OpponentModel, which maintains a probability distribution over the opponent's possible actions and updates this distribution based on observed behavior. The model uses economy-based priors as its starting point — for example, in an eco round (low money), opponents are more likely to play passive, group up, and use pistols. In a full-buy round, opponents are more likely to use utility heavily and execute complex strategies. These priors are stored as probability maps indexed by economy state (eco/force-buy/full-buy).

The model then applies Bayesian updating: as the match progresses and opponent actions are observed, the model blends the priors with observed frequencies using EMA (Exponential Moving Average): updated_prob = α × observed_freq + (1-α) × prior_prob. This allows the model to adapt to each specific opponent rather than relying solely on general priors.

**Leaf Evaluation:** When the search reaches a leaf node (either maximum depth or node budget exhausted), the WinProbabilityPredictor neural network evaluates the state's value. This neural network takes 12 game-state features and outputs a win probability.

**Trading Adaptation — ScenarioAnalyzer:** This module transforms into a scenario analysis engine for trading. The three node types become: MAX nodes (the trader's position decisions — enter, exit, scale up, scale down), MIN nodes (adverse market movements — the worst-case market reaction), and CHANCE nodes (probabilistic market events — earnings releases, central bank decisions, geopolitical events, each weighted by their probability and expected impact).

The OpponentModel becomes a CounterpartyBehaviorModel that tracks institutional flow patterns. Instead of economy-based priors, it uses market-microstructure priors: in low-volume environments, price movements are more likely to be noise (lower information content); in high-volume environments, movements are more likely to represent genuine information flow. The Bayesian updating mechanism tracks how the market typically reacts to specific patterns (e.g., how often a breakout above resistance leads to continuation vs. a false breakout) and updates these probabilities based on recent observations.

The leaf evaluation becomes a PositionValuePredictor that estimates the expected risk-adjusted return of holding the current position for the remaining time horizon, given the scenario's market state. This incorporates the V1 Bot's mathematical foundations: VaR, CVaR, and Kelly Criterion calculations at the leaf nodes ensure that even the most optimistic scenarios are evaluated through a risk-management lens.

The node budget of 1000 translates to a computational limit appropriate for real-time market analysis — enough to evaluate hundreds of scenarios while still producing results within seconds of receiving new market data.

#### 2.3.2 Blind Spot Detection (blind_spots.py — 208 lines)

The blind spot detector is a meta-analytical module that identifies recurring suboptimal decisions by comparing a player's actual actions against the game tree's recommended optimal actions. It operates across multiple rounds to identify patterns rather than one-off mistakes.

**Situation Classification:** Each decision point is classified into a situation category: "eco round," "1vN clutch," "post-plant," "numbers advantage," "retake," etc. This classification allows the detector to compute per-situation statistics — a player might perform optimally in eco rounds but consistently make mistakes in post-plant situations.

**Deviation Scoring:** For each situation where the player's action diverged from the game tree's recommendation, a deviation score is computed: deviation = |V(actual_action) - V(optimal_action)| / V(optimal_action), representing the percentage of value lost through the suboptimal decision. Deviations are accumulated per situation category.

**Priority Computation:** Blind spots are prioritized as: priority = frequency × average_impact_rating, where frequency is how often the suboptimal pattern occurs and impact_rating is the average deviation score. This ensures that both common mild mistakes and rare catastrophic mistakes are surfaced.

**Training Plan Generation:** For each identified blind spot, the module generates a natural-language training plan describing: the situation category, the typical mistake, the optimal action, and drills to practice. For example: "In 1v2 post-plant situations (encountered 14 times), you tend to peek aggressively (deviation: 23%). The optimal approach is to hold a close angle and use the ticking bomb as time pressure. Practice: 1v2 retake scenarios on workshop maps focusing on patience."

**Trading Adaptation — TradingWeaknessAnalyzer:** This becomes a powerful tool for systematic trading improvement. The situation classification maps to market conditions: "trending breakout," "false breakout," "mean-reversion setup," "news-driven spike," "low-liquidity gap," "end-of-session drift," etc. Each trade is classified into its situation category based on the market conditions at the time of entry.

The deviation scoring computes: for each trade, what was the optimal action (as determined by the model's hindsight analysis), and how far did the actual trade deviate? For example, if the model determines that the optimal exit was at +2.5% but the trader exited at +0.8% (premature exit due to fear), the deviation is (2.5 - 0.8) / 2.5 = 68%. If the trader held through a drawdown that the model would have exited, the deviation measures the unnecessary risk taken.

The blind spots become patterns like: "During trending breakouts (12 occurrences), you consistently take profit too early (avg deviation: 34%). Recommendation: use a trailing stop at 2× ATR instead of fixed take-profit targets." Or: "During false breakouts (8 occurrences), you enter too quickly without confirmation (avg deviation: 52%). Recommendation: wait for the first pullback after breakout and confirm with volume."

The training plan generation produces actionable trade journals with statistics, ensuring that the trader (or the automated system) systematically improves on its weakest areas.

#### 2.3.3 Momentum Tracker (momentum.py — 197 lines)

The momentum tracker models the psychological impact of consecutive outcomes on subsequent performance. It maintains a running "momentum multiplier" that captures whether a player is on a hot streak (multiplier > 1.0) or tilting (multiplier < 1.0).

**Exponential Decay Formula:** The core computation is: multiplier = base ± Δ × streak_length × e^(-λ × gap), where Δ = 0.05 (increment per streak unit), λ = 0.15 (decay rate), and gap is the number of rounds since the last outcome in the streak. The ± depends on whether the streak is positive (winning) or negative (losing). The exponential decay ensures that recent streaks have stronger effects — a streak from 3 rounds ago has less impact than a streak from the current round.

**Bounds:** The multiplier is clamped to [0.7, 1.4], preventing extreme values that could destabilize the system because even the worst tilt can't reduce the system to below 70% effectiveness, and even the hottest streak can't boost it beyond 140%.

**Tilt Detection:** When the multiplier drops below 0.85, the system flags a "tilt" state, indicating that the player may be making emotionally-driven decisions. This triggers specific coaching interventions (take a break, breathe, reset mentally).

**Hot Streak Detection:** When the multiplier rises above 1.2, the system flags a "hot streak" state, indicating elevated performance but also warning about potential overconfidence.

**Half-Switch Reset:** When the match reaches half-time (teams switch sides), the momentum multiplier is partially reset toward 1.0 via a blending operation: multiplier = 0.7 × 1.0 + 0.3 × current_multiplier. This accounts for the psychological reset that comes with switching sides while preserving some of the momentum state.

**Trading Adaptation — PnLMomentumTracker:** This translates almost directly to trading psychology management. The streak tracking becomes win/loss streak tracking on trades: consecutive winning trades build positive momentum (multiplier increases), consecutive losing trades build negative momentum (multiplier decreases).

The exponential decay accounts for the time between trades — a losing streak from yesterday has less impact than a losing streak from the last hour. The formula becomes: multiplier = base ± 0.05 × streak_length × e^(-0.15 × hours_since_last_trade).

Tilt detection at multiplier < 0.85 triggers automated position-sizing reduction — when the system detects that the trader (or automated system) is "tilting," it automatically reduces position sizes to limit the damage from emotionally-driven trades. This is a critical risk management feature that most trading systems lack.

Hot streak detection at multiplier > 1.2 triggers an overconfidence warning and can either maintain current position sizes (preventing the system from increasing risk due to temporary hot streak) or slightly reduce sizes (acknowledging that mean-reversion of performance is statistically likely after an unusually good streak).

The half-switch reset becomes a session boundary reset — at the start of each new trading day, the momentum multiplier is partially reset toward 1.0 (multiplier = 0.7 × 1.0 + 0.3 × previous), acknowledging the psychological reset of a new session while preserving some carry-over state.

The trading system adds one important extension not present in the CS2 version: drawdown-based momentum adjustment. When the portfolio drawdown exceeds certain thresholds (2%, 5%, 10%), additional negative momentum is applied regardless of the recent streak, because large drawdowns create psychological pressure that affects decision quality even after a few winning trades.

#### 2.3.4 Deception Index (deception_index.py — 218 lines)

The deception index quantifies tactical misdirection by measuring three independent signals of deceptive behavior and combining them into a composite score.

**Flash Bait Detection (weight: 0.25):** Counts flashbangs thrown that didn't blind any enemies within a 2-second window (128 ticks at 64 tick rate). A high "empty flash" rate indicates deliberate bait usage — throwing flashes not to blind but to create the expectation of a push, then rotating elsewhere.

**Rotation Feint Detection (weight: 0.40):** This is the most heavily-weighted signal. It analyzes player movement trajectories by sampling positions at regular intervals and computing direction changes. When a player moves toward Site A and then abruptly reverses direction (angle change > 108°, i.e. > 0.6π radians) toward Site B, this is classified as a rotation feint. The feint rate is the ratio of significant direction changes to total direction changes.

**Sound Deception Detection (weight: 0.35):** Analyzes the ratio of crouching (silent movement) to sprinting (noisy movement) in non-combat zones. Counter-intuitively, a LOW crouch ratio in safe zones indicates potential deception — the player is deliberately making noise to create false location information. The score inverts the crouch ratio: score = 1.0 - crouch_ratio × 2.0.

**Composite Index:** composite = 0.25 × flash_bait + 0.40 × rotation_feint + 0.35 × sound_deception, clamped to [0, 1].

**Baseline Comparison:** The module generates natural-language comparisons against pro player baselines: "Your deception index (0.72) is above the pro baseline (0.58). Your fakes and rotations are well-developed."

**Trading Adaptation — MarketManipulationDetector:** This becomes a sophisticated market manipulation detector. The three signals transform into:

1. **Spoofing Detection (weight: 0.25):** Detects large orders placed and then quickly cancelled before they can be filled. Analogous to "fake flashes" — orders intended to create the illusion of demand/supply without actual intent to trade. Implementation: monitor the order book for orders that are placed and cancelled within a short window, calculating the ratio of cancelled volume to filled volume.

2. **Fake Breakout Detection (weight: 0.40):** Detects price movements that break through support/resistance levels but then immediately reverse — analogous to rotation feints. Implementation: track price trajectories through key levels and measure the "reversal angle" — how sharply and quickly the price reverses after the breakout. A breakout that reverses within a few candles with high volume on the reversal is classified as a fake breakout.

3. **Volume Deception Detection (weight: 0.35):** Detects wash trading or artificial volume — analogous to sound deception (creating noise to mislead). Implementation: analyze the ratio of volume that leads to price movement vs. volume that doesn't (churn). High volume with low price impact suggests artificial volume generation.

The composite manipulation index warns the trading system to be cautious — when market manipulation is detected, the system should reduce position sizes, widen stop-losses, or avoid trading entirely until the manipulation signal subsides.

#### 2.3.5 Entropy Analysis (entropy_analysis.py — 146 lines)

The entropy analyzer measures the information-theoretic impact of tactical actions by computing Shannon entropy of spatial distributions before and after events.

**Shannon Entropy Computation:** The map is discretized into a 32×32 grid. Player positions are mapped to grid cells, producing a probability distribution p(cell) = count(cell) / total_count. Shannon entropy is then H = -Σ p_i log₂ p_i, measured in bits. Higher entropy means more dispersed positions (more uncertainty about enemy locations), while lower entropy means more clustered positions (more certainty).

**Utility Impact Analysis:** For each utility throw (smoke, flash, molotov, HE grenade), the analyzer computes: (1) pre-throw entropy H_pre (enemy position uncertainty before the utility), (2) post-throw entropy H_post (enemy position uncertainty after the utility), (3) entropy delta ΔH = H_pre - H_post (information gained from the utility), and (4) effectiveness rating = ΔH / max_delta, where max_delta is the theoretical maximum entropy reduction for each utility type (smoke=2.5 bits, flash=1.8, molotov=2.0, HE=1.5).

**Utility Ranking:** The analyzer sorts all utility throws by effectiveness rating in descending order, enabling coaching messages like "Your best smoke reduced enemy position uncertainty by 2.1 bits (84% effectiveness)."

**Trading Adaptation — SignalQualityMeter:** This module transforms into a signal quality assessment tool that measures the information content of trading signals and market events.

The Shannon entropy computation applies to the distribution of price returns across discrete bins — a market with uniformly distributed returns has high entropy (high uncertainty, no clear direction), while a market with concentrated returns has low entropy (clear directional bias or mean-reverting behavior). This provides a quantitative measure of "market clarity" that can gate the trading system's activity level—high entropy markets may warrant reduced position sizes because the direction is unclear.

The utility impact analysis becomes an event impact analyzer: for each significant market event (news release, central bank announcement, technical level break), compute the entropy of the return distribution before the event (H_pre) and after the event (H_post). If ΔH is large and positive (entropy decreased), the event resolved uncertainty and provided clear directional information. If ΔH is small or negative, the event created more confusion than clarity. This directly informs the V1 Bot's information-theoretic framework using Shannon Entropy and KL Divergence.

The effectiveness rating per event type provides meta-analysis: "Non-Farm Payroll releases resolve an average of 1.8 bits of uncertainty (90% effectiveness), while FOMC minutes resolve only 0.9 bits (45% effectiveness)." This informs the system's event-handling strategy — high-effectiveness events warrant wider pre-event position management.

#### 2.3.6 Win Probability Predictor (win_probability.py — 284 lines)

The win probability module predicts the likelihood of winning the current round given the game state. It uses a small neural network and heuristic adjustments for edge cases.

**Neural Network Architecture:** The network processes 12 input features through a 3-layer architecture: 12 → 64 → ReLU → Dropout(0.2) → 32 → ReLU → Dropout(0.2) → 1 → Sigmoid. The 12 features include: alive_ct, alive_t, ct_total_hp, t_total_hp, ct_equipment_value, t_equipment_value, bomb_planted (binary), time_remaining, ct_utility_count, t_utility_count, round_number, and economy_advantage.

**Heuristic Adjustments:** For extreme states that the neural network may not have seen enough training examples for, heuristic rules override: if one team has 5 alive and the other has 1, the probability is clamped in favor of the larger team. If the bomb is planted and time is very low, T-side probability is boosted. These heuristics act as guardrails against neural network error in low-data-density regions of the state space.

**Natural-Language Explanations:** The module generates explanations for its predictions, identifying the dominant factors: "CT win probability: 72% — primarily driven by numbers advantage (4v2) and equipment superiority (+$3,200)."

**Trading Adaptation — TradeSuccessPredictor:** This becomes a trade outcome predictor that estimates the probability of a trade reaching its take-profit before its stop-loss. The 12 features become: position_size_pct, entry_distance_from_support, entry_distance_from_resistance, current_atr, trend_alignment_score (1.0 if position direction matches trend, 0.0 if against), rsi_value, volume_ratio (current/average), spread_as_pct_of_atr, momentum_multiplier (from the PnLMomentumTracker), regime_classification_confidence, time_to_major_event, and correlation_with_usd_index.

The heuristic adjustments become: if a trade is entered against a strong trend (ADX > 40 and position against trend direction), the success probability is clamped downward regardless of other factors. If a trade is entered with massive volume confirmation (volume > 3× average) in the direction of the trend, the probability is boosted. These heuristics encode trading wisdom that the neural network may lack in edge cases.

---

### 2.4 Knowledge and Experience Layer — Deep Analysis

#### 2.4.1 Experience Bank — COPER Framework (experience_bank.py — 733 lines)

The ExperienceBank is the CS2 Analyzer's long-term memory system, implementing the COPER (Context-Optimized Prompt with Experience and Replay) framework. This is one of the most architecturally sophisticated modules and one of the most valuable for trading adaptation.

**ExperienceContext — Structured Context Hashing:** Each experience (a round of gameplay with its outcome) is stored with a structured context that includes: map, round_type (eco/force/full), team_composition, economy_state, score_differential, and situation_class. The context is hashed using a deterministic hash function to enable fast exact-match retrieval. The hash combines all context fields: `hash = md5(f"{map}:{round_type}:{economy}:{score_diff}")`. This enables O(1) lookup of experiences in identical contexts.

**Dual Retrieval Strategy:** The module implements two complementary retrieval mechanisms running in parallel:

1. **Semantic Retrieval:** Uses Sentence-BERT (all-MiniLM-L6-v2, 384-dimensional embeddings) to encode the current situation as a text description, then performs cosine similarity search against the embeddings of all stored experiences. This finds experiences that are semantically similar even if the exact game state differs — for example, a clutch situation on Mirage might match a clutch situation on Inferno if the tactical dynamics are similar. The retrieval returns the top-k most similar experiences with their similarity scores.

2. **Hash Retrieval:** Uses the deterministic context hash for exact-match retrieval. This finds experiences in exactly the same context (same map, same economy state, same score differential) and is useful when the system has already encountered this exact situation before.

**Pro Example Filtering:** The experience bank stores both pro player and regular player experiences, with a filter that can retrieve only pro-level examples. This allows the system to compare the current player's behavior against what a professional would do in the same situation.

**Advice Synthesis (COPER):** The core COPER synthesis takes: (1) Context — the current situation, (2) Retrieved Experiences — the most relevant past experiences, (3) Pro Examples — what professionals did in similar situations, (4) Current Performance Metrics — how the player is currently performing, and synthesizes personalized advice. The synthesis considers: the delta between the player's actual behavior and the retrieved pro examples, the outcomes of past similar experiences (did following the pro strategy lead to better outcomes?), and the player's current skill level (no point recommending advanced strategies to beginners).

**Feedback Loop:** After each match, the system evaluates whether previous coaching advice was followed and whether the outcome improved. This is implemented as: (1) Match N generates coaching advice, (2) Match N+1's performance is compared against Match N's, (3) If performance improved in the coached areas, the advice is reinforced (increased weight in future retrievals), (4) If performance didn't improve, the advice is de-weighted or the system generates alternative advice.

**Demo Extraction Pipeline:** The system can automatically extract experiences from parsed demo files, creating structured ExperienceContext objects with computed features and outcomes for each round. This pipeline normalizes the raw tick data into the standardized experience format.

**Trading Adaptation — TradeHistoryBank:** This becomes the trading system's institutional memory. The adaptation preserves all five pillars of the COPER framework:

**Trade Context Hashing:** Each trade is stored with a structured context: instrument (XAUUSD), timeframe (1H, 4H, D), regime (trending/ranging/volatile/crisis), volatility_quartile (low/medium/high/extreme), session (London/NY/Asia), day_of_week, and distance_to_next_event. The hash enables instant recall: "Have I ever traded XAUUSD in a trending regime with high volatility during London session before?"

**Dual Retrieval for Trading:**

1. Semantic Retrieval — Encode the current market description ("XAUUSD breaking above resistance at 2050 with increasing volume and RSI at 62 during NY session") and find the most similar historical trades. This catches non-obvious similarities: a breakout setup in XAUUSD might semantically match a breakout setup in Silver or EUR/USD because the pattern dynamics are similar.
2. Hash Retrieval — Exact-match lookup for identical market conditions. If the system has traded XAUUSD in a trending regime with high volatility during London session before, retrieve those exact trades and their outcomes instantly.

**Pro Example Filtering** becomes Institutional Pattern Matching — filtering for trades that match patterns identified in institutional flow data (large block trades, systematic fund positioning) rather than retail noise.

**Advice Synthesis (COPER for Trading):**

1. Context — Current market state (regime, volatility, correlations, calendar events)
2. Experiences — Similar past trades from the TradeHistoryBank (with outcomes)
3. Pro Examples — Institutional patterns from the filtered dataset
4. Current Metrics — Recent PnL, win rate, drawdown level, momentum multiplier
Synthesis output: "Based on 23 similar trades in trending regimes with high volatility, the optimal strategy has been to enter on the first pullback after breakout (65% win rate, 2.1R average) rather than chasing the breakout directly (48% win rate, 1.3R average). Your recent trades show a pattern of chasing entries — recommend waiting for the pullback."

**Feedback Loop for Trading:** After each trade is closed, the system evaluates: (1) Did the TradeHistoryBank's advice match the actual trade decision? (2) Was the outcome positive or negative? (3) If the advice was followed and the outcome was positive, increase the weight of that advice template. (4) If the advice was ignored and the outcome was negative, flag this as a "confirmed blind spot." (5) If the advice was followed but the outcome was negative, analyze whether the advice was fundamentally wrong (needs de-weighting) or whether it was a statistically expected loss (maintain weight). This creates a continuously improving feedback loop where the system's advice quality improves with every trade.

#### 2.4.2 RAG Knowledge System (rag_knowledge.py — 472 lines)

The RAG (Retrieval-Augmented Generation) Knowledge system provides a semantic search interface over a curated knowledge base of tactical information.

**Embedding Pipeline:** Text is embedded using Sentence-BERT (all-MiniLM-L6-v2), producing 384-dimensional dense vectors. The system includes a TF-IDF fallback for environments where the Sentence-BERT model is unavailable. Embeddings are cached after computation to avoid redundant encoding.

**Knowledge Structure:** Each knowledge entry (TacticalKnowledge in the database) contains: category (smoke, flash, position, rotation, economy), map, side (CT/T), description, pro_references (links to professional examples), and the computed embedding vector. The entries are populated from curated JSON files.

**Retrieval Algorithm:** Given a query, the system: (1) embeds the query using Sentence-BERT, (2) computes cosine similarity against all knowledge entries, (3) optionally filters by category and/or map, (4) returns the top-k entries with similarity scores, (5) increments a usage counter on each returned entry for analytics.

**Usage Tracking:** Each knowledge entry maintains a usage count, enabling the system to identify which knowledge is most frequently accessed and which is unused (potentially outdated or irrelevant).

**Trading Adaptation — StrategyKnowledgeBase:** This becomes the trading system's strategic reference library. The knowledge categories transform from CS2 tactical categories to trading categories:

| CS2 Category | Trading Category | Example Content |
|---|---|---|
| Smoke | Stop-Loss Strategy | Best practices for stop-loss placement relative to ATR, support/resistance, and volatility |
| Flash | Entry Timing | Entry signal confirmation techniques, pullback entry strategies, breakout vs. retest entries |
| Position | Position Sizing | Kelly Criterion application, volatility-adjusted sizing, drawdown-based scaling |
| Rotation | Portfolio Rotation | Sector rotation signals, risk-on/risk-off switching, correlation-based rebalancing |
| Economy | Money Management | Compound growth strategies, risk capital allocation, max drawdown limits |

The knowledge base is populated from the V1 Bot's mathematical foundations documents — each formula, technique, and indicator from the 6,000+ lines of mathematical specification becomes a searchable knowledge entry. For example, the Kalman Filter entry would contain: "The Kalman Filter provides optimal state estimation for noisy linear systems. In trading, it can be used to estimate the true price level from noisy market data, with the state equation x_{t|t} = x_{t|t-1} + K_t(z_t - H·x_{t|t-1}) where K_t is the Kalman gain. Apply when: estimating trend direction from noisy intraday data, filtering RSI values for smoother signals, estimating volatility state. Reference: V1 Bot Mathematical Foundations §5.4."

---

## Part III: Services and Orchestration Layer — Deep Analysis

### 3.1 Coaching Service — 4-Mode Pipeline (coaching_service.py — 519 lines)

The CoachingService is the CS2 Analyzer's main orchestration module that coordinates all analysis and coaching subsystems into a unified output. It implements a 4-mode coaching pipeline with cascading fallback:

**Mode 1 — COPER (Recommended):** Uses the ExperienceBank to retrieve contextually relevant past experiences, combines them with RAG knowledge retrieval, and synthesizes personalized coaching. This mode produces the highest-quality coaching because it draws on both direct experience and curated knowledge. The coaching output includes: primary recommendation, supporting evidence from past experiences, pro player comparisons, and confidence score.

**Mode 2 — Hybrid:** Combines ML model predictions (from the JEPA or RAP Coach model) with RAG knowledge retrieval. The ML model generates feature-level deviations from the pro baseline (expressed as Z-scores), and the RAG system retrieves relevant knowledge entries to provide context for those deviations. The output is a ranked list of insights with severity tiers (CRITICAL: |Z| > 3, HIGH: |Z| > 2, MEDIUM: |Z| > 1, LOW: |Z| ≤ 1).

**Mode 3 — RAG:** Pure knowledge retrieval without ML predictions. Uses the current game context (map, round type, situation) to retrieve relevant tactical knowledge entries. This mode is the fallback when ML models are unavailable or immature.

**Mode 4 — Legacy:** Static deviation-based corrections using hardcoded thresholds. For example: "If crosshair height is below 60% of standard height, suggest: raise crosshair placement." This is the last resort when all other modes fail.

**Phase 6 Advanced Analysis:** In addition to the main coaching pipeline, the service coordinates Phase 6 advanced analysis modules: momentum analysis (detecting tilt/hot states), deception analysis (scoring tactical sophistication), entropy analysis (evaluating utility effectiveness), strategy analysis (game tree + blind spot detection), and engagement range analysis (spatial pattern analysis). These analyses are appended to the coaching output as supplementary insights.

**Temporal Baselines:** The service maintains running baselines of the player's performance metrics, updating them after each match. This allows differential analysis: "Your crosshair placement improved by 12% compared to your last 5 matches."

**Differential Heatmap Insights:** The service can generate heatmap comparisons showing where the player's position distribution differs from pro player position distributions on the same map. Regions with large deltas are flagged as areas for improvement.

**Trading Adaptation — TradingAdvisorService:** This is the trading system's main orchestration layer. The 4-mode pipeline becomes:

**Mode 1 — COPER Trading:** Uses the TradeHistoryBank to retrieve similar past trades, combines them with StrategyKnowledgeBase entries, and synthesizes a personalized trading recommendation. Output: "Based on 18 similar setups (trending regime, high volatility, London session), the recommended approach is: long entry on pullback to 2045 (20-EMA support), stop at 2038 (below 50-EMA), target 1:2.5R. Historical win rate for this setup: 67%."

**Mode 2 — Hybrid Trading:** Combines the JEPA/RAP model's predictions (Z-score deviations from historical baselines) with StrategyKnowledgeBase retrieval. Output: "RSI deviation: +2.3σ (overbought relative to regime baseline). Volume deviation: -1.5σ (below average). Knowledge match: 'In trending gold markets, RSI overbought divergence from price is a stronger signal than RSI overbought absolute value — wait for price confirmation before shorting.'"

**Mode 3 — Knowledge-Only:** Pure retrieval from the StrategyKnowledgeBase. Used when models are immature or when the market regime is unclear.

**Mode 4 — Conservative:** Simple rule-based system using classical technical analysis (moving average crossovers, RSI overbought/oversold, Bollinger Band touches) with conservative position sizing. This is the "never lose money" mode.

### 3.2 Hybrid Coaching Engine (hybrid_engine.py — 610 lines)

The HybridCoachingEngine is responsible for fusing ML predictions with knowledge retrieval into unified insights. This is the core intelligence module that determines what to say and how confident to be.

**Z-Score Deviation Analysis:** The engine computes Z-scores for each player metric relative to the pro baseline: Z = (player_metric - pro_mean) / pro_std. Metrics with |Z| > 1 are flagged as deviations. The Z-scores are computed across 25 match-aggregate features (the same features used by CoachTrainingManager).

**ML Model Integration:** When an ML model is available and mature, the engine uses it to generate predictions for "what a pro player would do in this situation." The delta between the model's prediction and the player's actual behavior provides additional deviation signals.

**Knowledge Retrieval Context:** The engine constructs a retrieval query from the current context: "{map_name} {side} {round_type} {situation_class}" and retrieves relevant tactical knowledge. The retrieved knowledge is filtered by relevance score (cosine similarity > 0.3) and used to provide context for the ML-detected deviations.

**Confidence Computation:** The final confidence for each insight is: confidence = |Z_score| × knowledge_effectiveness × meta_drift_adjustment. This means that a deviation needs to be both statistically significant (high |Z|) AND have relevant knowledge support (high knowledge_effectiveness) to be reported with high confidence. The meta_drift_adjustment reduces confidence when the system detects that its baselines may be drifting.

**Insight Prioritization:** Insights are categorized into priority tiers: CRITICAL (|Z| > 3, confidence > 0.8), HIGH (|Z| > 2, confidence > 0.6), MEDIUM (|Z| > 1, confidence > 0.4), LOW (otherwise). Only HIGH and CRITICAL insights are presented by default; MEDIUM and LOW are available on request.

**Trading Adaptation — HybridSignalEngine:** The Z-score analysis becomes the core signal generation mechanism. Instead of comparing player metrics to pro baselines, the engine compares current market conditions to historical regime baselines:

- Volatility Z-score: How unusual is current volatility compared to the historical average for this regime?
- Momentum Z-score: How strong is the current trend momentum compared to historical trends in this regime?
- Volume Z-score: How unusual is the current volume compared to the baseline?
- Correlation Z-score: How unusual are current cross-asset correlations?

When multiple Z-scores align (e.g., high momentum + rising volume + normal volatility), the system generates high-confidence trend-following signals. When Z-scores conflict (e.g., high momentum but declining volume), the system generates lower-confidence signals with caveats.

The knowledge retrieval provides trading context: "Historical data shows that gold breakouts above round-number resistance with volume > 1.5σ have a 71% probability of continuation within 24 hours (Source: V1 Bot §14.7.2, Market Microstructure)."

### 3.3 Analysis Orchestrator (analysis_orchestrator.py — 480 lines)

The AnalysisOrchestrator coordinates all Phase 6 analysis modules into a structured analysis report. It manages the execution order, handles dependencies between modules, and aggregates results.

**Module Coordination:** The orchestrator runs the following modules in sequence:

1. Momentum Analysis → Produces tilt/hot state and multiplier
2. Deception Analysis → Produces deception composite index
3. Entropy Analysis → Produces utility effectiveness rankings
4. Strategy Analysis → Runs game tree + blind spot detection
5. Engagement Range Analysis → Produces spatial pattern insights

Each module's output is captured and structured into an analysis report that includes raw metrics, comparisons to baselines, natural-language summaries, and priority-ranked recommendations.

**Trading Adaptation — MarketAnalysisOrchestrator:** The orchestration pattern is directly reusable. The module sequence becomes:

1. PnL Momentum Analysis → Hot/tilt state, confidence multiplier
2. Manipulation Detection → Market manipulation composite index
3. Signal Quality Analysis → Information content of current signals
4. Scenario Analysis → Game-tree evaluation of position outcomes
5. Weakness Analysis → Recurring mistake patterns
6. Multi-Timeframe Analysis → Cross-timeframe signal confirmation

---

## Part IV: Processing and Feature Engineering — Detailed Merger Specification

### 4.1 FeatureExtractor — The Bridge Between Raw Data and Neural Networks (vectorizer.py — 267 lines)

The FeatureExtractor is the single most critical module for ensuring consistency between training and inference. The CS2 Analyzer enforces a strict rule: both training (StateReconstructor) and inference (GhostEngine) MUST use this single implementation. This prevents the dangerous and common bug of training/inference feature mismatch, where the model sees slightly different feature distributions at inference time than it was trained on, leading to degraded performance that is extremely difficult to debug.

**METADATA_DIM = 25:** The unified feature vector contains exactly 25 dimensions, carefully chosen to capture all relevant aspects of the game state while remaining compact enough for efficient neural network processing.

**Feature Groups:**

- Core Vitals (indices 0-4): health (0-100 normalized to 0-1), armor (0-100 normalized), has_helmet (binary), has_defuser (binary), equipment_value (normalized by round economy cap)
- Movement State (indices 5-7): is_crouching (binary), is_scoped (binary), is_blinded (binary)
- Tactical Awareness (index 8): enemies_visible (count, normalized by team size)
- Spatial Position (indices 9-11): x, y, z coordinates (normalized to [0,1] by map bounds)
- Round Context (indices 12-18): round_time (normalized by round duration), weapon_class (0.0-1.0 categorical encoding from WEAPON_CLASS_MAP), ammo_percent (current/max), alive_teammates (normalized by 5), alive_enemies (normalized by 5), flash_remaining (count), smoke_remaining (count)
- Map Context (indices 19-24): distance_to_site_a (normalized), distance_to_site_b (normalized), elevation (z-delta from map average), zone_encoding (3 dims for map region categorization)

**Weapon Class Map:** An important design decision is the encoding of weapons as a continuous variable (0.0 to 1.0) rather than one-hot encoding. This preserves the ordinal relationship between weapon tiers: knife (0.0) < pistol (0.2) < SMG (0.4) < rifle (0.6) < sniper (0.8) < heavy (1.0). This encoding is more compact than one-hot and allows the neural network to learn that "rifle > SMG" without seeing every possible weapon pair.

**HeuristicConfig Integration:** The FeatureExtractor supports runtime hot-swapping of normalization bounds via a HeuristicConfig object. This allows the system to update its normalization ranges as it encounters new data without requiring model retraining — for example, if a new map has different coordinate ranges, the bounds can be updated online.

**Trading Adaptation — MarketFeatureExtractor:** The feature vector expands from 25 to approximately 60 dimensions to capture the richer information content of market data:

- Price Features (indices 0-5): open, high, low, close, volume, spread (all normalized by rolling windows)
- Trend Indicators (indices 6-15): SMA_20, SMA_50, SMA_200, EMA_12, EMA_26, DEMA_20, MACD, MACD_signal, MACD_histogram, ADX (all normalized to [0,1] or [-1,1])
- Momentum Oscillators (indices 16-25): RSI_14, Stochastic_K, Stochastic_D, CCI_14, Williams_R, ROC_10, MFI_14, Stochastic_RSI, Ultimate_Oscillator, Momentum_10
- Volatility Measures (indices 26-33): ATR_14, Bollinger_upper, Bollinger_lower, Bollinger_width, Keltner_upper, Keltner_lower, Historical_Vol_20, Parkinson_Vol
- Volume Indicators (indices 34-40): OBV, VWAP, CMF_20, Chaikin_Oscillator, Force_Index, Volume_SMA_ratio, Volume_profile_value_area
- Context Features (indices 41-50): hour_of_day (sin/cos encoded), day_of_week (sin/cos encoded), session_flag (Asia/London/NY one-hot), time_to_next_event (normalized), VIX_level (if available), DXY_change, correlation_with_SPX
- Market Microstructure (indices 51-59): bid_ask_spread, order_book_imbalance, tick_direction (uptick/downtick/zero), trade_flow_imbalance, realized_volatility_5min, return_autocorrelation, Hurst_exponent, VPIN_estimate, momentum_multiplier (from PnLMomentumTracker)

The continuous encoding pattern is preserved: instead of one-hot encoding the session (Asia=0.0, London=0.5, NY=1.0), we use a continuous variable that captures the ordinal relationship between sessions. Similarly, day_of_week uses sin/cos encoding to capture the cyclical nature (Friday is close to Monday in circular space).

The HeuristicConfig hot-swap mechanism is especially valuable for trading: market conditions change over time (regime shifts, volatility clustering), and the normalization bounds should adapt without model retraining. For example, during a volatility spike, the normalization bounds for ATR should expand to prevent saturation.

### 4.2 State Reconstructor — Tick Data to Neural Tensors (state_reconstructor.py — 59 lines)

The StateReconstructor converts raw tick-level game data into the tensor format expected by the RAP Coach model.

**Sequence Window:** The default configuration uses 32 ticks per window with 50% overlap between consecutive windows. This means each training sample consists of 32 consecutive ticks of game data, and adjacent training samples overlap by 16 ticks. The overlap provides data augmentation and ensures that events at window boundaries are captured in at least one complete window.

**Vision Bridge — TensorFactory:** The StateReconstructor includes a TensorFactory that generates synthetic visual tensors from tick data. Since the RAP Coach model expects view frames, map frames, and motion frames (for the Perception module), the TensorFactory converts tick-level features into spatial representations. The view tensor is a 3×224×224 representation of the player's perspective, the map tensor is a 3×112×112 tactical map, and the motion tensor is the frame-to-frame difference.

**Trading Adaptation — MarketStateReconstructor:** The sequence window concept translates directly: instead of 32 game ticks, the window contains the last N price bars (configurable: N=32 for daily data, N=64 for hourly, N=128 for 15-minute). The 50% overlap is preserved for training data augmentation.

The TensorFactory transforms dramatically. Instead of generating synthetic visual frames, it generates market state tensors. The two approaches:

1. **1D Temporal Tensor (Primary):** A (channels × sequence_length) tensor where each channel is a feature time series. For 60 features over 32 time steps, this produces a 60×32 tensor. This feeds a 1D-convolutional perception layer (the trading adaptation of RAPPerception).

2. **2D Market Image (Experimental):** Converting market data into a 2D "image" representation where the x-axis is time, the y-axis is feature index, and the pixel values are the normalized feature values. This enables the use of 2D convolutions (preserving the ResNet architecture) to detect spatial patterns in the feature×time space. This is experimental but has shown promise in recent literature for detecting complex multi-feature patterns.

---

## Part V: Knowledge Synthesis — Integrating V1 Bot Mathematics into the Adapted Architecture

### 5.1 Mathematical Foundations Integration Strategy

The V1 Bot's 14th document specifies over 200 mathematical equations across 19 domains. These equations must be integrated into the adapted CS2 architecture at specific points. This section specifies exactly where each mathematical domain plugs into the adapted system.

**Stochastic Calculus (GBM, Itô's Lemma, Black-Scholes):** These models inform the probabilistic framework of the ScenarioAnalyzer (adapted Game Tree). The CHANCE nodes in the expectiminimax search use GBM-calibrated price movement distributions: dS = μS dt + σS dW, where μ and σ are estimated from recent market data. Itô's Lemma transforms provide the mathematics for computing option-like payoffs at leaf nodes (for stop-loss/take-profit probability calculation). The Black-Scholes framework informs the implied volatility surface used to calibrate the CHANCE node probabilities.

**Time Series (ARIMA, GARCH, Kalman):** ARIMA provides the baseline statistical forecast that the neural network must beat — if the JEPA model can't outperform ARIMA(p,d,q), the system should fall back to the simpler model. GARCH(1,1) provides the volatility forecast used in position sizing: σ²_t = ω + α_1 ε²_{t-1} + β_1 σ²_{t-1}. The Kalman Filter is integrated into the FeatureExtractor as a preprocessing step — instead of feeding raw indicator values, the system can optionally feed Kalman-filtered values that represent the estimated "true" indicator value with measurement noise removed. The Kalman state equation x_{t|t} = x_{t|t-1} + K_t(z_t - H·x_{t|t-1}) runs on each feature independently.

**ML/DL (LSTM, Transformer, TFT):** These architectures are already represented in the JEPA model's temporal processing. The LSTM layer in the JEPA model implements the standard gated architecture. The MoE layer provides Transformer-like attention through the gate network's softmax routing. The V1 Bot's TFT specification (variable selection networks, gated residual networks) can be incorporated as an alternative temporal processing module in the JEPA architecture — swappable via configuration.

**Reinforcement Learning (MDP, Q-learning, SAC):** The RL framework is integrated through the Pedagogy head's value function V(s) and the advantage computation A_t = actual_return - V(s). The differential Sharpe ratio dS_t/dη = (B_{t-1}ΔA_t - A_{t-1}ΔB_t) / (B_{t-1} - A²_{t-1})^{3/2} provides the reward signal for RL-based training. The SAC entropy regularization J(π) = Σ E[r(s_t, a_t) + αH(π(·|s_t))] can be applied to the Strategy layer's MoE routing to maintain exploration.

**Market Microstructure (VPIN, Kyle's Lambda, Hawkes):** These are computed in the MarketFeatureExtractor as additional input features. VPIN is estimated from volume-bucketed trade flow data. Kyle's Lambda Δp = λ × signed_volume measures price impact per unit of signed volume. Hawkes process intensity λ(t) = μ + Σ α·e^{-β(t-t_i)} models the self-exciting nature of trading activity (trades beget more trades). These features feed directly into the perception layer and provide the neural network with market microstructure information that most trading systems ignore.

**Information Theory (Shannon Entropy, KL Divergence):** Shannon Entropy is used in two places: (1) the MaturityObservatory's belief entropy signal, and (2) the SignalQualityMeter's market uncertainty assessment. KL Divergence D_KL(P||Q) = Σ P(x) log(P(x)/Q(x)) is used for concept drift detection — when the current market data distribution P diverges significantly from the training data distribution Q (high KL divergence), the system reduces confidence through the drift gate. Mutual Information I(X;Y) = H(X) - H(X|Y) is used for feature selection — features with low mutual information with the target variable (future returns) are candidates for removal from the feature vector.

**Risk Management (VaR, CVaR, Kelly):** These are integrated into the Risk Check stage (Stage 7 of the V1 Bot pipeline). VaR_α defines the maximum position loss at confidence level α. CVaR_α provides the expected loss in the tail beyond VaR. The Kelly Criterion f* = (bp - q) / b determines optimal position size. All three are computed at the portfolio level before each trade is approved. The MaturityObservatory's confidence multiplier further scales the Kelly-optimal size: final_size = kelly_size × maturity_multiplier × (1 - drawdown_penalty).

### 5.2 Feature Engineering Integration — Equation-by-Equation Specification

The V1 Bot specifies 60+ technical indicators with exact formulas. These are integrated into the MarketFeatureExtractor through a carefully designed computation graph that preserves incremental computation, handles missing data gracefully, and maintains numerical stability. This section provides the complete equation set for each indicator group, specifies the exact implementation requirements, and maps each equation to its integration point in the adapted architecture.

#### 5.2.1 Trend Indicators — Moving Average Family

The moving average family forms the backbone of trend detection. Each variant captures different aspects of price momentum through distinct weighting schemes:

**Simple Moving Average (SMA):** SMA_n = (1/n) Σ_{i=0}^{n-1} P_{t-i}. Incremental update: SMA_new = SMA_old + (P_new - P_{old_dropped}) / n. This requires maintaining a circular buffer of the last n prices. For 20, 50, and 200-period SMAs, the buffer sizes are 20, 50, and 200 respectively. The crossover signals (SMA_20 crossing above/below SMA_50, SMA_50 crossing above/below SMA_200) are classic trend indicators — the "Golden Cross" (50 above 200) and "Death Cross" (50 below 200) are among the most widely followed signals in institutional trading.

**Exponential Moving Average (EMA):** EMA_t = α × P_t + (1-α) × EMA_{t-1}, where α = 2/(n+1). The EMA gives exponentially decaying weight to past observations, with the most recent price receiving weight α and all previous observations receiving geometrically decreasing weights. The half-life of an EMA is h = -ln(2)/ln(1-α) ≈ (n-1)/2 periods. For the trading system, EMA_12 and EMA_26 are used for MACD computation, while EMA_9 serves as the MACD signal line. The EMA requires only the previous EMA value and the current price for its update — O(1) computation per tick, which is critical for real-time trading.

**Double Exponential Moving Average (DEMA):** DEMA_t = 2 × EMA_t - EMA(EMA_t). This reduces the lag inherent in standard EMAs by applying the EMA twice and subtracting the double-smoothed version. The lag reduction is approximately 50% compared to a standard EMA of the same period. The DEMA is particularly useful in trending markets where early signal detection matters.

**Triple Exponential Moving Average (TEMA):** TEMA_t = 3 × EMA_t - 3 × EMA(EMA_t) + EMA(EMA(EMA_t)). Further lag reduction through triple application. The TEMA can actually lead the price action in strong trends, producing earlier crossover signals at the cost of more false signals in ranging markets.

**Hull Moving Average (HMA):** HMA_t = WMA(2 × WMA(P, n/2) - WMA(P, n), √n), where WMA is the Weighted Moving Average with linearly increasing weights. The HMA achieves the best lag reduction of any moving average variant while maintaining relatively smooth output. It is computed through three WMA stages, requiring O(n) computation per update but producing signals that are both fast and relatively noise-free.

**Kaufman Adaptive Moving Average (KAMA):** KAMA_t = KAMA_{t-1} + SC_t × (P_t - KAMA_{t-1}), where SC (Smoothing Constant) is adaptive: SC = (ER × (fast_SC - slow_SC) + slow_SC)², ER = |P_t - P_{t-n}| / Σ_{i=0}^{n-1} |P_{t-i} - P_{t-i-1}|, fast_SC = 2/(2+1), slow_SC = 2/(30+1). The Efficiency Ratio (ER) measures how efficiently price is moving — in a strong trend, ER approaches 1.0 (price distance equals path distance), and the KAMA becomes responsive. In choppy markets, ER approaches 0.0 (price goes nowhere despite large path distance), and the KAMA becomes extremely smooth. This self-adapting behavior makes KAMA particularly valuable for the trading system because it automatically adjusts to the current market regime without external regime detection. Integration point: KAMA feeds the MarketFeatureExtractor at index 11, and its ER sub-component is also exposed as a standalone feature because it provides a regime indicator (high ER = trending, low ER = ranging).

#### 5.2.2 Momentum Oscillators — Rate of Change Detection

Momentum oscillators measure the speed and direction of price changes, providing leading indicators of trend reversals:

**Relative Strength Index (RSI):** RSI_t = 100 - 100/(1 + RS_t), where RS_t = EMA(gains, n) / EMA(losses, n). The incremental computation is: avg_gain_new = (avg_gain_old × (n-1) + gain_current) / n and avg_loss_new = (avg_loss_old × (n-1) + loss_current) / n, where gain_current = max(0, P_t - P_{t-1}) and loss_current = max(0, P_{t-1} - P_t). RSI_14 is the standard configuration. For the trading system, RSI serves dual purposes: (1) as an input feature to the neural network (occupying index 16 in the MarketFeatureExtractor), and (2) as a component of the rule-based regime classifier (RSI > 70 contributes to "overbought trending" classification, RSI < 30 contributes to "oversold trending" classification). The V1 Bot also specifies Stochastic RSI: StochRSI_t = (RSI_t - min(RSI, k)) / (max(RSI, k) - min(RSI, k)), which normalizes RSI to a [0,1] range over the last k periods, providing sharper overbought/oversold signals.

**MACD (Moving Average Convergence Divergence):** MACD_line = EMA_12 - EMA_26, Signal_line = EMA_9(MACD_line), Histogram = MACD_line - Signal_line. The MACD captures the interaction between two different time horizons of momentum. The histogram's sign change (positive to negative or vice versa) signals momentum shifts. The histogram's magnitude represents the strength of the momentum — increasing histogram magnitude confirms the trend, while decreasing histogram magnitude warns of potential reversal. The MACD occupies indices 12-14 in the MarketFeatureExtractor (MACD line, signal, histogram as three separate features).

**Commodity Channel Index (CCI):** CCI_t = (TP_t - SMA_n(TP)) / (0.015 × MD_t), where TP = (High + Low + Close) / 3 (Typical Price) and MD = (1/n) Σ |TP_i - SMA_n(TP)| (Mean Deviation). The 0.015 constant normalizes CCI so that approximately 70-80% of values fall between -100 and +100. Values beyond ±200 indicate extreme conditions. For the trading system, CCI provides a normalized measure of price deviation from its statistical mean that accounts for both direction and volatility — unlike RSI which is bounded by [0,100], CCI can reach arbitrary values, making extreme readings more informative.

**Williams %R:** %R_t = (Highest_High_n - Close_t) / (Highest_High_n - Lowest_Low_n) × (-100). This oscillator measures the current price position relative to its high-low range over n periods. %R = 0 means the price is at the period's high; %R = -100 means it's at the low. %R is mathematically related to the Stochastic oscillator but inverted and unsmoothed, making it more responsive to price changes.

**Money Flow Index (MFI):** Combines price and volume: MFI_t = 100 - 100/(1 + MF_ratio), where MF_ratio = Positive_MF / Negative_MF, Money_Flow = TP × Volume, and positive/negative classification depends on whether TP increased or decreased from the previous bar. MFI is essentially a volume-weighted RSI — it provides the same overbought/oversold signals as RSI but with the additional confirmation of volume. Integration point: MFI occupies index 22 and provides a critical volume-confirmation signal that the RAPStrategy's MoE gate can use to differentiate between conviction-driven and noise-driven price movements.

#### 5.2.3 Volatility Measures — Uncertainty Quantification

Volatility indicators measure the degree of price uncertainty and are critical for position sizing, stop-loss placement, and regime detection:

**Average True Range (ATR):** TR_t = max(High_t - Low_t, |High_t - Close_{t-1}|, |Low_t - Close_{t-1}|), ATR_n = EMA(TR, n). The ATR captures the "true" range of price movement, accounting for overnight gaps through the Close_{t-1} terms. ATR_14 is the standard configuration. For the trading system, ATR serves multiple critical functions: (1) position sizing — risk_per_share = ATR × multiplier, (2) stop-loss placement — stop = entry ± ATR × factor, (3) volatility normalization — dividing returns by ATR produces volatility-adjusted returns that are more comparable across different market regimes, and (4) regime detection — ATR/price ratio (normalized volatility) is a primary input to the rule-based regime classifier.

**Bollinger Bands:** Middle = SMA_20, Upper = SMA_20 + k × σ_20, Lower = SMA_20 - k × σ_20, where σ_20 is the 20-period rolling standard deviation and k = 2 by default. Bollinger Width = (Upper - Lower) / Middle measures the relative band width. Bollinger %B = (Price - Lower) / (Upper - Lower) measures the position within the bands. For the trading system, Bollinger Bands provide multiple signals: bandwidth expansion/contraction for volatility regime changes (the "Bollinger Squeeze" preceding breakouts), %B extremes for overbought/oversold conditions, and band touches for mean-reversion entries in ranging markets. Bollinger Width feeds the MaturityObservatory's volatility signal — rapid width changes indicate regime transitions that reduce model confidence.

**Parkinson Volatility Estimator:** σ_P = √(1/(4n·ln2) × Σ (ln(H_i/L_i))²). This uses only high-low range data and is approximately 5 times more efficient than the close-to-close volatility estimator. For the trading system, Parkinson volatility provides a more accurate real-time volatility estimate that is less affected by closing price noise. It occupies index 33 in the MarketFeatureExtractor and is also used within the Risk Check stage for more accurate VaR computation.

**Garman-Klass Volatility:** σ_GK = √(1/n × Σ [0.5(ln(H_i/L_i))² - (2ln2-1)(ln(C_i/O_i))²]). This uses all four OHLC values, combining the range-based Parkinson estimator with the open-to-close return to produce the most efficient (lowest variance) estimator of daily volatility from daily data alone. The Garman-Klass estimator is used in the V1 Bot's risk management equations for more accurate VaR and position sizing calculations.

**Yang-Zhang Volatility:** σ_YZ² = σ_overnight² + σ_open² + k × σ_RS², where σ_overnight captures the overnight gap component, σ_open captures the opening range, and σ_RS is the Rogers-Satchel estimator. This is the most comprehensive volatility estimator, accounting for opening jumps, drift, and intraday dynamics. It is used for the most accurate position sizing computations in the Risk Check stage but is too computationally expensive for real-time feature computation — it is computed on an end-of-day basis and used for overnight position management.

#### 5.2.4 Volume Indicators — Flow Analysis

Volume indicators measure the relationship between price movement and trading volume, providing confirmation or divergence signals:

**On-Balance Volume (OBV):** OBV_t = OBV_{t-1} + sign(ΔP) × Volume_t, where sign(ΔP) = +1 if close > previous close, -1 if close < previous close, 0 if unchanged. OBV is a cumulative indicator — its absolute value is less important than its direction and divergence from price. When price makes new highs but OBV doesn't ("bearish divergence"), it suggests the advance is on declining volume and may reverse. This divergence detection is implemented in the MarketFeatureExtractor as a derived feature: OBV_divergence = sign(ΔPrice_20) × sign(ΔOBV_20), where a value of -1 indicates divergence.

**Volume-Weighted Average Price (VWAP):** VWAP_t = Σ(TP_i × Volume_i) / Σ(Volume_i), computed from the start of the trading session. VWAP represents the average price at which the market has traded during the session, weighted by volume — it is the benchmark price that institutional traders use to evaluate execution quality. Price above VWAP suggests bullish institutional positioning; price below VWAP suggests bearish. For the trading system, the distance from VWAP (normalized by ATR) is a key feature for intraday analysis.

**Chaikin Money Flow (CMF):** CMF_n = Σ(CLV_i × Volume_i) / Σ(Volume_i), where CLV (Close Location Value) = ((Close - Low) - (High - Close)) / (High - Low). CMF measures the accumulation/distribution pressure over n periods. CMF > 0 indicates buying pressure (closes tend to be near highs); CMF < 0 indicates selling pressure (closes tend to be near lows). This provides a volume-confirmed directional signal that feeds the knowledge retrieval system's context formation.

#### 5.2.5 Adaptive Feature Selection via Mutual Information

The V1 Bot's information theory foundations specify Mutual Information I(X;Y) = H(X) - H(X|Y) for feature selection. The integration works as follows:

The system maintains a feature importance tracker that periodically (weekly during monthly retraining cycles) computes the MI between each input feature and the target variable (future returns at multiple horizons: 1-bar, 5-bar, 20-bar). Features with MI below a threshold (dynamically set as the 15th percentile of all MI scores) are flagged as "low-information" and their contribution to the feature vector is soft-gated — rather than removing them entirely (which would require model retraining), their values are multiplied by a reduction factor (0.5) that gracefully reduces their influence. New candidate features (such as novel technical indicators, alternative data sources, or interaction terms between existing features) are evaluated by computing their MI and comparing against the distribution of existing feature MI scores. Only features that exceed the median MI of existing features are added to the feature vector. This adaptive selection ensures that the feature set evolves with the market without requiring disruptive architectural changes.

The MI computation itself uses a k-nearest-neighbor estimator (Kraskov-Stögbauer-Grassberger): I(X;Y) = ψ(k) - 〈ψ(n_x + 1) + ψ(n_y + 1)〉 + ψ(N), where ψ is the digamma function, k is the number of neighbors, n_x and n_y are the number of points within the k-th neighbor distance in the x and y marginal spaces, and N is the total number of samples. This estimator is preferred over histogram-based MI because it works well with continuous variables and doesn't require binning decisions.

### 5.3 Risk Management Mathematics — Complete Integration Specification

The V1 Bot's risk management framework specifies 15+ equations that must be integrated into a cohesive risk control system. This section provides the complete integration mapping.

#### 5.3.1 Value at Risk (VaR) and Conditional VaR (CVaR)

**Parametric VaR:** VaR_α = μ + σ × Φ^{-1}(α), where μ is the expected return, σ is the portfolio volatility (computed via Garman-Klass or Yang-Zhang for accuracy), and Φ^{-1} is the inverse standard normal CDF. For α = 0.95, Φ^{-1}(0.95) = 1.645. This provides the "worst-case loss at 95% confidence" for position sizing.

**Historical VaR:** Sort historical returns in ascending order, take the αth percentile. More robust than parametric VaR because it doesn't assume normality — financial returns have fat tails that parametric VaR underestimates.

**CVaR (Expected Shortfall):** CVaR_α = E[L | L > VaR_α] = (1/(1-α)) ∫_α^1 VaR_u du. CVaR answers: "If we do experience a loss beyond VaR, what's the expected magnitude?" This is a more conservative risk measure that captures tail risk. Integration point: CVaR is computed at the portfolio level before each trade approval in the Risk Check stage for maximum position loss estimation.

**Cornish-Fisher VaR (for fat tails):** VaR_CF = μ + σ × (z + (z²-1)S/6 + (z³-3z)K/24 - (2z³-5z)S²/36), where z is the normal quantile, S is skewness, and K is excess kurtosis. This adjusts VaR for non-normal return distributions by incorporating skewness and kurtosis. For gold trading, where returns exhibit negative skewness (large sudden drops) and positive kurtosis (fat tails), the Cornish-Fisher correction can increase VaR estimates by 20-40% compared to the parametric assumption — critical for avoiding under-hedging.

#### 5.3.2 Position Sizing — Kelly Criterion and Extensions

**Standard Kelly:** f*= (bp - q) / b, where b is the benefit-to-cost ratio (average win / average loss), p is the probability of winning, and q = 1-p. For example, with a 55% win rate and 1.5:1 reward-to-risk ratio: f* = (1.5 × 0.55 - 0.45) / 1.5 = 0.25, suggesting risking 25% of capital per trade.

**Fractional Kelly:** f_practical = f* × fraction, where fraction is typically 0.25-0.50 (quarter-Kelly to half-Kelly). Full Kelly is mathematically optimal for maximizing long-term growth rate but produces extreme volatility that is psychologically and practically unsustainable. The trading system defaults to 0.33 × Kelly (one-third Kelly), which sacrifices approximately 11% of the theoretical growth rate while reducing variance by 67%.

**Confidence-Adjusted Kelly:** f_adjusted = f* × maturity_multiplier × (1 - drawdown_penalty), where maturity_multiplier comes from the MaturityObservatory (0.0 for DOUBT state, up to 1.0 for MATURE) and drawdown_penalty = min(1.0, current_drawdown / max_allowed_drawdown). This ensures that position sizes automatically decrease when the model is uncertain or when the portfolio is in drawdown — a critical safety mechanism not present in standard Kelly implementations.

**Multi-Asset Kelly (Portfolio Level):** For a portfolio of n assets, the optimal allocation vector is f* = Σ^{-1} × μ / γ, where Σ is the covariance matrix of returns, μ is the vector of expected excess returns, and γ is the risk aversion parameter. This generalizes single-asset Kelly to portfolio allocation and is used when the system trades multiple correlated instruments (though the primary focus is XAUUSD, the architecture supports expansion).

#### 5.3.3 Drawdown Management

**Maximum Drawdown:** MDD = max_{t ∈ [0,T]} (HWM_t - P_t) / HWM_t, where HWM_t = max_{s ∈ [0,t]} P(s) (High-Water Mark). The trading system tracks drawdown in real-time and applies escalating risk reduction:

- Drawdown < 2%: Normal operation, full position sizing
- Drawdown 2-5%: Reduce position sizes by 25%, tighten stop-losses by 0.5 ATR
- Drawdown 5-10%: Reduce position sizes by 50%, activate LEARNING mode regardless of maturity state
- Drawdown > 10%: Halt trading, activate CALIBRATING mode, require manual review before resuming

The drawdown thresholds are configured per-instrument (XAUUSD has tighter thresholds than lower-volatility instruments) and per-strategy (momentum strategies tolerate larger drawdowns than mean-reversion strategies because their return distributions have longer tails).

### 5.4 Regime Detection Architecture — Detailed Integration

The V1 Bot specifies three parallel regime classifiers that must integrate with the CS2 Analyzer's MoE gating mechanism. This section provides the complete integration specification.

#### 5.4.1 Rule-Based Classifier

The rule-based classifier uses a decision tree with the following conditions:

```
if ADX > 25 and |price - SMA_200| > 2 * ATR_20:
    regime = TRENDING
    sub_regime = STRONG_TREND
elif ADX > 25:
    regime = TRENDING
    sub_regime = MILD_TREND
elif ATR_14 / price > 95th_percentile(historical):
    regime = VOLATILE
    sub_regime = CRISIS if VIX > 30 else EXPANSION
elif ADX < 20 and Bollinger_Width < 25th_percentile(historical):
    regime = RANGING
    sub_regime = TIGHT_RANGE
elif ADX < 20:
    regime = RANGING
    sub_regime = WIDE_RANGE
else:
    regime = TRANSITIONAL
    sub_regime = UNDEFINED
```

This classifier runs on every new bar and produces an immediate regime label — it is the "fast path" that provides real-time regime awareness without computational delay. Its output is fed to the MoE gate network as a one-hot bias vector (matching the role-biased gating pattern from the CS2 Analyzer's JEPA model).

#### 5.4.2 Hidden Markov Model Classifier

The HMM classifier treats market regimes as hidden states and price observations (returns, volatility, volume changes) as emissions. The mathematical specification follows the Baum-Welch algorithm for parameter estimation:

**E-step (Forward-Backward):**

- Forward variable: α_t(i) = P(o_1...o_t, q_t = s_i | λ) — computed recursively as α_t(j) = [Σ_i α_{t-1}(i) × a_{ij}] × b_j(o_t)
- Backward variable: β_t(i) = P(o_{t+1}...o_T | q_t = s_i, λ) — computed recursively as β_t(i) = Σ_j a_{ij} × b_j(o_{t+1}) × β_{t+1}(j)
- Posterior: γ_t(i) = α_t(i) × β_t(i) / P(O | λ) — the probability of being in state i at time t

**M-step:**

- Transition update: â_ij = Σ_t ξ_t(i,j) / Σ_t γ_t(i), where ξ_t(i,j) = α_t(i) × a_ij × b_j(o_{t+1}) × β_{t+1}(j) / P(O | λ)
- Emission update: depends on the emission distribution family (Gaussian for continuous, multinomial for discrete)

The HMM is configured with 4 hidden states mapping to the four market regimes (trending, ranging, volatile, crisis). The emission distribution is multivariate Gaussian with 3 features: log-returns, realized volatility (5-bar), and log-volume-ratio. The HMM is retrained weekly on a rolling 6-month window of data.

**Viterbi Decoding:** The most-likely-state-sequence is computed using the Viterbi algorithm: δ_t(j) = max_i [δ_{t-1}(i) × a_{ij}] × b_j(o_t). The Viterbi path provides a smoothed regime label that is less noisy than the rule-based classifier — it considers the global sequence rather than just the current observation.

Integration with MoE: The HMM posterior probabilities γ_t(i) are fed directly to the MoE gate network as soft labels rather than hard regime classifications. This means the gate output g = softmax(W_g × h + W_hmm × γ_t), where W_hmm is a learned weight matrix that blends the HMM's regime probabilities with the neural network's latent representation. This soft blending prevents the hard switching artifacts that occur when regime labels abruptly change.

#### 5.4.3 Ensemble Regime Classification

The three classifiers (rule-based, HMM, k-means) are combined through weighted voting:

final_regime = argmax_r Σ_c w_c × P_c(regime = r), where w_c are classifier weights (initially equal at 1/3 each) and P_c(regime = r) is each classifier's probability for regime r.

The weights w_c are updated monthly based on each classifier's accuracy over the past month: classifiers that correctly predicted the regime (as determined by future price behavior) receive increased weight, while those that were incorrect receive decreased weight. This adaptive weighting ensures that the most accurate classifier for the current market conditions receives the most influence.

**Regime Transition Hysteresis:** To prevent whipsawing between regimes at transition boundaries, the system applies hysteresis: a transition from regime A to regime B requires the ensemble probability P(B) to exceed P(A) by at least a margin of 0.15 for at least 3 consecutive bars. This "sticky" behavior prevents the MoE from rapidly switching between experts, which can produce erratic trading signals.

---

## Part VI: Training and Deployment Lifecycle

### 6.1 Walk-Forward Training Methodology

The CS2 Analyzer uses chronological 70/15/15 splits to prevent temporal leakage. For trading, this is extended to a full walk-forward validation framework that accounts for the non-stationarity of financial markets and the critical requirement that future information must never contaminate past-based decisions.

#### 6.1.1 Walk-Forward Window Configuration

The walk-forward framework operates with configurable window sizes:

1. **Initial Training Window:** Train on the first N months of data (default: 12 months for daily data, 6 months for hourly, 3 months for 15-minute)
2. **Validation Window:** Validate on the next M months (default: 3 months / 1.5 months / 3 weeks, respectively)
3. **Test Window:** Test on the subsequent K months (default: 3 months / 1.5 months / 3 weeks)
4. **Walk Forward:** Slide the window forward by K months and repeat
5. **Purge Gap:** A gap of G bars (default: 5 trading days) between training and validation sets to prevent label leakage from lookahead in target computation

This ensures that the model is always evaluated on truly out-of-sample data. The walk-forward results are aggregated across all windows to produce robust performance estimates that account for the non-stationarity of financial markets. The minimum number of walk-forward folds is 5 — fewer than this provides insufficient statistical confidence in the performance estimates.

**Performance Aggregation:** For each walk-forward fold, the system records: Sharpe ratio, maximum drawdown, win rate, profit factor, and average trade duration. These metrics are aggregated across folds using both mean and worst-case statistics: the system reports both the average Sharpe ratio across folds (expected performance) and the minimum Sharpe ratio across any single fold (worst-case performance). The system only promotes from CALIBRATING to LEARNING if the worst-case Sharpe exceeds 0.5, ensuring that even the weakest fold was profitable.

#### 6.1.2 JEPA Pre-Training Stages

The JEPA pre-training follows a three-phase curriculum that mirrors the CS2 Analyzer's training practices but adapts them for market data:

**Phase 1 — Self-Supervised Representation Learning (60% of pre-training budget):** The JEPA model is trained using the InfoNCE contrastive loss with market data windowed into context-target pairs. The context window is the current state (last N bars), and the target window is the future state (next M bars). The model learns to predict the latent representation of the future from the current state. Context window sizes: N ∈ {16, 32, 64} (multi-scale pre-training, cycling). Target window sizes: M ∈ {1, 5, 20} (multi-horizon prediction). The temperature parameter τ for InfoNCE starts at 0.1 and is linearly annealed to 0.05 over the pre-training phase to sharpen the contrastive signal. The momentum coefficient for the target encoder EMA update starts at 0.99 and is cosine-annealed to 0.999, providing increasing stability as training progresses. Batch size: 256 windows, computed across the full historical dataset (not just the training window of a single walk-forward fold). This broad pre-training ensures that the learned representations capture the full spectrum of market dynamics.

**Phase 2 — Supervised Signal Prediction (30% of pre-training budget):** The pre-trained JEPA encoder is frozen, and the coaching head (MoE + LSTM temporal layer) is trained to predict trading signals. The target labels are computed from future price data using a triple-barrier method: for each bar, the target is +1 (BUY) if the price first hits the take-profit barrier (entry + k × ATR), -1 (SELL) if it first hits the stop-loss barrier (entry - k × ATR), or 0 (HOLD) if neither barrier is hit within T bars. The triple-barrier method produces more realistic labels than simple return-sign classification because it accounts for path dependency and risk/reward structure. The loss function is a weighted cross-entropy that accounts for class imbalance: L = -Σ w_c × y_c × log(ŷ_c), where w_c is inversely proportional to class frequency.

**Phase 3 — Regime-Specific Head Training (10% of pre-training budget):** The MoE gate network and regime-specific expert heads are fine-tuned with regime-conditioned data. The training data is split by regime (using the ensemble regime classifier's labels), and each expert is trained primarily on data from its assigned regime while maintaining exposure to other regimes (80% target regime, 20% other regimes). This prevents catastrophic forgetting while encouraging specialization. The gate network is trained end-to-end with a load-balancing auxiliary loss: L_balance = N × Σ_i f_i × P_i, where f_i is the fraction of samples routed to expert i and P_i is the average gate probability for expert i. This loss encourages uniform expert utilization, preventing the degenerate case where one expert dominates.

#### 6.1.3 Data Augmentation Strategies

Financial data is limited and non-stationary, making data augmentation critical for preventing overfitting. The adapted system implements five augmentation strategies:

1. **Temporal Jittering:** Randomly shift the window start position by ±k bars (k ∈ {1, 2, 3}), producing slightly offset views of the same market period. This teaches the model that the exact window alignment is not critical.

2. **Feature Noise Injection:** Add Gaussian noise with σ = 0.01 × feature_std to each feature independently. This provides regularization and simulates the effect of slightly different data sources or minor feed discrepancies.

3. **Regime Oversampling:** Market data is heavily imbalanced — trending and ranging regimes are common, while crisis regimes are rare but critical. The system oversamples crisis episodes by 3× to ensure the Crisis Expert receives adequate training data.

4. **Synthetic Regime Transitions:** Generate synthetic data at regime boundaries by interpolating between the end of one regime and the start of another. This provides additional training data for the regime transition hysteresis mechanism.

5. **Magnitude Scaling:** Randomly scale the price returns by a factor uniformly drawn from [0.8, 1.2]. This teaches the model that the direction of movement is more important than its exact magnitude, improving generalization across different volatility environments.

#### 6.1.4 Hyperparameter Search Protocol

The system uses a Bayesian optimization framework (Tree-structured Parzen Estimators / TPE) for hyperparameter search, with the walk-forward Sharpe ratio as the objective function. The hyperparameter search space includes:

- JEPA latent dimension: {64, 128, 256}
- Number of MoE experts: {3, 4, 5}
- LSTM hidden dimension: {64, 128, 256}
- LTC time constant range: [(0.1, 10.0), (0.5, 50.0), (1.0, 100.0)]
- Hopfield memory slots: {256, 512, 1024}
- Learning rate: log-uniform in [1e-5, 1e-3]
- Batch size: {64, 128, 256, 512}
- Context window size N: {16, 32, 64, 128}
- InfoNCE temperature τ: [0.03, 0.2]
- Kelly fraction: [0.15, 0.50]
- Confidence gate threshold: [0.60, 0.85]

The search budget is 100 trials, with early stopping for trials that show negative worst-case Sharpe after the first walk-forward fold. The best configuration is selected based on the median Sharpe ratio across all walk-forward folds, with a tie-breaker favoring lower maximum drawdown.

### 6.2 Maturity-Gated Deployment

The 3-tier maturity system (CALIBRATING/LEARNING/MATURE) from coach_manager.py determines the deployment level. Each tier has precisely defined entry criteria, operating constraints, and transition conditions.

**CALIBRATING Phase (first 200 episodes):**

- Paper trading only — all signals are generated but no real capital is deployed
- All 5 maturity signals accumulated (prediction uncertainty, regime confidence, feature stability, PnL accuracy, strategy consistency)
- Conviction index typically < 0.4
- Position sizing: 0% of real capital (paper only)
- Minimum duration: 200 trading episodes regardless of conviction index
- Exit condition: conviction index > 0.4 for 5 consecutive evaluation periods AND minimum 200 episodes completed AND worst-case walk-forward Sharpe > 0.5

**LEARNING Phase (200-1000 episodes):**

- Reduced position sizing — signals trade with 20-50% of target capital
- Position size within LEARNING = 20% + (conviction_index - 0.4) × 50% (linearly scales from 20% at 0.4 conviction to 50% at conviction approaching 0.8)
- Continuous maturity monitoring with automated fallback to CALIBRATING if conviction drops below 0.3
- Weekly walk-forward revalidation to detect model degradation
- Maximum single-trade loss: 1% of account (tighter than MATURE)
- Daily maximum loss: 2% of account (triggers session halt)
- Exit condition to MATURE: conviction index > 0.8 for 10 consecutive evaluation periods AND minimum 1000 episodes completed AND maximum drawdown during LEARNING phase < 5%
- Fallback condition to CALIBRATING: conviction < 0.3 for 3 consecutive periods OR maximum drawdown > 8% OR 5 consecutive losing weeks

**MATURE Phase (1000+ episodes, conviction > 0.8):**

- Full position sizing — signals trade at target capital levels
- Position size = Kelly_adjusted × maturity_multiplier (where maturity_multiplier = 1.0 at conviction > 0.8)
- Daily maturity monitoring with TensorBoard dashboards
- Maximum single-trade loss: 2% of account
- Daily maximum loss: 4% of account
- Automated circuit breaker: if 3 consecutive days show declining conviction, revert to LEARNING
- Additional circuit breaker: if any single day's loss exceeds 3%, immediately halt for manual review
- Regime-change circuit breaker: if the ensemble regime classifier detects a regime not seen during training, temporarily reduce position sizing by 50% until the new regime has been observed for at least 20 episodes

### 6.3 Continuous Learning Pipeline

The adapted system implements continuous learning mirroring the CS2 Analyzer's retraining cycles. Each cycle has explicit triggers, procedures, and validation steps to prevent catastrophic forgetting and model degradation.

#### 6.3.1 Daily Feature Maintenance Cycle

**Trigger:** Automatic, runs at end of each trading session.

**Procedure:**

1. Update all rolling statistics (means, standard deviations, normalization bounds) used by the MarketFeatureExtractor
2. Compute feature drift metrics: for each feature, calculate the KL divergence between today's feature distribution and the 30-day historical distribution
3. If any feature's KL divergence exceeds 0.5 nats, flag it as "drifting" and prepend a warning to the next day's trading signals
4. Update the TradeHistoryBank with today's completed trades, computing embeddings and updating the FAISS index
5. Recompute the MaturityObservatory's 5 signals and update the conviction index
6. Generate a daily health report: maturity status, drift warnings, feature statistics, and PnL summary

#### 6.3.2 Weekly Experience Integration Cycle

**Trigger:** Every Sunday before market open.

**Procedure:**

1. Process the past week's trades through the TradeHistoryBank, creating structured ExperienceContext entries with full market metadata
2. Re-embed all newly added experiences using Sentence-BERT, updating the semantic retrieval index
3. Evaluate the feedback loop: for each trade where COPER advice was provided, compare the advice quality against the trade outcome
4. Update COPER advice weights: reinforce successful advice templates, de-weight unsuccessful ones
5. Run the TradingWeaknessAnalyzer (adapted BlindSpotDetector) on the week's trades to identify recurring mistakes
6. Generate a weekly review report: blind spots, advice quality metrics, regime distribution, and portfolio analytics

#### 6.3.3 Monthly Model Retraining Cycle

**Trigger:** First weekend of each month, or automatically if the MaturityObservatory's conviction index drops below the tier threshold for 5 consecutive days.

**Procedure:**

1. Perform a full walk-forward retraining with the latest data, including all data accumulated since the last retraining
2. The retraining uses the current best hyperparameters but includes a small hyperparameter perturbation search (20 trials) to adapt to changing market conditions
3. Compare the new model's walk-forward performance against the current deployed model's historical performance
4. If the new model's worst-case Sharpe exceeds the current model's by at least 0.1, deploy the new model (gradual rollout: 50% new model, 50% old model for the first week)
5. If the new model performs worse, retain the current model and flag for architectural review
6. Update the StrategyKnowledgeBase with any new patterns or insights discovered during retraining
7. Archive the old model checkpoint for rollback capability

#### 6.3.4 Quarterly Architecture Review

**Trigger:** Manual review scheduled quarterly.

**Procedure:**

1. Evaluate whether the feature set remains optimal: run full Mutual Information analysis across all features and compare against the previous quarter
2. Assess regime classifier accuracy: compare each classifier's predictions against actual regime labels (determined by future price behavior) and update the ensemble weights
3. Review the MoE expert utilization: if any expert is consistently unused (< 5% gate weight across all episodes), consider removing it or reassigning its regime
4. Evaluate whether the model architecture (JEPA latent dim, LSTM hidden dim, Hopfield slots) remains appropriate for the current data distribution
5. Review and update drawdown thresholds, confidence gates, and position sizing parameters based on the quarter's performance
6. Generate a quarterly architecture health report with recommendations for the next quarter

### 6.4 Backtesting Infrastructure

The backtesting infrastructure mirrors the live trading pipeline exactly to prevent training-serving skew. The key principle is: the backtester uses the same code paths as the live system — the same MarketFeatureExtractor, the same model inference pipeline, the same risk management logic. The only difference is that the data source is historical rather than live.

**Backtesting Modes:**

1. **Full Backtest:** Run the complete pipeline (feature extraction → model inference → signal generation → risk check → position sizing → simulated execution) across the full historical dataset. This produces the most comprehensive performance assessment but is computationally expensive (hours to days).

2. **Signal-Only Backtest:** Run only the feature extraction and model inference stages, outputting raw signals without position sizing or execution simulation. This is faster (minutes to hours) and useful for rapid model iteration.

3. **Walk-Forward Backtest:** The standard evaluation mode — performs a full backtest within each walk-forward fold, producing per-fold and aggregated metrics.

**Execution Simulation:** The backtester simulates realistic execution conditions including: (1) spread — the bid-ask spread is computed from historical tick data or estimated from daily range, (2) slippage — entry and exit prices include a configurable slippage model (default: 0.5 × spread for market orders, 0 for limit orders), (3) fill probability — limit orders have a fill probability model based on historical fill rates at various limit-to-market distances, (4) partial fills — large orders may be only partially filled based on historical volume profiles, (5) latency — a configurable delay between signal generation and simulated execution (default: 100ms for live, 0 for backtest).

**Anti-Overfitting Safeguards:** (1) Minimum 5 walk-forward folds, (2) performance must be positive in at least 80% of folds, (3) Sharpe ratio must exceed the "null model" (random entry/exit with the same position sizing) by at least 1.0, (4) the system tracks the number of times each strategy/hyperparameter combination has been tested to detect multiple-testing bias, applying a Bonferroni correction to the significance threshold: α_adjusted = α / n_tests.

---

## Part VII: Implementation Roadmap

### Phase 1: Foundation (Weeks 1-3)

**Objective:** Establish the data pipeline and core feature engineering infrastructure.

**Deliverables:**

- **MarketFeatureExtractor** (adapted from `vectorizer.py`): Complete implementation of the 60-dimensional feature vector with all indicator computations, incremental update capability, and normalization bounds management. This is the single most critical deliverable because every downstream component depends on it.
  - File: `backend/processing/market_vectorizer.py`
  - Tests: Unit tests for each indicator computation, integration test for full feature vector generation
  - Acceptance: All indicator values match reference implementations (TA-Lib) to within 1e-6 tolerance

- **MarketStateReconstructor** (adapted from `state_reconstructor.py`): Sliding window generation with configurable window sizes, overlap, and multi-timeframe support.
  - File: `backend/processing/market_state_reconstructor.py`
  - Tests: Window generation tests, boundary condition tests, multi-timeframe alignment tests

- **HopfieldLayer and SuperpositionLayer** (direct port from `hflayers.py` and `superposition.py`): These layers are ported without modification since they are domain-agnostic.
  - Files: `backend/nn/layers/hflayers.py`, `backend/nn/layers/superposition.py`
  - Tests: Forward pass shape tests, gradient flow tests

- **Market Data Ingestion Pipeline**: Replace the CS2 demo parser with market data ingestion. Support for: (1) historical CSV/Parquet data loading, (2) live data streaming via WebSocket (exchange API), (3) data normalization and verification (detect missing bars, verify OHLCV consistency: H >= max(O,C) and L <= min(O,C)).
  - File: `backend/processing/market_data_pipeline.py`
  - Tests: Data integrity tests, missing data handling tests, live vs. historical symmetry tests

**Phase 1 Exit Criteria:** MarketFeatureExtractor produces correct 60-dim vectors from raw OHLCV data; MarketStateReconstructor generates correct sliding windows; data pipeline can ingest both historical and simulated live data.

### Phase 2: Core Models (Weeks 4-7)

**Objective:** Adapt the neural network architecture for market data processing.

**Deliverables:**

- **MarketPerception** (adapted from `perception.py`): Replace 2D CNN with 1D temporal convolutions. Three streams: Price Stream (ResNet-style 1D convolutions on OHLCV), Indicator Stream (lighter 1D convolutions on indicators), Change Stream (1D convolutions on first differences). Output: 128-dimensional perception vector.
  - File: `backend/nn/rap_coach/market_perception.py`
  - Tests: Shape tests (verify 128-dim output), gradient flow tests, multi-stream consistency tests

- **MarketMemory** (adapted from `memory.py`): LTC + Hopfield with minimal changes. LTC time constants are initialized with market-appropriate ranges (0.1-100.0 covering sub-minute to multi-day dynamics). Hopfield memory slots initialized to 512 (configurable). AutoNCP wiring preserved.
  - File: `backend/nn/rap_coach/market_memory.py`
  - Tests: LTC dynamics tests (verify continuous-time behavior), Hopfield retrieval tests, belief head output tests

- **MarketStrategy** (adapted from `strategy.py`): 4 MoE experts (Trend, Range, Volatile, Crisis). SuperpositionLayer context input: regime posterior probabilities from HMM. Gate network augmented with regime bias injection.
  - File: `backend/nn/rap_coach/market_strategy.py`
  - Tests: Expert specialization tests (verify gate weights concentrate appropriately), regime-conditioned output tests

- **MarketPedagogy** (adapted from `pedagogy.py`): Value function V(s) estimates expected risk-adjusted return. Strategy adapter replaces skill adapter. CausalAttributor with 5 trading concepts (Trend, Momentum, Volatility, Volume, Correlation).
  - File: `backend/nn/rap_coach/market_pedagogy.py`
  - Tests: Value estimation range tests, attribution score normalization tests

- **MarketRAPCoach** (adapted from `model.py`): Integration of all sub-modules. Forward pass: MarketPerception → MarketMemory → MarketStrategy → MarketPedagogy. Output dictionary: signal_probs, belief_state, value_estimate, gate_weights, position_sizing, attribution.
  - File: `backend/nn/rap_coach/market_model.py`
  - Tests: End-to-end forward pass tests, output shape tests, gradient accumulation tests

**Phase 2 Exit Criteria:** MarketRAPCoach accepts MarketFeatureExtractor output and produces correctly-shaped signal predictions; all sub-modules have passing unit tests; full forward-backward pass completes without errors.

### Phase 3: Analysis Engine (Weeks 8-10)

**Objective:** Adapt all analysis modules for market data.

**Deliverables:**

- **ScenarioAnalyzer** (from `game_tree.py`): Expectiminimax search with MAX (position), MIN (adverse market), CHANCE (probabilistic events) nodes. CounterpartyBehaviorModel with market-microstructure priors. PositionValuePredictor at leaf nodes incorporating VaR/CVaR.
  - File: `backend/analysis/scenario_analyzer.py`

- **TradingWeaknessAnalyzer** (from `blind_spots.py`): Situation classification by market conditions, deviation scoring against model-optimal actions, priority computation, actionable trade journal generation.
  - File: `backend/analysis/trading_weakness.py`

- **PnLMomentumTracker** (from `momentum.py`): Win/loss streak tracking, exponential decay with hours_since_last_trade, tilt detection at 0.85, overconfidence warning at 1.2, session boundary reset, drawdown-based momentum adjustment.
  - File: `backend/analysis/pnl_momentum.py`

- **MarketManipulationDetector** (from `deception_index.py`): Spoofing detection (0.25), fake breakout detection (0.40), volume deception detection (0.35). Composite manipulation index with trading guardrails.
  - File: `backend/analysis/manipulation_detector.py`

- **SignalQualityMeter** (from `entropy_analysis.py`): Shannon entropy of return distributions for market clarity assessment. Event impact analysis using pre/post entropy comparison. Per-event-type effectiveness ratings.
  - File: `backend/analysis/signal_quality.py`

- **TradeSuccessPredictor** (from `win_probability.py`): 12-feature neural network for P(trade reaches TP before SL). Heuristic overrides for extreme conditions. Natural-language explanation generation.
  - File: `backend/analysis/trade_success.py`

**Phase 3 Exit Criteria:** All analysis modules produce correct outputs on synthetic market data; PnLMomentumTracker correctly detects simulated tilt/hot streak conditions; ScenarioAnalyzer evaluates at least 500 scenarios within 2 seconds.

### Phase 4: Knowledge Integration (Weeks 11-13)

**Objective:** Adapt the knowledge and experience systems for trading.

**Deliverables:**

- **TradeHistoryBank** (from `experience_bank.py`): COPER framework with dual retrieval (semantic + hash), trade context hashing, pro/institutional pattern filtering, advice synthesis, outcome-based feedback loop.
  - File: `backend/knowledge/trade_history_bank.py`
  - Dependency: Sentence-BERT model (all-MiniLM-L6-v2), FAISS index

- **StrategyKnowledgeBase** (from `rag_knowledge.py`): Semantic search over trading knowledge entries populated from V1 Bot mathematical foundations. 5 categories: Stop-Loss Strategy, Entry Timing, Position Sizing, Portfolio Rotation, Money Management. Usage tracking for analytics.
  - File: `backend/knowledge/strategy_knowledge.py`
  - Data: V1 Bot equation entries converted to structured knowledge format

- **V1 Bot Mathematical Foundations Import:** Convert all 14 V1 Bot documents into structured knowledge entries. Each equation becomes a searchable entry with: formula, description, application context, integration point, and reference citation.
  - Script: `scripts/import_v1_bot_knowledge.py`
  - Output: JSON knowledge file with 200+ entries

- **HybridSignalEngine** (from `hybrid_engine.py`): Z-score deviation analysis against regime baselines, ML model integration, knowledge retrieval context construction, confidence computation, insight prioritization.
  - File: `backend/coaching/hybrid_signal_engine.py`

**Phase 4 Exit Criteria:** TradeHistoryBank successfully stores and retrieves trade experiences with correct semantic matching; StrategyKnowledgeBase returns relevant entries for market-related queries; HybridSignalEngine produces prioritized insights with confidence scores.

### Phase 5: Orchestration (Weeks 14-16)

**Objective:** Integrate all components into the unified trading pipeline.

**Deliverables:**

- **TradingAdvisorService** (from `coaching_service.py`): 4-mode pipeline (COPER → Hybrid → Knowledge → Conservative) with cascading fallback. Phase 6 advanced analysis coordination. Temporal baselines for differential analysis.
  - File: `backend/services/trading_advisor.py`

- **MarketAnalysisOrchestrator** (from `analysis_orchestrator.py`): Module coordination sequence (PnL Momentum → Manipulation → Signal Quality → Scenario → Weakness → Multi-Timeframe). Structured analysis report generation.
  - File: `backend/services/market_analysis_orchestrator.py`

- **TradingMaturityObservatory** (from `maturity_observatory.py`): 5 trading-adapted maturity signals, conviction index computation, maturity state management (DOUBT → CRISIS → LEARNING → CONVICTION → MATURE), TensorBoard logging.
  - File: `backend/nn/rap_coach/trading_maturity.py`

- **TradingModelManager** (from `coach_manager.py`): CALIBRATING/LEARNING/MATURE tier management, walk-forward training orchestration, JEPA pre-training curriculum, 10/10 minimum data rule (adapted to minimum 200 episodes), feature specification management.
  - File: `backend/services/trading_model_manager.py`

- **Regime Detection Ensemble:** Rule-based + HMM + k-means parallel classifiers with weighted voting and transition hysteresis.
  - File: `backend/analysis/regime_detector.py`

**Phase 5 Exit Criteria:** TradingAdvisorService produces complete trading recommendations through all 4 modes; TradingMaturityObservatory correctly transitions between maturity states; TradingModelManager successfully orchestrates a full walk-forward training cycle.

### Phase 6: Integration and Testing (Weeks 17-20)

**Objective:** End-to-end validation and deployment preparation.

**Deliverables:**

- **End-to-End Integration Tests:** Complete pipeline tests from raw market data → feature extraction → model inference → signal generation → risk check → position sizing → simulated execution. Tests cover all 4 market regimes and all 3 maturity tiers.

- **Walk-Forward Backtesting Campaign:** Minimum 5 walk-forward folds across at least 3 years of historical XAUUSD data. Required performance: worst-case Sharpe > 0.5, average Sharpe > 1.0, maximum drawdown < 15%, win rate > 50%.

- **Paper Trading Deployment:** Deploy the system in CALIBRATING mode with live market data feed. Run for minimum 200 episodes (approximately 1-2 months depending on trading frequency). Monitor all 5 maturity signals and conviction index progression.

- **Performance Benchmarking:** Compare the adapted system's performance against three baselines: (1) Buy-and-hold XAUUSD, (2) V1 Bot baseline metrics (from specification), (3) Simple moving average crossover (SMA_20/SMA_50) as a technical analysis baseline.

- **Stress Testing:** Run the system against historical periods of extreme market conditions: (1) 2008 financial crisis gold rally, (2) 2013 gold crash (-28% in 6 months), (3) 2020 COVID crash and recovery, (4) 2022-2023 rate hike cycle. Verify that circuit breakers activate appropriately, position sizing reduces during drawdowns, and the system survives without catastrophic loss.

- **Documentation:** Complete API documentation for all adapted modules, deployment guide, monitoring runbook, and incident response playbook.

---

## Appendix A: Complete Module Inventory

| Module | Lines | CS2 Function | Trading Function |
|--------|-------|-------------|-----------------|
| moneymaker.py | 282 | CLI orchestrator | TradingCLI |
| hflayers.py | 97 | Hopfield memory | PatternBank |
| schema.py | 262 | DB lifecycle | MarketDB lifecycle |
| jepa_model.py | 846 | JEPA coaching | Market prediction |
| maturity_observatory.py | 325 | Model maturity | Trading confidence |
| training_orchestrator.py | 324 | Training loop | Walk-forward training |
| rap_coach/model.py | 100 | RAP integration | Trading signal pipeline |
| rap_coach/perception.py | 73 | Visual extraction | Market feature encoding |
| rap_coach/memory.py | 69 | LTC + Hopfield | Market memory |
| rap_coach/strategy.py | 69 | MoE decision | Regime-specific signals |
| rap_coach/pedagogy.py | 98 | Value + attribution | Portfolio value + explanation |
| rap_coach/communication.py | 61 | Skill-based output | Signal explanation |
| rap_coach/chronovisor_scanner.py | 370 | Multi-scale detection | Multi-timeframe signals |
| rap_coach/skill_model.py | 108 | 5-axis skill | 5-concept analysis |
| layers/superposition.py | 99 | Context gating | Regime gating |
| game_tree.py | 446 | Expectiminimax | Scenario analysis |
| blind_spots.py | 208 | Weakness detection | Trading weakness |
| momentum.py | 197 | Streak tracking | PnL momentum |
| deception_index.py | 218 | Tactical deception | Manipulation detection |
| entropy_analysis.py | 146 | Entropy analysis | Signal quality |
| win_probability.py | 284 | Win prediction | Trade success prediction |
| experience_bank.py | 733 | COPER framework | Trade history bank |
| rag_knowledge.py | 472 | Semantic search | Strategy knowledge base |
| coaching_service.py | 519 | 4-mode coaching | 4-mode trading signals |
| hybrid_engine.py | 610 | ML + RAG fusion | Hybrid signal engine |
| analysis_orchestrator.py | 480 | Analysis coordination | Market analysis orchestrator |
| coach_manager.py | 732 | Training management | Model lifecycle manager |
| vectorizer.py | 267 | Feature extraction | Market feature extraction |
| state_reconstructor.py | 59 | Tick → tensor | OHLCV → tensor |

**Total CS2 Lines Analyzed: ~8,334 (core modules only, excluding utilities, tests, and configs)**
**Total CS2 Lines Full Repo: ~63,035**

## Appendix B: Mathematical Foundations Cross-Reference

| V1 Bot Math Domain | Equations | Integration Point in Adapted Architecture |
|---|---|---|
| Stochastic Calculus | GBM, Itô, Black-Scholes | ScenarioAnalyzer CHANCE nodes |
| Time Series | ARIMA, GARCH, Kalman | MarketFeatureExtractor preprocessing |
| ML/DL | LSTM, Transformer, TFT | JEPA temporal processing layer |
| Reinforcement Learning | MDP, SAC, diff. Sharpe | Pedagogy V(s) + training reward |
| Market Microstructure | VPIN, Lambda, Hawkes | MarketFeatureExtractor input features |
| Information Theory | Shannon, KL, MI | MaturityObservatory + drift detection |
| Risk Management | VaR, CVaR, Kelly | Risk Check stage + position sizing |
| Portfolio Theory | Markowitz, HRP | Portfolio-level position allocation |
| Optimization | Adam, SGD, KKT | TrainingOrchestrator optimizer config |
| Technical Indicators | 60+ formulas | MarketFeatureExtractor (60 features) |
| Ensemble Methods | Bagging, Stacking | Multi-model signal aggregation |
| Wavelet Analysis | DWT, CWT | Multi-resolution feature decomposition |
| Macroeconomics | Taylor Rule, IRP | Calendar event impact modeling |
| Confidence Gating | Page-Hinkley, CUSUM | MaturityObservatory drift detection |

---

_Document generated: 2026-02-24. Total word count target: 19,000+. This document represents the complete architectural merger specification between the Macena CS2 Analyzer and the V1 Bot trading system._
