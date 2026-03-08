# Skill: MONEYMAKER V1 Model Architectures

You are the AI Architect. You design specific neural network structures tailored for financial time-series forecasting.

---

## When This Skill Applies
Activate this skill whenever:
- Defining PyTorch model classes (`nn.Module`).
- Choosing model types (Transformer, LSTM, CNN).
- Implementing custom layers or heads.
- Configuring ensemble strategies.

---

## Primary Architecture: XAUTransformer
- **Input**: `(Batch, Seq_Len=64, Features)`.
- **Core**: Transformer Encoder (3 layers, `d_model=96`, 4 heads).
- **Positional Encoding**: Sinusoidal (injection before encoder).
- **Multi-Head Output**:
    1.  **Direction**: Softmax (Buy/Hold/Sell).
    2.  **Confidence**: Sigmoid (0-1).
    3.  **Stop-Loss**: Softplus (Dynamic distance).
    4.  **Take-Profit**: Softplus (Dynamic distance).

## Alternative Architectures
- **BiLSTM-Attention**: Bidirectional LSTM with Self-Attention aggregation.
- **Dilated CNN**: WaveNet-style 1D convolutions for long receptive fields.
- **TradingBrain (MoE)**: Mixture of Experts (Trend, Mean-Rev) with Gating Network.

## Ensemble Strategy
- **Stacking**: Logistic Regression meta-learner on Out-of-Fold predictions.
- **Diversity**: Combine Transformer, LSTM, CNN, and Trees (XGBoost/LightGBM).

## Checklist
- [ ] Does the model output multiple heads (Direction + Confidence)?
- [ ] Is `batch_first=True` used?
- [ ] Are causal masks applied where necessary (though Encoder processes full window)?
- [ ] Is the sequence length standardized (64)?
