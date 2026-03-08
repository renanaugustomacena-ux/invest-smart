# MONEYMAKER V1 -- AI/ML Training Infrastructure and Pipeline

> **Autore** | Renan Augusto Macena

---

## Table of Contents

1. [Introduction -- Teaching the Machine to Trade](#1-introduction--teaching-the-machine-to-trade)
2. [GPU Training Environment Setup](#2-gpu-training-environment-setup)
3. [Feature Engineering Pipeline](#3-feature-engineering-pipeline)
4. [Labeling Strategy -- Triple Barrier Method](#4-labeling-strategy--triple-barrier-method)
5. [Model Architectures](#5-model-architectures)
6. [Training Workflow](#6-training-workflow)
7. [Ensemble Strategy](#7-ensemble-strategy)
8. [Model Versioning and Deployment](#8-model-versioning-and-deployment)
9. [TensorBoard and Training Monitoring](#9-tensorboard-and-training-monitoring)
10. [Common Pitfalls and How We Avoid Them](#10-common-pitfalls-and-how-we-avoid-them)

---

## 1. Introduction -- Teaching the Machine to Trade

The ML Training Lab is where the core intelligence of MONEYMAKER V1 is forged. It is the dedicated environment in which machine learning models are trained, validated, and prepared for deployment into the live trading system. Unlike the Algo Engine (Document 5), which makes real-time decisions in production, the Training Lab operates offline, consuming historical data and producing model artifacts that will eventually power the Brain's inference engine. The separation between training and inference is deliberate: training is computationally expensive, GPU-intensive, and tolerant of latency, while inference must be lightweight, deterministic, and execute within milliseconds. By isolating these two concerns, MONEYMAKER achieves both the depth of learning needed for robust models and the speed required for live trading.

The Training Lab runs on a dedicated virtual machine within the MONEYMAKER infrastructure. This VM has exclusive access to an AMD Radeon RX 9070 XT GPU, passed through via VFIO from the Proxmox hypervisor. The GPU provides 16 GB of VRAM and the computational throughput necessary to train deep neural networks on millions of data points. The VM runs Ubuntu 24.04 with AMD's ROCm 6.3 stack, which provides the HIP runtime and libraries that allow PyTorch to execute on AMD hardware with near-parity to NVIDIA's CUDA ecosystem. This is a non-trivial configuration -- AMD GPUs require careful environment variable tuning and kernel configuration that we document exhaustively in Section 2.

The training pipeline follows a strict sequence of stages, each building on the output of the previous one. The stages are:

1. **Raw Data Ingestion**: Historical OHLCV (Open, High, Low, Close, Volume) data is fetched from the TimescaleDB instance (see Document 3) or from external APIs via yfinance and ccxt. This raw data is the foundation upon which everything is built. The quality of the raw data directly determines the ceiling of model performance -- no amount of sophisticated architecture can compensate for dirty or incomplete data.

2. **Feature Engineering**: Raw prices are transformed into a rich set of technical indicators, statistical features, and derived signals. This stage converts the four-dimensional price data (OHLCV) into a 40+ dimensional feature space that captures momentum, volatility, trend strength, mean reversion signals, volume dynamics, and price structure. The feature engineering code is shared between the Training Lab and the Algo Engine to ensure there is zero training-serving skew.

3. **Labeling**: Each data point is assigned a label (BUY, HOLD, or SELL) using the Triple Barrier Method. This is a sophisticated labeling approach borrowed from Marcos Lopez de Prado's "Advances in Financial Machine Learning" that considers not just the future return, but the path the price takes to get there. A bar that eventually reaches a profit target but first triggers a stop-loss is labeled differently than one that moves directly to profit.

4. **Training**: The labeled, feature-engineered data is fed into one or more model architectures. MONEYMAKER trains a diverse ensemble of models: Transformer encoders, BiLSTM networks, dilated convolutional networks, gradient-boosted trees (LightGBM, XGBoost), and experimental architectures like the Mixture of Experts (TradingBrain) and Deep Q-Networks. Each architecture captures different patterns in the data, and their diversity is the foundation of the ensemble strategy.

5. **Validation**: Models are validated using walk-forward validation, the gold standard for temporal data. Unlike k-fold cross-validation, which shuffles data and breaks temporal ordering, walk-forward validation trains on a historical window and tests on the immediately following window, then slides forward. This mimics how the model will actually be used in production: trained on the past, deployed to predict the future.

6. **Deployment**: Validated models are registered in the model registry (PostgreSQL), their checkpoint files and scaler parameters are saved to disk, and a champion-challenger evaluation determines whether the new model should replace the current production model. If promoted, the Algo Engine is notified via a signal file and performs a hot-swap of model weights without requiring a restart.

The overarching goal of this entire pipeline is to produce models that **generalize** to unseen market data. Overfitting -- where a model memorizes the training data rather than learning transferable patterns -- is the single greatest risk in financial ML. A model that achieves 95% accuracy on historical data but performs at chance on live data is worse than useless: it provides false confidence that leads to real losses. Every design decision in the Training Lab, from the choice of validation strategy to the regularization techniques to the label smoothing, is oriented toward this goal of generalization.

This document covers every aspect of the ML Training Lab in exhaustive detail. Section 2 describes the GPU environment setup, including the AMD ROCm configuration, PyTorch installation, and Python environment. Section 3 details the feature engineering pipeline, from raw indicators through fractional differencing and normalization. Section 4 explains the Triple Barrier labeling method. Section 5 presents all model architectures. Section 6 covers the training workflow, including data splitting, the training loop, walk-forward validation, and hyperparameter optimization. Section 7 describes the ensemble strategy. Section 8 covers model versioning and deployment. Section 9 discusses monitoring with TensorBoard. Section 10 addresses common pitfalls and the specific countermeasures MONEYMAKER employs.

---

## 2. GPU Training Environment Setup

### 2.1 AMD ROCm Configuration

MONEYMAKER V1 uses an AMD Radeon RX 9070 XT as its training accelerator. This GPU is based on AMD's RDNA 4 architecture (device ID `gfx1201`) and provides 16 GB of GDDR6 VRAM, 64 compute units, and a memory bandwidth of approximately 576 GB/s. While NVIDIA dominates the ML training landscape, the RX 9070 XT offers compelling price-to-performance for medium-scale training workloads, and AMD's ROCm (Radeon Open Compute) ecosystem has matured sufficiently to support PyTorch with reasonable parity.

The GPU is passed through to the Training VM via VFIO (Virtual Function I/O) from the Proxmox hypervisor. VFIO allows the VM to have direct, bare-metal access to the GPU hardware, bypassing the hypervisor's emulation layer. This is essential for ML workloads because GPU compute kernels cannot tolerate the latency and overhead of software emulation. The VFIO passthrough configuration is documented in Document 2 (Infrastructure and VM Topology).

**ROCm 6.3 Installation on Ubuntu 24.04:**

The ROCm stack installation follows AMD's official procedure but requires several RDNA 4-specific adjustments. The installation sequence is:

```bash
# 1. Add AMD's GPG key and repository
wget -q -O - https://repo.radeon.com/rocm/rocm.gpg.key | sudo apt-key add -
echo 'deb [arch=amd64] https://repo.radeon.com/rocm/apt/6.3/ ubuntu noble main' | \
    sudo tee /etc/apt/sources.list.d/rocm.list

# 2. Install the ROCm meta-package
sudo apt update
sudo apt install rocm-dev rocm-libs miopen-hip rocblas hipblas

# 3. Add user to render and video groups
sudo usermod -aG render,video $USER

# 4. Verify installation
rocminfo | grep gfx
# Expected output: Name: gfx1201
```

After installation, the ROCm runtime must detect the GPU correctly. Running `rocminfo` should list the `gfx1201` agent. Running `rocm-smi` should show the GPU temperature, clock speeds, and memory utilization.

**Critical Environment Variables:**

The RDNA 4 architecture is relatively new to the ROCm ecosystem, and several environment variables are required to ensure stable operation. These variables are set in the Training VM's `/etc/environment` and in the Python virtual environment's activation script:

```bash
# CRITICAL: Disable System DMA engine
# On gfx1201, the SDMA engine has a known issue that causes memory corruption
# during large tensor transfers. Disabling it forces all DMA operations through
# the shader engine, which is slower but correct.
export HSA_ENABLE_SDMA=0

# GPU device selection
# In a multi-GPU system, these variables restrict PyTorch to the training GPU.
# Even in our single-GPU setup, setting them explicitly prevents any ambiguity.
export ROCR_VISIBLE_DEVICES=0
export HIP_VISIBLE_DEVICES=0

# Target architecture
# Tells the HIP compiler which GPU architecture to generate code for.
# Without this, the compiler may generate generic code that runs slower.
export HCC_AMDGPU_TARGET=gfx1201

# PyTorch memory allocator configuration
# expandable_segments:True allows the memory allocator to grow in segments
# rather than pre-allocating a fixed pool. This reduces memory fragmentation
# and avoids OOM errors during training when tensor sizes vary.
export PYTORCH_HIP_ALLOC_CONF=expandable_segments:True

# MIOpen kernel compilation parallelism
# MIOpen (AMD's deep learning primitives library) compiles GPU kernels on first
# use. Setting parallel compilation to 4 threads speeds up the first-run warmup.
export MIOPEN_COMPILE_PARALLEL_LEVEL=4

# Disable MIOpen database logging (reduces disk I/O during training)
export MIOPEN_DEBUG_DISABLE_SQL_WAL=1

# Set MIOpen cache directory (pre-compiled kernels are cached here)
export MIOPEN_USER_DB_PATH=/home/moneymaker/.config/miopen/
export MIOPEN_CUSTOM_CACHE_DIR=/home/moneymaker/.cache/miopen/
```

The `HSA_ENABLE_SDMA=0` variable deserves special emphasis. Without this setting, the System DMA engine on `gfx1201` can corrupt tensor data during host-to-device and device-to-host transfers. This manifests as NaN values appearing in loss computations, seemingly random gradient explosions, or models that train perfectly for 10 epochs and then suddenly diverge. The corruption is intermittent and data-dependent, making it extremely difficult to diagnose without prior knowledge of this issue. Setting `HSA_ENABLE_SDMA=0` unconditionally prevents this class of bugs at the cost of approximately 5-10% slower data transfer speeds, which is an acceptable tradeoff for training correctness.

### 2.2 PyTorch with ROCm

PyTorch provides official ROCm-compatible wheels that include the HIP runtime and all necessary backend libraries. The installation uses AMD's PyTorch index URL:

```bash
# Install PyTorch with ROCm 6.3 support
pip install torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/rocm6.3
```

After installation, verification is performed with a comprehensive test script:

```python
import torch

# Basic GPU detection
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available (HIP backend): {torch.cuda.is_available()}")
print(f"Device count: {torch.cuda.device_count()}")
print(f"Device name: {torch.cuda.get_device_name(0)}")
print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

# Compute verification: matrix multiplication
a = torch.randn(4096, 4096, device='cuda', dtype=torch.float32)
b = torch.randn(4096, 4096, device='cuda', dtype=torch.float32)
c = torch.mm(a, b)
print(f"Matrix multiply result shape: {c.shape}")
print(f"Result contains NaN: {torch.isnan(c).any().item()}")  # Must be False

# Mixed precision verification
with torch.cuda.amp.autocast():
    d = torch.mm(a.half(), b.half())
    print(f"FP16 result dtype: {d.dtype}")  # Should be float16
    print(f"FP16 result contains NaN: {torch.isnan(d).any().item()}")  # Must be False
```

Note that PyTorch uses the `torch.cuda` namespace even on AMD GPUs. This is because ROCm's HIP runtime provides CUDA API compatibility, so all `torch.cuda.*` calls are transparently mapped to HIP equivalents. There is no need to change any PyTorch code when switching between NVIDIA and AMD hardware.

**Mixed Precision Training:**

Mixed precision training uses FP16 (half-precision) arithmetic for forward and backward passes while maintaining FP32 (full-precision) master copies of weights. This provides approximately 2x speedup on the RX 9070 XT because:

- FP16 operations use half the memory bandwidth, and training is typically memory-bandwidth-bound
- The GPU's tensor cores (or equivalent compute units in RDNA 4) natively support FP16 at higher throughput
- Reduced memory consumption allows larger batch sizes

The implementation uses PyTorch's Automatic Mixed Precision (AMP):

```python
scaler = torch.cuda.amp.GradScaler()

for batch in dataloader:
    optimizer.zero_grad()

    with torch.cuda.amp.autocast():
        output = model(batch['features'])
        loss = criterion(output, batch['labels'])

    scaler.scale(loss).backward()
    scaler.unscale_(optimizer)
    torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
    scaler.step(optimizer)
    scaler.update()
```

The `GradScaler` dynamically adjusts the loss scaling factor to prevent FP16 underflow during backward passes. If gradients become too small to represent in FP16, the scaler increases the scaling factor; if gradients overflow (producing Inf values), the scaler reduces the factor and skips that optimizer step.

**GPU Memory Management:**

With 16 GB of VRAM, the RX 9070 XT can train models with up to approximately 50 million parameters in FP16, or 25 million in FP32. For larger models or larger batch sizes, we employ gradient checkpointing:

```python
from torch.utils.checkpoint import checkpoint

class CheckpointedTransformerLayer(nn.Module):
    def forward(self, x):
        # Instead of storing all intermediate activations, recompute them
        # during the backward pass. Trades compute for memory.
        return checkpoint(self._forward_impl, x, use_reentrant=False)
```

Gradient checkpointing reduces memory consumption by approximately 60% at the cost of approximately 30% longer training time. This tradeoff is worthwhile when training the largest models in our ensemble.

### 2.3 Python Environment

The Training VM uses a dedicated Python virtual environment to isolate ML dependencies from the system Python. The environment is created and managed as follows:

```bash
# Create virtual environment
python3.11 -m venv /home/moneymaker/ml_env

# Activate
source /home/moneymaker/ml_env/bin/activate

# Core ML packages
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.3
pip install numpy pandas polars scikit-learn
pip install xgboost lightgbm catboost
pip install optuna  # Hyperparameter optimization

# Data packages
pip install yfinance  # Yahoo Finance data
pip install ccxt  # Cryptocurrency exchange API (async support)
pip install pyarrow  # Parquet file I/O (fast columnar storage)
pip install psycopg2-binary  # PostgreSQL driver
pip install sqlalchemy  # ORM for database operations

# Utility packages
pip install loguru  # Structured logging with rotation
pip install rich  # Rich console output (progress bars, tables)
pip install tensorboard  # Training visualization
pip install matplotlib seaborn  # Plotting for analysis notebooks

# Feature engineering
pip install ta  # Technical analysis library
pip install statsmodels  # Statistical models (ADF test for stationarity)

# Experiment tracking
pip install mlflow  # Optional: experiment tracking server
```

The environment is version-pinned using a `requirements.txt` file with exact versions to ensure reproducibility. Every training run logs the output of `pip freeze` alongside the model checkpoint so that the exact software environment can be reconstructed if needed.

Key version constraints:

- Python 3.11 (required for latest PyTorch ROCm builds)
- NumPy < 2.0 (compatibility with older scientific packages)
- Pandas >= 2.0 (performance improvements with Arrow backend)
- Polars >= 0.20 (used for high-performance data manipulation in feature engineering)

---

## 3. Feature Engineering Pipeline

### 3.1 The Feature Engineering Philosophy

Feature engineering is the process of transforming raw market data into a representation that a machine learning model can effectively learn from. In the context of financial time series, this is particularly challenging because raw prices are non-stationary (their statistical properties change over time), highly noisy (signal-to-noise ratio is extremely low), and exhibit complex, non-linear dependencies that vary across market regimes.

MONEYMAKER's feature engineering pipeline is governed by three core principles:

**Principle 1: Features Must Be Informative.** Each feature must carry some predictive signal about future price movements. A feature that is pure noise -- even if it is a well-known technical indicator -- degrades model performance by expanding the feature space without adding information. We validate informativeness using mutual information scores and permutation importance tests during model development. Features that consistently rank at the bottom of importance rankings across multiple models and time periods are candidates for removal.

**Principle 2: Features Must Be Stationary (or Nearly So).** Machine learning models assume that the statistical relationship between features and labels is stable over time. If a feature's distribution shifts (non-stationarity), the model's learned decision boundaries become invalid. Raw prices are non-stationary by definition (they trend upward or downward), so we transform them into stationary representations: returns, normalized oscillators, fractionally differenced series, and z-scored values. Stationarity is verified using the Augmented Dickey-Fuller (ADF) test with a significance level of 0.05.

**Principle 3: Features Must Be Non-Redundant.** Highly correlated features (multicollinearity) waste model capacity and can cause instability in linear models and gradient-based optimization. For example, RSI(14) and RSI(21) are typically correlated at r > 0.9, so including both provides diminishing marginal information. We monitor pairwise correlations and variance inflation factors (VIF) during feature selection, removing or combining features that exceed correlation thresholds (r > 0.85).

The transformation pipeline applies three sequential stages to the raw data:

```
Raw Prices (OHLCV)
    |
    v
Technical Indicators (40+ features)
    |
    v
Stationary Features (fractional differencing, returns, normalization)
    |
    v
Normalized Sequences (z-scored, windowed for model input)
```

### 3.2 Technical Indicators (40+ Features)

The feature engineering module computes a comprehensive suite of technical indicators from raw OHLCV data. Each indicator is carefully chosen to capture a specific aspect of market behavior, and all are transformed to be approximately stationary and scale-invariant.

**Returns (Multi-Horizon):**

Log returns at multiple horizons capture momentum at different scales:

```python
for horizon in [1, 5, 10, 20]:
    df[f'log_return_{horizon}'] = np.log(df['close'] / df['close'].shift(horizon))
```

- `log_return_1`: Single-bar momentum. Captures immediate price changes. High-frequency noise but also contains microstructure signals.
- `log_return_5`: Short-term momentum (approximately 1 hour at 15-minute bars). Captures intraday trend continuation.
- `log_return_10`: Medium-term momentum. Smooths out noise, captures more persistent trends.
- `log_return_20`: Longer-term momentum. Captures multi-session trends and mean reversion setups.

Log returns are preferred over simple returns because they are additive over time (log_return over N bars = sum of individual log returns) and have better statistical properties (closer to normal distribution).

**Volatility (Rolling Standard Deviation):**

```python
for window in [10, 20, 50]:
    df[f'volatility_{window}'] = df['log_return_1'].rolling(window).std()
```

- `volatility_10`: Short-term volatility regime. Spikes during news events, earnings releases.
- `volatility_20`: Medium-term volatility. Captures the current risk environment.
- `volatility_50`: Long-term volatility baseline. Slow-moving, captures structural regime shifts.

Volatility is arguably the most important feature category. High-volatility regimes require wider stop-losses and different position sizing than low-volatility regimes. Models that are aware of the current volatility regime can adapt their predictions accordingly.

**RSI (Relative Strength Index):**

```python
for period in [14, 21]:
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    # Normalize to [-1, +1] for ML compatibility
    df[f'rsi_{period}'] = (rsi - 50) / 50
```

RSI measures momentum by comparing the magnitude of recent gains to recent losses. Values above 0 (70 in traditional terms) indicate overbought conditions; values below 0 (30 in traditional terms) indicate oversold. The normalization to [-1, +1] is essential for neural network training, as it centers the feature around zero and bounds its range.

**MACD (Moving Average Convergence/Divergence):**

```python
ema_12 = df['close'].ewm(span=12).mean()
ema_26 = df['close'].ewm(span=26).mean()
macd_line = (ema_12 - ema_26) / df['close']  # Divide by price for scale invariance
signal_line = macd_line.ewm(span=9).mean()
histogram = macd_line - signal_line

df['macd_line'] = macd_line
df['macd_signal'] = signal_line
df['macd_histogram'] = histogram
```

The MACD captures trend momentum through the difference between fast and slow exponential moving averages. Critically, we divide by price to achieve scale invariance: a MACD value of 10 means very different things when the price is 100 vs. 2000. The histogram (difference between MACD line and signal line) is particularly informative as it captures the rate of change of momentum.

**Bollinger Bands:**

```python
sma_20 = df['close'].rolling(20).mean()
std_20 = df['close'].rolling(20).std()
upper_band = sma_20 + 2 * std_20
lower_band = sma_20 - 2 * std_20

# %B: position of price within the bands (0 = at lower, 1 = at upper)
df['bb_percent_b'] = (df['close'] - lower_band) / (upper_band - lower_band)
# Bandwidth: width of bands relative to price (volatility measure)
df['bb_bandwidth'] = (upper_band - lower_band) / sma_20
```

Bollinger %B and bandwidth capture both mean-reversion signals (price at extremes of bands) and volatility regimes (bandwidth expansion/contraction).

**ATR (Average True Range):**

```python
for period in [7, 14]:
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = true_range.rolling(period).mean()
    df[f'atr_{period}'] = atr / df['close']  # Normalize by price
```

ATR measures volatility in absolute terms (unlike standard deviation which measures return volatility). Normalizing by price converts it to a percentage measure. ATR is also used to set dynamic stop-loss and take-profit levels in the Triple Barrier labeling method.

**Stochastic Oscillator (%K/%D):**

```python
low_14 = df['low'].rolling(14).min()
high_14 = df['high'].rolling(14).max()
df['stoch_k'] = ((df['close'] - low_14) / (high_14 - low_14) - 0.5) * 2  # [-1, +1]
df['stoch_d'] = df['stoch_k'].rolling(3).mean()
```

The stochastic oscillator measures where the closing price falls within the recent high-low range. It is complementary to RSI and provides an additional momentum perspective.

**ADX with Directional Indicators (+DI/-DI):**

```python
# Directional Movement
plus_dm = df['high'].diff()
minus_dm = -df['low'].diff()
plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

atr_14 = ...  # As computed above
plus_di = 100 * (plus_dm.rolling(14).mean() / atr_14)
minus_di = 100 * (minus_dm.rolling(14).mean() / atr_14)
dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
adx = dx.rolling(14).mean()

df['adx'] = adx / 50 - 1  # Normalize to [-1, +1]
df['di_diff'] = (plus_di - minus_di) / 50  # Normalized directional difference
```

The ADX is critical for regime detection. An ADX above 25 (0 in our normalized scale) indicates a strong trend, while below 20 indicates a range-bound market. The directional indicators (+DI/-DI) tell the model which direction the trend is moving. This feature combination allows the model to distinguish between trending and mean-reverting market regimes, which require fundamentally different trading strategies.

**EMA Crossovers:**

```python
for fast, slow in [(9, 21), (21, 50), (50, 200)]:
    ema_fast = df['close'].ewm(span=fast).mean()
    ema_slow = df['close'].ewm(span=slow).mean()
    df[f'ema_cross_{fast}_{slow}'] = (ema_fast - ema_slow) / df['close']
```

EMA crossover signals capture trend direction at multiple timeframes. The 9/21 crossover captures short-term trends, 21/50 captures medium-term, and 50/200 captures the long-term secular trend (the famous "golden cross" and "death cross").

**Williams %R:**

```python
df['williams_r'] = ((df['high'].rolling(14).max() - df['close']) /
                     (df['high'].rolling(14).max() - df['low'].rolling(14).min()) - 0.5) * 2
```

Williams %R is an inverse stochastic oscillator that measures overbought/oversold conditions. It is complementary to both RSI and Stochastic, providing a slightly different perspective on momentum.

**CCI (Commodity Channel Index):**

```python
typical_price = (df['high'] + df['low'] + df['close']) / 3
sma_tp = typical_price.rolling(20).mean()
mad = typical_price.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean())
df['cci'] = (typical_price - sma_tp) / (0.015 * mad) / 200  # Normalized
```

CCI identifies cyclical trends by measuring the deviation of price from its statistical mean, normalized by the mean absolute deviation. It is particularly useful for identifying when price is at extremes relative to its recent history.

**Volume Indicators:**

```python
# On-Balance Volume (normalized)
obv = (np.sign(df['close'].diff()) * df['volume']).cumsum()
df['obv_norm'] = (obv - obv.rolling(50).mean()) / obv.rolling(50).std()

# Volume Ratio: current volume relative to average
df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
df['volume_ratio'] = np.log1p(df['volume_ratio'])  # Log transform to reduce skewness
```

Volume provides critical confirmation of price movements. A breakout on high volume is more likely to persist than one on low volume. OBV captures the cumulative flow of volume with price direction, and the volume ratio captures whether current activity is above or below normal.

**Price Structure:**

```python
# High-Low Range (normalized by price)
df['hl_range'] = (df['high'] - df['low']) / df['close']

# Body-to-Shadow Ratio (candlestick analysis)
body = abs(df['close'] - df['open'])
total_range = df['high'] - df['low']
df['body_shadow_ratio'] = body / total_range.replace(0, np.nan)
df['body_shadow_ratio'] = df['body_shadow_ratio'].fillna(0)
```

Price structure features capture candlestick patterns in a continuous, ML-friendly format. A high body-to-shadow ratio indicates a decisive candle (strong directional conviction), while a low ratio indicates indecision (doji-like candles).

**Rate of Change (ROC):**

```python
for period in [5, 10, 20]:
    df[f'roc_{period}'] = (df['close'] - df['close'].shift(period)) / df['close'].shift(period)
```

ROC is a simple but effective momentum measure that captures the percentage change over different horizons. It is more interpretable than log returns and captures the same directional information.

### 3.3 Fractional Differencing

Fractional differencing is one of the most important -- and most overlooked -- techniques in financial feature engineering. It addresses the fundamental stationarity-memory dilemma that plagues all time series analysis.

**The Dilemma:**

Machine learning models require stationary features (stable statistical properties over time). The standard approach to achieving stationarity is integer differencing: taking first differences (returns) of prices. However, integer differencing is a blunt instrument. First differencing (d=1) achieves stationarity but destroys all memory of the price level. The model loses the information that "price is at an all-time high" or "price is near a major support level" -- information that is extremely valuable for prediction.

The opposite extreme -- using raw prices (d=0) -- preserves all memory but is non-stationary. The model would see prices ranging from, say, 1500 to 2500 during training and then encounter 2700 during inference, a value it has never seen before.

**The Solution: Fractional Differencing**

Fractional differencing with d between 0 and 1 provides a continuous spectrum between no differencing (d=0, full memory, non-stationary) and full differencing (d=1, no memory, stationary). The goal is to find the minimum d that achieves stationarity while preserving the maximum amount of memory from the original series.

The fractionally differenced series is computed using the backshift operator and the generalized binomial theorem:

```python
def get_weights(d, threshold=1e-4, max_length=500):
    """
    Compute weights for fractional differencing using the binomial series expansion.

    The fractional differencing operator (1 - B)^d is expanded as:
    w_0 = 1
    w_k = -w_{k-1} * (d - k + 1) / k

    Weights are truncated when |w_k| < threshold to make computation tractable.
    """
    weights = [1.0]
    k = 1
    while True:
        w = -weights[-1] * (d - k + 1) / k
        if abs(w) < threshold:
            break
        weights.append(w)
        k += 1
        if k > max_length:
            break
    return np.array(weights[::-1])  # Reverse for convolution


def frac_diff(series, d, threshold=1e-4):
    """
    Apply fractional differencing of order d to a time series.
    """
    weights = get_weights(d, threshold)
    width = len(weights)
    result = np.full(len(series), np.nan)

    for i in range(width - 1, len(series)):
        result[i] = np.dot(weights, series[i - width + 1:i + 1])

    return result


def find_min_d(series, max_d=1.0, step=0.05, pvalue_threshold=0.05):
    """
    Find the minimum d that achieves stationarity (ADF test p-value < threshold).
    """
    from statsmodels.tsa.stattools import adfuller

    for d in np.arange(0, max_d + step, step):
        diffed = frac_diff(series.values, d)
        diffed_clean = diffed[~np.isnan(diffed)]

        if len(diffed_clean) < 100:
            continue

        adf_stat, pvalue, *_ = adfuller(diffed_clean, maxlag=1)

        if pvalue < pvalue_threshold:
            return d

    return 1.0  # Fall back to integer differencing
```

In practice, for XAU/USD (gold) price series, the minimum d typically falls in the range [0.35, 0.55]. This means that approximately 45-65% of the price memory is preserved while achieving stationarity. The fractionally differenced price series retains information about relative price levels and long-term trends while having stable statistical properties that ML models can learn from.

Fractional differencing is applied to:

- Log prices: `frac_diff(np.log(close), d)` -- the primary target
- Volume: `frac_diff(np.log1p(volume), d)` -- captures volume regime changes
- Spread: `frac_diff(spread, d)` -- captures liquidity regime changes

The ADF test to find minimum d is performed once during initial model development and periodically rechecked during retraining. If the optimal d shifts significantly, it may indicate a structural change in the market that warrants investigation.

### 3.4 Feature Normalization

Normalization is the process of scaling features to a common range so that no single feature dominates the model's learning simply by having a larger numerical magnitude. Without normalization, a feature ranging from -1 to 1 (like RSI) would have negligible influence compared to a feature ranging from 0 to 100 (like raw ADX), even if the former is more predictive.

**StandardScaler (Z-Score Normalization):**

The primary normalization method is z-score normalization:

```python
x_normalized = (x - mean) / std
```

This transforms each feature to have zero mean and unit variance. The critical implementation detail is that the scaler must be fit on the training data only:

```python
from sklearn.preprocessing import StandardScaler
import json

# Fit scaler on TRAINING data only
scaler = StandardScaler()
scaler.fit(X_train)  # Computes mean and std from training data

# Transform all splits using the SAME scaler
X_train_scaled = scaler.transform(X_train)
X_val_scaled = scaler.transform(X_val)
X_test_scaled = scaler.transform(X_test)

# Save scaler parameters for deployment
scaler_params = {
    'mean': scaler.mean_.tolist(),
    'std': scaler.scale_.tolist(),
    'feature_names': feature_names
}
with open('scaler_params.json', 'w') as f:
    json.dump(scaler_params, f)
```

Fitting the scaler on validation or test data constitutes data leakage -- the model indirectly gains information about the future distribution. This is one of the most common and insidious mistakes in financial ML, and MONEYMAKER enforces this constraint at the code level.

The scaler parameters (mean and standard deviation for each feature) are saved as a JSON file alongside the model checkpoint. During inference, the Algo Engine loads these parameters and applies the same normalization to live data. This ensures that the feature distribution seen during inference matches the distribution seen during training.

**Alternative Scalers:**

For features with natural bounds (RSI, Stochastic, %B), MinMaxScaler is used:

```python
x_normalized = (x - x_min) / (x_max - x_min)
```

For features with heavy outliers (volume ratio, ATR during extreme volatility events), RobustScaler is used:

```python
x_normalized = (x - median) / IQR
```

where IQR is the interquartile range (Q3 - Q1). This is less sensitive to outliers than StandardScaler because the median and IQR are robust statistics.

### 3.5 Sequence Construction

Neural network models in MONEYMAKER operate on sequences of feature vectors, not individual data points. Each input to the model is a window of consecutive bars, allowing the model to learn temporal patterns and dependencies.

**Input Shape:** `(batch_size, sequence_length, n_features)`

- `batch_size`: Number of sequences in a mini-batch (typically 256)
- `sequence_length`: Number of consecutive bars in each sequence (64 bars)
- `n_features`: Number of features per bar (40+, varies by configuration)

**Sequence Construction:**

```python
def create_sequences(features, labels, seq_length=64, step=1):
    """
    Create overlapping sequences using a sliding window.

    Args:
        features: (n_bars, n_features) array of normalized features
        labels: (n_bars,) array of integer labels
        seq_length: Number of bars per sequence
        step: Sliding window step size

    Returns:
        X: (n_sequences, seq_length, n_features) array
        y: (n_sequences,) array (label at the last bar of each sequence)
    """
    X, y = [], []
    for i in range(0, len(features) - seq_length, step):
        X.append(features[i:i + seq_length])
        y.append(labels[i + seq_length - 1])  # Label at the end of the window

    return np.array(X), np.array(y)
```

The sequence length of 64 bars is a tunable hyperparameter. At 15-minute bars, 64 bars represents 16 hours of market data (approximately 2 trading days). This window is long enough to capture intraday trends and short-term patterns while being short enough to fit comfortably in GPU memory. The hyperparameter search (Section 6.4) explores sequence lengths from 32 to 128.

**No Shuffling:** The sequences are NOT shuffled during dataset construction. For validation and testing, temporal order must be strictly preserved. During training, we use a `SequentialSampler` that samples sequences in order within each epoch, or a `RandomSampler` that shuffles only the order in which sequences are presented (not the bars within sequences). This ensures that the model never sees "future" data within a sequence.

---

## 4. Labeling Strategy -- Triple Barrier Method

### 4.1 Why Not Simple Returns?

The most straightforward approach to labeling financial data is to compute the future return over a fixed horizon and classify it as BUY (positive return), SELL (negative return), or HOLD (return close to zero). This is intuitive but deeply flawed.

Consider a bar where the price rises 3% over the next 20 bars. A fixed-horizon label would mark this as BUY. But what if, during those 20 bars, the price first dropped 5% (triggering any reasonable stop-loss) before recovering? A trader who entered a long position at this bar would have been stopped out at a 5% loss, even though the "label" says BUY. The model learns that this pattern is a buy signal, and in production it enters the trade, gets stopped out, and loses money.

The fundamental problem is that fixed-horizon labels ignore the price path between the entry and the label horizon. They assume that the trader holds the position for exactly N bars regardless of what happens, which is not how any rational trading system operates. MONEYMAKER uses stop-losses and take-profits, and the labeling method must account for this.

### 4.2 The Three Barriers

The Triple Barrier Method, introduced by Marcos Lopez de Prado, addresses this by defining three barriers around each bar:

**Upper Barrier (Take Profit):** A horizontal barrier above the current price at a distance of `TP%`. If the price rises and touches this barrier before the other two, the trade would have been profitable, and the label is BUY (class 2).

**Lower Barrier (Stop Loss):** A horizontal barrier below the current price at a distance of `SL%`. If the price falls and touches this barrier before the other two, the trade would have hit the stop-loss, and the label is SELL (class 0).

**Vertical Barrier (Timeout):** A vertical barrier at `max_holding_period` bars in the future. If neither the upper nor lower barrier is hit within this time window, the trade would have been held to timeout, and the label is HOLD (class 1).

```python
def triple_barrier_label(close_prices, idx, tp_mult=1.5, sl_mult=0.8,
                          max_holding=20, atr_period=14):
    """
    Compute triple barrier label for bar at index idx.

    Barrier levels are based on ATR for dynamic adaptation to volatility.
    """
    # Current price
    price = close_prices[idx]

    # Compute ATR at this bar
    # (simplified -- actual implementation uses the full ATR calculation)
    recent_ranges = close_prices[idx - atr_period:idx].diff().abs()
    atr = recent_ranges.rolling(atr_period).mean().iloc[-1]

    # Set barrier levels
    tp_distance = tp_mult * atr
    sl_distance = sl_mult * atr
    upper_barrier = price + tp_distance
    lower_barrier = price - sl_distance

    # Check which barrier is hit first
    future_prices = close_prices[idx + 1:idx + 1 + max_holding]

    for t, future_price in enumerate(future_prices):
        if future_price >= upper_barrier:
            return 2  # BUY -- TP hit first
        if future_price <= lower_barrier:
            return 0  # SELL -- SL hit first

    return 1  # HOLD -- timeout reached
```

**Dynamic Barrier Levels:**

The barrier distances are not fixed percentages but are scaled by ATR (Average True Range). During high-volatility periods, barriers are wider; during low-volatility periods, they are tighter. This ensures that:

- In volatile markets, the model does not generate excessive SELL labels from normal volatility triggering tight stop-losses
- In quiet markets, the model does not generate excessive HOLD labels from wide barriers that are never reached

The multipliers `tp_mult=1.5` and `sl_mult=0.8` are asymmetric by design. The take-profit is set wider than the stop-loss, reflecting the asymmetric risk-reward ratio that profitable trading systems require. A trade that risks 0.8 ATR to gain 1.5 ATR has a reward-to-risk ratio of 1.875:1, meaning the system can be profitable even with a win rate below 50%.

### 4.3 Symmetric Labeling

The basic Triple Barrier Method as described above only considers long (buy) trades. But MONEYMAKER also takes short (sell) trades, so the labeling must consider both directions symmetrically.

For each bar, we evaluate two scenarios:

1. **Long scenario:** Price rises to upper barrier (TP for long) or falls to lower barrier (SL for long)
2. **Short scenario:** Price falls to lower barrier (TP for short) or rises to upper barrier (SL for short)

```python
def symmetric_triple_barrier(close_prices, idx, tp_mult=1.5, sl_mult=0.8,
                              max_holding=20, atr_period=14):
    """
    Symmetric labeling that considers both long and short opportunities.
    """
    price = close_prices[idx]
    atr = compute_atr(close_prices, idx, atr_period)

    tp_distance = tp_mult * atr
    sl_distance = sl_mult * atr

    long_tp = price + tp_distance
    long_sl = price - sl_distance
    short_tp = price - tp_distance
    short_sl = price + sl_distance

    future_prices = close_prices[idx + 1:idx + 1 + max_holding]

    long_tp_time = None
    long_sl_time = None
    short_tp_time = None
    short_sl_time = None

    for t, fp in enumerate(future_prices):
        if long_tp_time is None and fp >= long_tp:
            long_tp_time = t
        if long_sl_time is None and fp <= long_sl:
            long_sl_time = t
        if short_tp_time is None and fp <= short_tp:
            short_tp_time = t
        if short_sl_time is None and fp >= short_sl:
            short_sl_time = t

    # Determine which profitable exit happens first
    long_profit_time = long_tp_time if (long_tp_time is not None and
                        (long_sl_time is None or long_tp_time <= long_sl_time)) else None
    short_profit_time = short_tp_time if (short_tp_time is not None and
                         (short_sl_time is None or short_tp_time <= short_sl_time)) else None

    if long_profit_time is not None and short_profit_time is not None:
        # Both directions profitable -- choose the one that hits first
        if long_profit_time <= short_profit_time:
            return 2  # BUY
        else:
            return 0  # SELL
    elif long_profit_time is not None:
        return 2  # BUY
    elif short_profit_time is not None:
        return 0  # SELL
    else:
        return 1  # HOLD -- neither direction is profitable within horizon
```

This symmetric approach ensures that the model learns to identify both bullish and bearish setups with equal fidelity. In a strongly trending market, the labels will naturally skew toward the trend direction; in a ranging market, HOLD labels will dominate.

### 4.4 Label Distribution and Balancing

After applying the Triple Barrier Method to the entire dataset, the typical label distribution is approximately:

- BUY (class 2): ~30%
- HOLD (class 1): ~40%
- SELL (class 0): ~30%

The exact distribution varies by market regime and barrier parameters. During strongly trending periods, one directional class may dominate; during ranging periods, HOLD dominates.

**Class Imbalance Handling:**

Moderate class imbalance (30/40/30) does not require aggressive resampling, but it does require adjustments to the loss function to prevent the model from degenerating into always predicting the majority class (HOLD).

MONEYMAKER uses a weighted cross-entropy loss:

```python
# Compute class weights inversely proportional to frequency
class_counts = np.bincount(labels)
total = len(labels)
class_weights = total / (len(class_counts) * class_counts)
class_weights = torch.tensor(class_weights, dtype=torch.float32).to(device)

criterion = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=0.1)
```

Label smoothing with a factor of 0.1 softens the hard labels (e.g., [0, 0, 1] becomes [0.033, 0.033, 0.933]). This prevents the model from becoming overconfident in its predictions and acts as a form of regularization.

**Why NOT SMOTE for Time Series:**

SMOTE (Synthetic Minority Over-sampling Technique) creates synthetic training samples by interpolating between existing minority class samples. While effective for tabular data, it is inappropriate for time series because:

- It creates samples that do not correspond to any real temporal sequence
- The synthetic features may violate temporal dependencies (e.g., impossible sequences of returns)
- It breaks the causal structure of the data

Instead, MONEYMAKER relies on the weighted loss function and label smoothing to handle imbalance, combined with the natural balancing effect of the symmetric labeling approach.

---

## 5. Model Architectures

### 5.1 Primary: Transformer Encoder (XAUTransformer)

The primary model architecture is a Transformer Encoder adapted for time-series classification. The Transformer architecture, originally developed for natural language processing, is well-suited to financial time series because its self-attention mechanism can capture long-range dependencies without the vanishing gradient problems of recurrent networks.

**Architecture Overview:**

```
Input: (batch, 64, n_features)
    |
    v
Input Projection: Linear(n_features, 96)  -- projects features to model dimension
    |
    v
Sinusoidal Positional Encoding  -- injects temporal order information
    |
    v
TransformerEncoderLayer x 3:
    - MultiHeadAttention(d_model=96, nhead=4)  -- self-attention
    - FeedForward(96 -> 384 -> 96)  -- non-linear transformation
    - LayerNorm + Dropout(0.35) + Residual connections
    |
    v
LayerNorm
    |
    v
Global Average Pooling (across time dimension)
    |
    v
4 Output Heads:
    - direction_head: Linear(96, 48) -> ReLU -> Dropout -> Linear(48, 3)  -- BUY/HOLD/SELL
    - confidence_head: Linear(96, 48) -> ReLU -> Linear(48, 1) -> Sigmoid  -- [0, 1]
    - sl_head: Linear(96, 48) -> ReLU -> Linear(48, 1) -> Softplus -> * 0.02
    - tp_head: Linear(96, 48) -> ReLU -> Linear(48, 1) -> Softplus -> * 0.04
```

**Implementation:**

```python
class XAUTransformer(nn.Module):
    def __init__(self, n_features, d_model=96, nhead=4, num_layers=3,
                 dim_feedforward=384, dropout=0.35, num_classes=3):
        super().__init__()

        # Input projection
        self.input_proj = nn.Linear(n_features, d_model)

        # Positional encoding
        self.pos_encoder = SinusoidalPositionalEncoding(d_model, max_len=256)

        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            activation='gelu',
            batch_first=True,
            norm_first=True  # Pre-LayerNorm for training stability
        )
        self.transformer = nn.TransformerEncoder(
            encoder_layer,
            num_layers=num_layers,
            norm=nn.LayerNorm(d_model)
        )

        # Output heads
        self.direction_head = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(d_model // 2, num_classes)
        )

        self.confidence_head = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.ReLU(),
            nn.Linear(d_model // 2, 1),
            nn.Sigmoid()
        )

        self.sl_head = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.ReLU(),
            nn.Linear(d_model // 2, 1),
            nn.Softplus()
        )

        self.tp_head = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.ReLU(),
            nn.Linear(d_model // 2, 1),
            nn.Softplus()
        )

    def forward(self, x):
        # x: (batch, seq_len, n_features)
        x = self.input_proj(x)          # (batch, seq_len, d_model)
        x = self.pos_encoder(x)          # Add positional information
        x = self.transformer(x)          # (batch, seq_len, d_model)
        x = x.mean(dim=1)               # Global average pooling -> (batch, d_model)

        direction = self.direction_head(x)         # (batch, 3)
        confidence = self.confidence_head(x)       # (batch, 1)
        sl_distance = self.sl_head(x) * 0.02      # (batch, 1) -- scaled SL fraction
        tp_distance = self.tp_head(x) * 0.04      # (batch, 1) -- scaled TP fraction

        return direction, confidence.squeeze(-1), sl_distance.squeeze(-1), tp_distance.squeeze(-1)
```

**Sinusoidal Positional Encoding:**

Since the Transformer has no inherent notion of sequence order (unlike RNNs), positional information is injected via sinusoidal encoding:

```python
class SinusoidalPositionalEncoding(nn.Module):
    def __init__(self, d_model, max_len=256):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer('pe', pe.unsqueeze(0))

    def forward(self, x):
        return x + self.pe[:, :x.size(1)]
```

**Why Transformer:**

- **Self-attention captures long-range dependencies:** Unlike LSTM, which must propagate information through every intervening timestep, attention can directly connect any two bars in the sequence, even if they are 60 bars apart.
- **Parallelizable training:** Unlike recurrent networks, all timesteps can be processed simultaneously, leading to significant speedup on GPU.
- **Interpretable attention weights:** The attention maps can be visualized to understand which historical bars the model considers important for its current prediction.

**Output Head Design:**

The multi-head output design is a key architectural innovation in MONEYMAKER. Rather than just predicting direction (BUY/HOLD/SELL), the model simultaneously predicts:

- **Confidence:** How certain is the model? Low confidence predictions can be filtered out.
- **Stop-Loss distance:** How far should the stop-loss be? This adapts to the model's perception of the current volatility regime.
- **Take-Profit distance:** How far should the take-profit be? This adapts to the model's perception of the current trend strength.

The Softplus activation for SL and TP heads ensures outputs are always positive. The scaling factors (0.02 for SL, 0.04 for TP) set the output range: SL distances are typically 0-2% of price, TP distances are 0-4% of price.

### 5.2 Alternative: BiLSTM with Attention

The Bidirectional LSTM provides a complementary perspective to the Transformer. While the Transformer processes all timesteps in parallel through attention, the BiLSTM processes them sequentially, maintaining an explicit hidden state that summarizes the sequence history.

```python
class BiLSTMAttention(nn.Module):
    def __init__(self, n_features, hidden_dim=128, num_layers=2,
                 dropout=0.3, num_classes=3):
        super().__init__()

        self.lstm = nn.LSTM(
            input_size=n_features,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout
        )

        # Multi-head attention for timestep weighting
        self.attention = nn.MultiheadAttention(
            embed_dim=hidden_dim * 2,  # Bidirectional doubles hidden dim
            num_heads=4,
            dropout=dropout,
            batch_first=True
        )

        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_classes)
        )

    def forward(self, x):
        lstm_out, (h_n, c_n) = self.lstm(x)  # (batch, seq, hidden*2)

        # Self-attention over LSTM outputs
        attn_out, attn_weights = self.attention(lstm_out, lstm_out, lstm_out)

        # Use attention-weighted mean
        context = attn_out.mean(dim=1)  # (batch, hidden*2)

        return self.classifier(context)
```

The bidirectional aspect allows the model to see "future" context during training (the backward LSTM processes the sequence in reverse). This is acceptable during training because we are learning patterns from complete sequences. During inference, only the forward direction contributes to real-time predictions, though in MONEYMAKER's case the model sees the full 64-bar window which is entirely historical relative to the prediction point.

### 5.3 Alternative: Dilated CNN (WaveNet-Inspired)

The Dilated CNN architecture is inspired by DeepMind's WaveNet, adapted for financial time series. It uses one-dimensional convolutions with exponentially increasing dilation rates to achieve a very large receptive field with relatively few parameters.

```python
class DilatedCNNBlock(nn.Module):
    def __init__(self, channels, kernel_size=3, dilation=1, dropout=0.2):
        super().__init__()
        self.conv1 = nn.Conv1d(channels, channels, kernel_size,
                                padding='same', dilation=dilation)
        self.conv2 = nn.Conv1d(channels, channels, kernel_size,
                                padding='same', dilation=dilation)
        self.dropout = nn.Dropout(dropout)
        self.norm = nn.BatchNorm1d(channels)

    def forward(self, x):
        # Gating mechanism
        tanh_out = torch.tanh(self.conv1(x))
        sigmoid_out = torch.sigmoid(self.conv2(x))
        gated = tanh_out * sigmoid_out
        gated = self.dropout(gated)

        # Residual connection
        return self.norm(x + gated)


class DilatedCNN(nn.Module):
    def __init__(self, n_features, channels=64, num_blocks=4,
                 dropout=0.2, num_classes=3):
        super().__init__()

        self.input_proj = nn.Conv1d(n_features, channels, kernel_size=1)

        # Exponentially increasing dilation: 1, 2, 4, 8
        self.blocks = nn.ModuleList([
            DilatedCNNBlock(channels, dilation=2**i, dropout=dropout)
            for i in range(num_blocks)
        ])

        self.classifier = nn.Sequential(
            nn.AdaptiveAvgPool1d(1),
            nn.Flatten(),
            nn.Linear(channels, channels // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(channels // 2, num_classes)
        )

    def forward(self, x):
        x = x.transpose(1, 2)  # (batch, features, seq_len) for Conv1d
        x = self.input_proj(x)

        for block in self.blocks:
            x = block(x)

        return self.classifier(x)
```

With 4 blocks and kernel size 3, the receptive field is 1 + 2 *(1 + 2 + 4 + 8) = 31 bars, covering approximately half the input sequence. The gating mechanism (tanh* sigmoid) allows the network to learn which information to pass through, similar to the LSTM's gating.

### 5.4 Tree-Based Models (CPU)

LightGBM and XGBoost are gradient-boosted decision tree models that operate on flattened tabular data. They do not process sequences directly; instead, the 64-bar sequence is flattened into a single vector of length `64 * n_features`.

```python
import lightgbm as lgb
import xgboost as xgb

# Flatten sequences for tree-based models
X_train_flat = X_train.reshape(X_train.shape[0], -1)  # (n_samples, 64 * n_features)

# LightGBM
lgb_model = lgb.LGBMClassifier(
    n_estimators=1000,
    max_depth=8,
    learning_rate=0.05,
    num_leaves=63,
    subsample=0.8,
    colsample_bytree=0.8,
    min_child_samples=50,
    reg_alpha=0.1,
    reg_lambda=0.1,
    class_weight='balanced',
    random_state=42,
    n_jobs=-1
)
lgb_model.fit(X_train_flat, y_train,
              eval_set=[(X_val_flat, y_val)],
              callbacks=[lgb.early_stopping(50)])

# XGBoost
xgb_model = xgb.XGBClassifier(
    n_estimators=1000,
    max_depth=8,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    min_child_weight=50,
    reg_alpha=0.1,
    reg_lambda=0.1,
    tree_method='hist',
    random_state=42,
    n_jobs=-1
)
xgb_model.fit(X_train_flat, y_train,
              eval_set=[(X_val_flat, y_val)],
              verbose=False)
```

**Advantages of tree-based models:**

- **Fast training on CPU:** No GPU required, trains in minutes
- **Interpretable feature importance:** Can identify which features (and which bars within the sequence) are most predictive
- **Robust to feature scale:** No normalization required (though we apply it anyway for consistency)
- **No sequence length sensitivity:** Can handle varying feature counts without architectural changes

Tree models serve as strong baselines and ensemble members. If a deep learning model cannot outperform a well-tuned LightGBM, the deep learning model's complexity is not justified.

### 5.5 Mixture of Experts (TradingBrain)

The TradingBrain architecture is an experimental model that attempts to mimic how a human trader switches between strategies based on market conditions. It uses a Mixture of Experts (MoE) design with specialized expert networks for different market regimes.

```python
class TradingBrain(nn.Module):
    def __init__(self, n_features, d_model=96, num_classes=3):
        super().__init__()

        # Layer 1: Perception -- encode raw features
        self.perception = nn.Sequential(
            nn.Linear(n_features, d_model),
            nn.GELU(),
            nn.LayerNorm(d_model)
        )

        # Layer 2: Memory -- LSTM for temporal context
        self.memory = nn.LSTM(d_model, d_model, num_layers=2,
                              batch_first=True, dropout=0.2)

        # Layer 3: Strategy -- 4 expert networks
        self.expert_trend = self._make_expert(d_model)
        self.expert_mean_reversion = self._make_expert(d_model)
        self.expert_breakout = self._make_expert(d_model)
        self.expert_range = self._make_expert(d_model)

        # Gating network: selects which expert(s) to use
        self.gating = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.ReLU(),
            nn.Linear(d_model // 2, 4),
            nn.Softmax(dim=-1)
        )

        # Layer 4: Decision -- final classification
        self.decision = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(d_model // 2, num_classes)
        )

    def _make_expert(self, d_model):
        return nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.GELU(),
            nn.Dropout(0.2),
            nn.Linear(d_model, d_model)
        )

    def forward(self, x):
        # Perception
        x = self.perception(x)  # (batch, seq, d_model)

        # Memory
        memory_out, _ = self.memory(x)  # (batch, seq, d_model)
        context = memory_out[:, -1, :]  # Last timestep (batch, d_model)

        # Strategy: compute expert outputs
        experts = torch.stack([
            self.expert_trend(context),
            self.expert_mean_reversion(context),
            self.expert_breakout(context),
            self.expert_range(context)
        ], dim=1)  # (batch, 4, d_model)

        # Gating: determine expert weights
        gate_weights = self.gating(context)  # (batch, 4)

        # Weighted combination of expert outputs
        combined = (experts * gate_weights.unsqueeze(-1)).sum(dim=1)  # (batch, d_model)

        # Decision
        return self.decision(combined)
```

The gating network learns to route inputs to the appropriate expert based on market conditions. For example, during a strong uptrend (high ADX, positive EMA crossovers), the gating network should route primarily to the Trend expert. During a ranging market (low ADX, mean-reverting price), it should route to the MeanReversion or Range expert.

### 5.6 Reinforcement Learning (DQN Ensemble)

The Reinforcement Learning approach treats trading as a sequential decision-making problem rather than a classification problem. Instead of predicting a label, the RL agent learns a policy that maps states (market conditions) to actions (BUY, HOLD, SELL) by maximizing cumulative reward.

MONEYMAKER implements three DQN variants that vote together:

1. **DQN (Deep Q-Network):** Standard value function approximation
2. **DoubleDQN:** Reduces overestimation bias by decoupling action selection and value estimation
3. **DuelingDQN:** Separates state value and action advantage for more stable learning

```python
class DuelingDQN(nn.Module):
    def __init__(self, state_dim, action_dim=3, hidden_dim=128):
        super().__init__()

        self.feature_net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU()
        )

        # Value stream
        self.value_stream = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1)
        )

        # Advantage stream
        self.advantage_stream = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, action_dim)
        )

    def forward(self, x):
        features = self.feature_net(x)
        value = self.value_stream(features)
        advantage = self.advantage_stream(features)
        # Q(s,a) = V(s) + A(s,a) - mean(A(s,a))
        return value + advantage - advantage.mean(dim=-1, keepdim=True)
```

**Reward Function -- Differential Sharpe Ratio:**

The reward at each timestep is the Differential Sharpe Ratio, which is a risk-adjusted measure that penalizes both losses and excessive volatility:

```python
def differential_sharpe_ratio(returns, A_prev=0, B_prev=0, eta=0.01):
    """
    Incremental Sharpe ratio update.
    A_prev: exponential moving average of returns
    B_prev: exponential moving average of squared returns
    """
    A_t = A_prev + eta * (returns - A_prev)
    B_t = B_prev + eta * (returns**2 - B_prev)

    denominator = (B_t - A_t**2)**0.5
    if denominator < 1e-8:
        return 0.0

    dsr = (B_prev * (returns - A_prev) - 0.5 * A_prev * (returns**2 - B_prev)) / \
          (B_t - A_t**2)**1.5

    return dsr, A_t, B_t
```

The experience replay buffer stores 100,000 transitions and is sampled uniformly during training. The three DQN agents are trained independently and their action choices are aggregated by majority voting during inference.

---

## 6. Training Workflow

### 6.1 Data Split Strategy

Financial time series require a fundamentally different data splitting strategy than standard ML datasets. Random shuffling is prohibited because it would allow the model to "see the future" -- training on data from March and testing on data from January is data leakage.

MONEYMAKER uses a strict temporal split:

```
|<------- 80% Train ------->|<- 10% Val ->|<- 10% Test ->|
                             ^              ^
                         Purge Gap      Purge Gap
                          (5 bars)       (5 bars)
```

```python
def temporal_split(features, labels, train_ratio=0.80, val_ratio=0.10, purge_gap=5):
    """
    Split data temporally with purge gaps to prevent label leakage.
    """
    n = len(features)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))

    X_train = features[:train_end]
    y_train = labels[:train_end]

    # Purge gap: skip 5 bars between train and validation
    X_val = features[train_end + purge_gap:val_end]
    y_val = labels[train_end + purge_gap:val_end]

    # Purge gap: skip 5 bars between validation and test
    X_test = features[val_end + purge_gap:]
    y_test = labels[val_end + purge_gap:]

    return (X_train, y_train), (X_val, y_val), (X_test, y_test)
```

The **purge gap** of 5 bars between splits is critical. Because the Triple Barrier Method uses future prices (up to 20 bars ahead) to compute labels, the last few bars of the training set have labels that depend on prices in the validation set. The purge gap ensures that no training label is computed using any validation/test data.

The scaler is fit on `X_train` only, then applied to all three splits. This is enforced at the code level with assertion checks.

### 6.2 Training Loop

The training loop implements a comprehensive set of techniques for robust, stable training:

```python
def train_model(model, train_loader, val_loader, config):
    """
    Full training loop with all MONEYMAKER best practices.
    """
    # Optimizer: AdamW with weight decay for L2 regularization
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config['lr'],            # Default: 1e-3
        weight_decay=config['wd'],  # Default: 0.05
        betas=(0.9, 0.999)
    )

    # Learning rate scheduler: cosine annealing with warm restarts
    scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(
        optimizer,
        T_0=10,   # First restart after 10 epochs
        T_mult=2  # Double the period after each restart
    )

    # Mixed precision components
    scaler = torch.cuda.amp.GradScaler()

    # Loss function with class weights and label smoothing
    criterion = nn.CrossEntropyLoss(
        weight=config['class_weights'].to(device),
        label_smoothing=0.10
    )

    # Early stopping
    best_val_loss = float('inf')
    patience_counter = 0
    patience = 15

    # Gradient accumulation
    accumulation_steps = 4

    for epoch in range(config['max_epochs']):
        model.train()
        epoch_loss = 0
        optimizer.zero_grad()

        for step, batch in enumerate(train_loader):
            features = batch['features'].to(device)
            labels = batch['labels'].to(device)

            # Data augmentation: Gaussian noise
            if config['augment_noise']:
                noise = torch.randn_like(features) * 0.03
                features = features + noise

            # Data augmentation: temporal masking (randomly zero out 10% of timesteps)
            if config['augment_mask']:
                mask = torch.rand(features.shape[:2], device=device) > 0.10
                features = features * mask.unsqueeze(-1)

            # Forward pass with mixed precision
            with torch.cuda.amp.autocast():
                direction, confidence, sl, tp = model(features)
                loss = criterion(direction, labels)

            # Scale loss for gradient accumulation
            loss = loss / accumulation_steps
            scaler.scale(loss).backward()

            if (step + 1) % accumulation_steps == 0:
                # Gradient clipping (prevents exploding gradients)
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)

                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad()

            epoch_loss += loss.item() * accumulation_steps

        # Validation
        val_loss, val_acc = evaluate(model, val_loader, criterion)
        scheduler.step()

        # Logging
        logger.info(f"Epoch {epoch}: train_loss={epoch_loss/len(train_loader):.4f}, "
                     f"val_loss={val_loss:.4f}, val_acc={val_acc:.4f}, "
                     f"lr={scheduler.get_last_lr()[0]:.6f}")

        # Early stopping check
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            torch.save(model.state_dict(), config['checkpoint_path'])
        else:
            patience_counter += 1
            if patience_counter >= patience:
                logger.info(f"Early stopping at epoch {epoch}")
                break

    # Load best model
    model.load_state_dict(torch.load(config['checkpoint_path']))
    return model
```

**Key Design Decisions:**

**AdamW Optimizer:** Adam with decoupled weight decay. Standard Adam applies weight decay as L2 regularization to the gradient, which interacts poorly with the adaptive learning rate. AdamW decouples these, applying weight decay directly to the weights, which is mathematically more principled and empirically more effective.

**Cosine Annealing with Warm Restarts:** The learning rate follows a cosine curve from the initial value down to near zero, then resets ("warm restart") and repeats with a longer period. This allows the model to escape local minima during the restart phase and fine-tune during the low-LR phase. The schedule is: 10 epochs at period 1, 20 epochs at period 2, 40 epochs at period 3, and so on.

**Gradient Accumulation:** With an actual batch size of 256 and accumulation over 4 steps, the effective batch size is 1024. This provides more stable gradient estimates without requiring 4x the GPU memory. Gradients from 4 mini-batches are summed before the optimizer step.

**Gradient Clipping:** Clipping the gradient norm to 1.0 prevents catastrophic gradient explosions, which can occur when the model encounters outlier data points (e.g., flash crashes or extreme volatility events).

**Data Augmentation:** Gaussian noise (sigma=0.03) adds random perturbations to features, forcing the model to be robust to small variations. Temporal masking (randomly zeroing 10% of timesteps) forces the model to make predictions even with missing information, improving robustness to data quality issues in production.

### 6.3 Walk-Forward Validation

Walk-forward validation is the gold standard for evaluating time series models. It simulates how the model will actually be used: trained on historical data and deployed to predict future data.

```python
def walk_forward_validation(model_class, features, labels, config,
                            n_splits=5, train_ratio=0.7, purge_gap=5, embargo=3):
    """
    Walk-forward validation with purge and embargo.

    |<-- train -->|purge|<- val ->|embargo|<-- train -->|purge|<- val ->|...
    """
    n = len(features)
    fold_size = n // n_splits
    results = []

    for fold in range(n_splits):
        # Define fold boundaries
        fold_start = fold * fold_size
        fold_end = min((fold + 1) * fold_size + int(fold_size * (1 - train_ratio)), n)

        train_end = fold_start + int((fold_end - fold_start) * train_ratio)
        val_start = train_end + purge_gap
        val_end = fold_end

        # Extract data
        X_train = features[fold_start:train_end]
        y_train = labels[fold_start:train_end]
        X_val = features[val_start:val_end]
        y_val = labels[val_start:val_end]

        # Fit scaler on this fold's training data
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train.reshape(-1, X_train.shape[-1]))
        X_val_scaled = scaler.transform(X_val.reshape(-1, X_val.shape[-1]))

        # Reshape back to sequences
        X_train_scaled = X_train_scaled.reshape(X_train.shape)
        X_val_scaled = X_val_scaled.reshape(X_val.shape)

        # Train model
        model = model_class(**config['model_params']).to(device)
        model = train_model(model, make_loader(X_train_scaled, y_train),
                           make_loader(X_val_scaled, y_val), config)

        # Evaluate
        predictions = predict(model, X_val_scaled)
        fold_metrics = compute_metrics(predictions, y_val, X_val)
        fold_metrics['fold'] = fold
        results.append(fold_metrics)

        logger.info(f"Fold {fold}: accuracy={fold_metrics['accuracy']:.4f}, "
                     f"sharpe={fold_metrics['sharpe']:.4f}")

    # Aggregate results
    avg_sharpe = np.mean([r['sharpe'] for r in results])
    min_sharpe = min([r['sharpe'] for r in results])
    avg_accuracy = np.mean([r['accuracy'] for r in results])

    logger.info(f"Walk-Forward Results: avg_sharpe={avg_sharpe:.4f}, "
                 f"min_sharpe={min_sharpe:.4f}, avg_accuracy={avg_accuracy:.4f}")

    # Reject model if worst fold loses money
    if min_sharpe < 0:
        logger.warning("MODEL REJECTED: negative Sharpe in at least one fold")
        return None, results

    return results
```

The **purge gap** (5 bars) prevents label leakage between training and validation within each fold. The **embargo** (3 bars) provides additional buffer after the validation window before the next fold's training data begins, preventing any residual information leakage from the validation period into the next fold's training.

The rejection criterion -- minimum fold Sharpe ratio must be positive -- is deliberately conservative. A model that loses money in even one temporal fold is considered unreliable. This filter prevents deployment of models that happen to perform well on average but catastrophically fail in certain market regimes.

### 6.4 Hyperparameter Optimization

MONEYMAKER uses Optuna, a Bayesian hyperparameter optimization framework, to automatically search the hyperparameter space:

```python
import optuna

def objective(trial):
    """Optuna objective function for hyperparameter search."""

    # Sample hyperparameters
    config = {
        'lr': trial.suggest_float('lr', 1e-5, 1e-2, log=True),
        'd_model': trial.suggest_categorical('d_model', [64, 96, 128]),
        'nhead': trial.suggest_categorical('nhead', [2, 4, 8]),
        'num_layers': trial.suggest_int('num_layers', 2, 6),
        'dropout': trial.suggest_float('dropout', 0.1, 0.5),
        'batch_size': trial.suggest_categorical('batch_size', [128, 256, 512]),
        'seq_length': trial.suggest_categorical('seq_length', [32, 64, 128]),
        'weight_decay': trial.suggest_float('weight_decay', 1e-4, 1e-1, log=True),
    }

    # Validate d_model is divisible by nhead
    if config['d_model'] % config['nhead'] != 0:
        raise optuna.TrialPruned()

    # Build model and data loaders with trial config
    model = XAUTransformer(
        n_features=n_features,
        d_model=config['d_model'],
        nhead=config['nhead'],
        num_layers=config['num_layers'],
        dropout=config['dropout']
    ).to(device)

    train_loader = make_loader(X_train, y_train, batch_size=config['batch_size'])
    val_loader = make_loader(X_val, y_val, batch_size=config['batch_size'])

    # Train for limited epochs
    for epoch in range(30):
        train_one_epoch(model, train_loader, config)
        val_loss, val_acc = evaluate(model, val_loader)

        # Report intermediate value for pruning
        trial.report(val_acc, epoch)

        # Prune unpromising trials early
        if trial.should_prune():
            raise optuna.TrialPruned()

    return val_acc

# Create study with median pruner
study = optuna.create_study(
    direction='maximize',
    pruner=optuna.pruners.MedianPruner(n_startup_trials=10, n_warmup_steps=5)
)

# Run optimization
study.optimize(objective, n_trials=100, timeout=30*60)  # 50-100 trials, 30 min max

logger.info(f"Best trial: {study.best_trial.params}")
logger.info(f"Best accuracy: {study.best_trial.value:.4f}")
```

The **MedianPruner** terminates trials that perform below the median of completed trials at the same epoch. This dramatically reduces total computation time by killing unpromising hyperparameter configurations early. With 100 trials and a 30-minute timeout, the typical search takes 2-4 hours and evaluates 60-80 complete trials (the rest are pruned).

---

## 7. Ensemble Strategy

### 7.1 Multi-Model Ensemble

MONEYMAKER's ensemble strategy is based on the principle that diverse models capture different patterns in the data, and their aggregation produces more robust predictions than any individual model. The ensemble consists of six models:

1. **XAUTransformer** -- captures long-range dependencies via self-attention
2. **BiLSTM with Attention** -- captures sequential patterns with bidirectional context
3. **LSTM-Attention** (unidirectional) -- captures sequential patterns without future context
4. **Dilated CNN** -- captures multi-scale local patterns via dilated convolutions
5. **LightGBM** -- captures non-linear feature interactions via gradient-boosted trees
6. **XGBoost** -- captures similar patterns to LightGBM with different regularization

Diversity is the key to ensemble effectiveness. If all models make the same predictions, combining them provides no benefit. The six architectures are deliberately chosen to be structurally diverse: attention-based, recurrence-based, convolution-based, and tree-based. They have different inductive biases and will make different types of errors.

Each model is trained independently on the same data and produces probability distributions over the three classes (BUY, HOLD, SELL). These probability vectors are the inputs to the ensemble combination methods.

**Out-of-Fold Predictions:**

To prevent the ensemble from overfitting to the training data, each model's predictions are generated using out-of-fold evaluation. For each fold of the walk-forward validation, the model predicts on data it was not trained on. These out-of-fold predictions are then used to train the meta-learner.

```python
def generate_oof_predictions(model_class, features, labels, n_folds=5):
    """Generate out-of-fold predictions for meta-learner training."""
    oof_predictions = np.zeros((len(features), 3))  # 3 classes

    fold_size = len(features) // n_folds

    for fold in range(n_folds):
        val_start = fold * fold_size
        val_end = min((fold + 1) * fold_size, len(features))

        # Train on everything except this fold
        train_idx = list(range(0, val_start)) + list(range(val_end, len(features)))
        val_idx = list(range(val_start, val_end))

        model = train_on_subset(model_class, features[train_idx], labels[train_idx])
        oof_predictions[val_idx] = predict_proba(model, features[val_idx])

    return oof_predictions
```

### 7.2 Stacking Meta-Learner

The stacking meta-learner is a second-level model that learns to optimally combine the predictions of the six base models:

```python
from sklearn.linear_model import LogisticRegression

# Concatenate OOF predictions from all 6 models
# Each model produces 3 probabilities, so meta_features has 18 columns
meta_features = np.hstack([
    oof_transformer,     # (n_samples, 3)
    oof_bilstm,          # (n_samples, 3)
    oof_lstm_attn,       # (n_samples, 3)
    oof_dilated_cnn,     # (n_samples, 3)
    oof_lightgbm,        # (n_samples, 3)
    oof_xgboost          # (n_samples, 3)
])  # Shape: (n_samples, 18)

# Train meta-learner on validation set
meta_model = LogisticRegression(
    C=1.0,
    max_iter=1000,
    multi_class='multinomial',
    solver='lbfgs',
    class_weight='balanced'
)
meta_model.fit(meta_features[val_idx], labels[val_idx])
```

The meta-learner is deliberately simple (logistic regression) to avoid overfitting the ensemble itself. A complex meta-learner could learn to memorize which base model is correct for specific data points, which does not generalize. The logistic regression learns stable, linear relationships between base model predictions and the correct label.

The meta-learner's coefficients are interpretable: they reveal which base models are most trusted. For example, if the Transformer coefficient is highest, the meta-learner has learned that the Transformer is the most reliable predictor on this data.

### 7.3 Genetic Evolution of Weights

In addition to the fixed stacking meta-learner, MONEYMAKER employs a genetic algorithm to evolve ensemble weights nightly. This adaptation mechanism allows the ensemble to shift its trust toward models that are performing well in the current market regime.

```python
import random

def genetic_ensemble_optimization(model_predictions, true_labels, price_data,
                                   pop_size=50, generations=50):
    """
    Evolve ensemble weights using a genetic algorithm.

    Fitness: net_profit * (1 - max_drawdown)^2 * log(trade_count)
    """
    n_models = len(model_predictions)

    # Initialize population: random weight vectors
    population = [np.random.dirichlet(np.ones(n_models)) for _ in range(pop_size)]

    for gen in range(generations):
        # Evaluate fitness
        fitness_scores = []
        for individual in population:
            # Weighted average of model predictions
            ensemble_pred = sum(w * pred for w, pred in zip(individual, model_predictions))
            final_pred = np.argmax(ensemble_pred, axis=-1)

            # Simulate trading with these predictions
            trades = simulate_trades(final_pred, price_data)
            net_profit = trades['net_profit']
            max_dd = trades['max_drawdown']
            n_trades = trades['trade_count']

            # Fitness function
            if n_trades < 10 or net_profit <= 0:
                fitness = 0
            else:
                fitness = net_profit * (1 - max_dd)**2 * np.log(n_trades + 1)

            fitness_scores.append(fitness)

        # Selection: tournament selection (k=3)
        new_population = []
        for _ in range(pop_size):
            tournament = random.sample(range(pop_size), 3)
            winner = max(tournament, key=lambda i: fitness_scores[i])
            new_population.append(population[winner].copy())

        # Crossover: two-point crossover
        for i in range(0, pop_size - 1, 2):
            if random.random() < 0.7:  # Crossover probability
                pt1, pt2 = sorted(random.sample(range(n_models), 2))
                child1 = np.concatenate([
                    new_population[i][:pt1],
                    new_population[i+1][pt1:pt2],
                    new_population[i][pt2:]
                ])
                child2 = np.concatenate([
                    new_population[i+1][:pt1],
                    new_population[i][pt1:pt2],
                    new_population[i+1][pt2:]
                ])
                # Renormalize to sum to 1
                new_population[i] = child1 / child1.sum()
                new_population[i+1] = child2 / child2.sum()

        # Mutation: Gaussian perturbation
        for i in range(pop_size):
            if random.random() < 0.1:  # Mutation probability
                mutation = np.random.normal(0, 0.05, n_models)
                new_population[i] = np.clip(new_population[i] + mutation, 0.01, 1.0)
                new_population[i] /= new_population[i].sum()

        population = new_population

    # Return best individual
    best_idx = max(range(pop_size), key=lambda i: fitness_scores[i])
    return population[best_idx]
```

The fitness function `net_profit * (1 - max_drawdown)^2 * log(trade_count)` balances three objectives:

- **Net profit:** The ensemble must make money
- **Max drawdown penalty:** The squared term heavily penalizes large drawdowns, preferring consistent returns over volatile high returns
- **Trade count bonus:** The log term gently rewards more active ensembles, preventing degenerate solutions that trade once and happen to be right

The genetic algorithm runs nightly on the previous day's data, producing updated ensemble weights that are deployed for the next trading session. This allows the ensemble to adapt as market regimes shift -- for example, increasing the Trend expert's weight during trending markets and the MeanReversion expert's weight during ranging markets.

---

## 8. Model Versioning and Deployment

### 8.1 Model Registry

Every trained model is registered in the PostgreSQL database with comprehensive metadata:

```sql
CREATE TABLE model_registry (
    model_id        SERIAL PRIMARY KEY,
    model_name      VARCHAR(100) NOT NULL,
    model_version   VARCHAR(50) NOT NULL,
    architecture    VARCHAR(50) NOT NULL,  -- 'transformer', 'bilstm', etc.
    trained_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Training configuration
    config_json     JSONB NOT NULL,  -- Full hyperparameter config

    -- Performance metrics
    train_accuracy  FLOAT,
    val_accuracy    FLOAT,
    test_accuracy   FLOAT,
    val_sharpe      FLOAT,
    val_max_dd      FLOAT,
    wf_avg_sharpe   FLOAT,  -- Walk-forward average Sharpe
    wf_min_sharpe   FLOAT,  -- Walk-forward minimum Sharpe

    -- File paths
    checkpoint_path VARCHAR(500),
    scaler_path     VARCHAR(500),

    -- Deployment status
    status          VARCHAR(20) DEFAULT 'trained',  -- trained/challenger/champion/retired
    promoted_at     TIMESTAMPTZ,
    retired_at      TIMESTAMPTZ,

    -- Data provenance
    train_start     TIMESTAMPTZ,
    train_end       TIMESTAMPTZ,
    n_train_samples INTEGER,
    n_features      INTEGER,

    UNIQUE(model_name, model_version)
);
```

Checkpoint files follow a strict naming convention:

```
/home/moneymaker/models/
    xau_transformer_v1.2.3_20260221_143052.pt
    xau_transformer_v1.2.3_20260221_143052_scaler.json
    xau_bilstm_v1.1.0_20260220_091500.pt
    xau_bilstm_v1.1.0_20260220_091500_scaler.json
```

The version format is `major.minor.patch`:

- **Major:** Architecture change (new model structure)
- **Minor:** Hyperparameter change or retraining with new data
- **Patch:** Same config, retrained for validation purposes

### 8.2 Champion-Challenger Promotion

The promotion process ensures that only models that demonstrably improve upon the current production model are deployed:

```python
def evaluate_challenger(challenger_model, champion_model, test_data, config):
    """
    Determine whether the challenger should replace the champion.
    """
    # Evaluate both models on the same held-out test data
    challenger_metrics = evaluate_model(challenger_model, test_data)
    champion_metrics = evaluate_model(champion_model, test_data)

    # Promotion criteria (ALL must be met)
    criteria = {
        'accuracy': challenger_metrics['accuracy'] > config.get('min_accuracy', 0.80),
        'sharpe_improvement': challenger_metrics['sharpe'] > champion_metrics['sharpe'] * 1.05,
        'max_dd_acceptable': challenger_metrics['max_drawdown'] < 0.15,
        'min_trades': challenger_metrics['trade_count'] > 50,
        'wf_positive': challenger_metrics['wf_min_sharpe'] > 0,
    }

    all_passed = all(criteria.values())

    logger.info(f"Promotion evaluation:")
    for criterion, passed in criteria.items():
        logger.info(f"  {criterion}: {'PASS' if passed else 'FAIL'}")

    if all_passed:
        promote_model(challenger_model)
        logger.info("Challenger PROMOTED to champion")
    else:
        logger.info("Challenger REJECTED -- champion retained")

    return all_passed
```

**Hot-Swap Mechanism:**

When a challenger is promoted, the Algo Engine must load the new model weights without restarting. This is accomplished via a signal file:

```python
# ML Lab writes signal file after promotion
signal_data = {
    'action': 'UPDATE_MODEL',
    'model_name': 'xau_transformer',
    'model_version': 'v1.2.3',
    'checkpoint_path': '/home/moneymaker/models/xau_transformer_v1.2.3_20260221.pt',
    'scaler_path': '/home/moneymaker/models/xau_transformer_v1.2.3_20260221_scaler.json',
    'timestamp': datetime.utcnow().isoformat()
}

with open('/shared/model_updates/UPDATE_SIGNAL', 'w') as f:
    json.dump(signal_data, f)
```

The Algo Engine watches the `/shared/model_updates/` directory using `inotify` (or polling) and, upon detecting a new signal file, loads the new checkpoint and scaler parameters. The swap is atomic: the old model remains active until the new model is fully loaded and verified, then a pointer swap makes the new model active for subsequent predictions.

### 8.3 Continuous Learning

MONEYMAKER implements a multi-tier retraining schedule to keep models current with evolving market dynamics:

**Daily Retraining (Sliding Window):**

- Every night at 00:00 UTC, the most recent 90 days of data is used to fine-tune the current model
- The fine-tuning uses a reduced learning rate (1/10 of the original) to preserve existing knowledge while adapting to recent patterns
- The fine-tuned model is evaluated via the champion-challenger process before promotion

**Weekly Full Retraining:**

- Every Sunday, a full retraining is performed on the extended history (up to 2 years of data)
- All hyperparameters are re-optimized via a short Optuna search (20 trials)
- The ensemble weights are re-evolved via the genetic algorithm

**Monthly Walk-Forward Validation:**

- Every month, a full walk-forward validation is performed on the most recent 6 months of data
- If the average Sharpe ratio drops below 0.5 or the minimum fold Sharpe drops below 0, an alert is raised
- This serves as a degradation detector: if market conditions have changed fundamentally, the model may need architectural changes, not just retraining

---

## 9. TensorBoard and Training Monitoring

Training monitoring is essential for diagnosing problems, tracking progress, and making informed decisions about model development. MONEYMAKER uses TensorBoard as its primary training visualization tool, supplemented by Loguru for structured logging and custom dashboards.

**TensorBoard Integration:**

```python
from torch.utils.tensorboard import SummaryWriter

writer = SummaryWriter(log_dir=f'/home/moneymaker/tb_logs/{model_name}_{timestamp}')

# During training loop:
writer.add_scalar('Loss/train', train_loss, epoch)
writer.add_scalar('Loss/validation', val_loss, epoch)
writer.add_scalar('Accuracy/train', train_acc, epoch)
writer.add_scalar('Accuracy/validation', val_acc, epoch)
writer.add_scalar('Sharpe/validation', val_sharpe, epoch)
writer.add_scalar('Learning_Rate', scheduler.get_last_lr()[0], epoch)

# Confusion matrix at end of each validation epoch
from sklearn.metrics import confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns

cm = confusion_matrix(y_true, y_pred, labels=[0, 1, 2])
fig, ax = plt.subplots(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=['SELL', 'HOLD', 'BUY'],
            yticklabels=['SELL', 'HOLD', 'BUY'], ax=ax)
ax.set_xlabel('Predicted')
ax.set_ylabel('Actual')
writer.add_figure('Confusion_Matrix', fig, epoch)
plt.close(fig)

# Feature importance heatmap (for tree models)
if hasattr(model, 'feature_importances_'):
    importance = model.feature_importances_.reshape(seq_length, n_features)
    fig, ax = plt.subplots(figsize=(12, 8))
    sns.heatmap(importance, cmap='viridis', ax=ax)
    ax.set_xlabel('Feature Index')
    ax.set_ylabel('Timestep')
    writer.add_figure('Feature_Importance', fig, epoch)
    plt.close(fig)

writer.close()
```

**Key Metrics Monitored:**

- **Loss curves (train vs. validation):** The gap between training and validation loss is the primary indicator of overfitting. If training loss continues to decrease while validation loss plateaus or increases, the model is overfitting.
- **Accuracy and Sharpe per epoch:** These are the ultimate performance metrics. Sharpe ratio is preferred over accuracy because it accounts for the magnitude and risk of trades, not just the direction.
- **Learning rate schedule:** Visualizing the cosine annealing schedule helps verify that warm restarts are occurring at the expected epochs.
- **Confusion matrix:** Reveals class-specific performance. A model that achieves 80% accuracy by always predicting HOLD (the majority class) would show a degenerate confusion matrix with no BUY or SELL predictions.
- **Gradient norms:** Monitoring gradient magnitudes helps detect vanishing or exploding gradients before they manifest as training instability.

TensorBoard is accessed via a web browser on the monitoring VLAN at `http://ml-training-vm:6006`. It is not exposed to the public internet or to the trading VLAN.

---

## 10. Common Pitfalls and How We Avoid Them

Financial machine learning is notoriously prone to pitfalls that can produce models that appear to work brilliantly in backtesting but fail catastrophically in live trading. This section catalogs the most common pitfalls and describes the specific countermeasures MONEYMAKER employs.

**Pitfall 1: Overfitting**

Overfitting occurs when the model memorizes the training data rather than learning generalizable patterns. In financial ML, where the signal-to-noise ratio is extremely low, overfitting is the default outcome without aggressive countermeasures.

MONEYMAKER's defenses:

- **Walk-forward validation** (Section 6.3): The gold standard for temporal data. Ensures the model is evaluated on truly unseen future data.
- **Dropout (0.35):** Randomly disables 35% of neurons during training, forcing the network to learn redundant representations.
- **Weight decay (0.05):** L2 regularization penalizes large weights, preferring simpler models.
- **Early stopping (patience=15):** Stops training when validation performance stops improving, preventing the model from continuing to memorize training data.
- **Label smoothing (0.10):** Prevents the model from becoming overconfident in its predictions.
- **Data augmentation:** Gaussian noise and temporal masking force the model to be robust to perturbations.

**Pitfall 2: Data Leakage**

Data leakage occurs when information from the validation or test set inadvertently leaks into the training process. This inflates performance metrics and produces models that appear to predict the future but are actually cheating.

MONEYMAKER's defenses:

- **Scaler fit on training data only:** The normalization parameters (mean, std) are computed exclusively from training data. Fitting on validation data would leak information about the future distribution.
- **Purge gap (5 bars):** Because the Triple Barrier labeling uses future prices, labels near the train/validation boundary contain information about the validation period. The purge gap removes these contaminated samples.
- **No shuffling:** Data is never shuffled across temporal boundaries. Train/validation/test splits are strictly chronological.
- **Embargo (3 bars):** Additional buffer in walk-forward validation to prevent any residual leakage.

**Pitfall 3: Training-Serving Skew**

Training-serving skew occurs when the feature computation code used during training differs from the code used during inference. Even subtle differences (e.g., using a different moving average implementation, or normalizing with different parameters) can cause the model to receive inputs it was not trained on, degrading performance.

MONEYMAKER's defense:

- **Shared feature engineering code:** The exact same Python module (`feature_engineering.py`) is imported by both the Training Lab and the Algo Engine. There is one source of truth for feature computation.
- **Scaler parameters saved alongside checkpoints:** The exact mean and standard deviation used during training are saved as JSON and loaded during inference. There is no recomputation of normalization parameters.
- **Integration tests:** Automated tests verify that the features computed by the training pipeline and the inference pipeline are identical for the same input data.

**Pitfall 4: Class Imbalance**

If the label distribution is heavily skewed (e.g., 10% BUY, 80% HOLD, 10% SELL), the model can achieve high accuracy by always predicting the majority class, which is useless for trading.

MONEYMAKER's defenses:

- **Weighted cross-entropy loss:** Class weights inversely proportional to frequency ensure that misclassifying a rare class is penalized more heavily.
- **Label smoothing:** Prevents the model from collapsing to a single class by softening the target distribution.
- **Symmetric Triple Barrier labeling:** Produces more balanced labels than fixed-horizon methods by considering both long and short opportunities.
- **Evaluation with class-specific metrics:** Accuracy alone is insufficient. MONEYMAKER tracks precision, recall, and F1-score for each class independently.

**Pitfall 5: GPU Memory Errors**

Running out of GPU memory causes training to crash, losing progress. This is especially problematic with the 16 GB VRAM constraint of the RX 9070 XT.

MONEYMAKER's defenses:

- **Gradient checkpointing:** Trades compute for memory by recomputing activations during the backward pass rather than storing them.
- **Mixed precision (FP16):** Halves memory consumption for activations and gradients.
- **Batch size tuning:** The batch size is set to the largest value that fits in memory, determined empirically. Gradient accumulation is used to achieve larger effective batch sizes.
- **Memory monitoring:** A background thread monitors GPU memory utilization and logs warnings when usage exceeds 90%.

**Pitfall 6: Non-Stationarity**

Financial time series are inherently non-stationary. Statistical relationships between features and labels change as market regimes shift. A model trained on a trending market may perform poorly in a ranging market.

MONEYMAKER's defenses:

- **Fractional differencing:** Achieves stationarity while preserving memory (Section 3.3).
- **Continuous retraining:** Daily fine-tuning and weekly full retraining ensure the model adapts to evolving market conditions.
- **Regime-aware architecture:** The TradingBrain's Mixture of Experts architecture explicitly models different market regimes through specialized expert networks.
- **Walk-forward validation with rejection:** Models that fail in any temporal fold are rejected, preventing deployment of models that only work in specific regimes.

**Pitfall 7: Survivorship Bias and Look-Ahead Bias**

Survivorship bias occurs when the training data only includes assets that survived to the present (e.g., only companies that did not go bankrupt). Look-ahead bias occurs when features or labels use information that would not have been available at the time.

MONEYMAKER's defenses:

- **Single-asset focus:** MONEYMAKER trades XAU/USD (gold), which has no survivorship issue as it has been continuously traded for centuries.
- **Point-in-time features:** All features are computed using only data available at the time of the bar. No future-dated features are ever used.
- **Triple Barrier Method with explicit future window:** The label computation explicitly defines a forward-looking window, and the purge gap ensures this window does not contaminate training.

---

## Appendix A: Training Environment Quick Reference

| Component | Value |
|-----------|-------|
| GPU | AMD Radeon RX 9070 XT (16 GB VRAM, gfx1201) |
| ROCm Version | 6.3 |
| OS | Ubuntu 24.04 LTS |
| Python | 3.11 |
| PyTorch | 2.x with ROCm support |
| VRAM Budget | ~14 GB usable (OS overhead ~2 GB) |
| Max Model Size | ~50M parameters (FP16) |
| Typical Training Time | 1-4 hours per model |
| Hyperparameter Search | 50-100 trials, 2-4 hours |
| Walk-Forward Folds | 5 |
| Sequence Length | 64 bars (default) |
| Feature Count | 40+ |

## Appendix B: Feature List Summary

| Category | Features | Count |
|----------|----------|-------|
| Returns | log_return_1, _5,_10, _20 | 4 |
| Volatility | volatility_10,_20, _50 | 3 |
| RSI | rsi_14, rsi_21 | 2 |
| MACD | macd_line, macd_signal, macd_histogram | 3 |
| Bollinger | bb_percent_b, bb_bandwidth | 2 |
| ATR | atr_7, atr_14 | 2 |
| Stochastic | stoch_k, stoch_d | 2 |
| ADX | adx, di_diff | 2 |
| EMA Cross | ema_cross_9_21,_21_50,_50_200 | 3 |
| Williams %R | williams_r | 1 |
| CCI | cci | 1 |
| Volume | obv_norm, volume_ratio | 2 |
| Price Structure | hl_range, body_shadow_ratio | 2 |
| ROC | roc_5, roc_10, roc_20 | 3 |
| Fractional Diff | frac_diff_price, frac_diff_volume, frac_diff_spread | 3 |
| **Total** | | **~35-45** |

## Appendix C: Model Architecture Comparison

| Architecture | Parameters | Training Time | GPU Required | Strengths |
|-------------|-----------|---------------|-------------|-----------|
| XAUTransformer | ~2M | 2-3 hours | Yes | Long-range dependencies, parallelizable |
| BiLSTM-Attention | ~3M | 3-4 hours | Yes | Sequential patterns, bidirectional context |
| Dilated CNN | ~1M | 1-2 hours | Yes | Multi-scale local patterns, fast inference |
| TradingBrain (MoE) | ~4M | 3-5 hours | Yes | Regime-aware, interpretable expert routing |
| LightGBM | N/A (trees) | 5-15 min | No | Feature importance, fast, robust |
| XGBoost | N/A (trees) | 10-20 min | No | Similar to LightGBM, different regularization |
| DQN Ensemble | ~1M each | 2-3 hours | Yes | Sequential decision-making, risk-adjusted |

---

## Appendix D: Cross-References to Other Documents

| Document | Relevance to This Document |
|----------|---------------------------|
| 01 - System Architecture Overview | High-level system context for ML components |
| 02 - Infrastructure and VM Topology | GPU passthrough, VM configuration |
| 03 - Data Pipeline and Storage | TimescaleDB source data, data ingestion |
| 04 - Feature Store and Data Engineering | Shared feature engineering code |
| 05 - Algo Engine and Inference Engine | Consumer of trained models, hot-swap mechanism |
| 07 - Risk Management | Constraints on model outputs (SL/TP limits) |
| 08 - Backtesting Framework | Offline evaluation of trained models |
| 09 - Monitoring and Alerting | Training monitoring, model degradation alerts |
| 10 - Deployment and Operations | Model deployment procedures |

---

*Fine del documento 6 -- AI/ML Training Infrastructure and Pipeline*
