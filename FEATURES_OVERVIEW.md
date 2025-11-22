# 🎯 Complete Feature Overview

## 🖥️ DuckDice GUI

### Graphical Interface Features
✅ **User-Friendly Interface** - Intuitive Tkinter-based GUI
✅ **Multiple Tabs** - Organized access to all features
✅ **Settings Panel** - Easy API key and configuration management
✅ **Real-Time Output** - Live display of bet results and responses
✅ **Auto-Betting Support** - Integrated automated betting strategies
✅ **No Extra Dependencies** - Uses standard Python Tkinter

### Available Tabs
| Tab | Description |
|-----|-------------|
| **Dice** | Play Original Dice game with high/low betting |
| **Range Dice** | Bet on numbers being in or out of a range |
| **Stats** | View currency statistics and balances |
| **User Info** | Display comprehensive account information |
| **Auto Bet** | Run automated betting with strategy selection |

### Quick Launch
```bash
# Direct launch
python duckdice_gui.py

# Or via package entry point
pip install -e .
duckdice-gui
```

![DuckDice GUI Screenshot](https://github.com/user-attachments/assets/ff443b51-b569-4e13-bbae-c70373aece45)

---

## 🛠️ DuckDice CLI Tool

### Core API Commands
| Command | Description | Example |
|---------|-------------|---------|
| `dice` | Play Original Dice | `python duckdice.py --api-key KEY dice --symbol BTC --amount 0.1 --chance 50 --high` |
| `range-dice` | Play Range Dice | `python duckdice.py --api-key KEY range-dice --symbol XLM --amount 0.1 --range 7777 7777 --in` |
| `stats` | Get currency stats | `python duckdice.py --api-key KEY stats --symbol BTC` |
| `user-info` | Get user information | `python duckdice.py --api-key KEY user-info` |

### Supported Features
✅ High/Low betting (Original Dice)
✅ In/Out range betting (Range Dice)
✅ Faucet mode (`--faucet`)
✅ Wagering bonus support (`--wagering-bonus-hash`)
✅ TLE participation (`--tle-hash`)
✅ JSON output (`--json`)
✅ Custom API URL (`--base-url`)
✅ Timeout configuration (`--timeout`)

### Output Formats
- 📊 **Human-Readable**: Formatted tables with emojis
- 📄 **JSON**: Raw API responses for scripting

---

## 🔬 RNG Analysis Toolkit

### 1. Statistical Analysis (`pattern_analyzer.py`)

| Test | Purpose | Output |
|------|---------|--------|
| **Distribution Tests** | Chi-square, KS test | PASS/FAIL + p-values |
| **Autocorrelation** | Sequential dependencies | Correlation at each lag |
| **Runs Test** | Randomness verification | Z-score + p-value |
| **Fourier Analysis** | Periodic patterns | Frequency spectrum |
| **Seed Correlation** | Seed-outcome relationship | Variance analysis |
| **Nonce Patterns** | Nonce-based patterns | Mod analysis |

### 2. Machine Learning (`ml_predictor.py`)

| Model | Type | Purpose |
|-------|------|---------|
| **Random Forest** | Ensemble | Tree-based prediction |
| **Gradient Boosting** | Ensemble | Sequential boosting |
| **XGBoost** | Ensemble | Extreme gradient boosting |
| **LightGBM** | Ensemble | Fast gradient boosting |
| **Neural Network** | Deep | Multi-layer perceptron |
| **Ridge Regression** | Linear | L2 regularization |
| **Lasso Regression** | Linear | L1 regularization |

**Metrics Tracked:**
- MAE (Mean Absolute Error)
- RMSE (Root Mean Squared Error)
- R² Score
- Improvement over baseline
- Feature importance

### 3. Deep Learning (`deep_learning_predictor.py`)

| Model | Architecture | Sequence Length |
|-------|-------------|-----------------|
| **LSTM** | 2-layer LSTM + Dense | 50 |
| **GRU** | 2-layer GRU + Dense | 50 |
| **CNN-LSTM** | Conv1D + LSTM | 50 |
| **Attention-LSTM** | LSTM + Attention | 50 |

**Features:**
- Sequence-to-one prediction
- Overfitting detection
- Early stopping
- Dropout regularization

### 4. Visualizations (`visualizer.py`)

| Visualization | Description |
|---------------|-------------|
| **Distribution Plot** | Histogram, Q-Q plot, box plot, density |
| **Time Series** | Numbers over time, rolling means, win rates |
| **Autocorrelation** | ACF plot with significance bands |
| **Pattern Heatmap** | Transition probability matrix |
| **Feature Importance** | Bar charts per model |
| **Predictions** | Actual vs predicted, residuals |

---

## 📊 Analysis Workflow

```
┌─────────────────────────────────────┐
│   1. Load Bet History CSVs          │
│   - Multiple files support          │
│   - Extract seeds from URLs         │
│   - Create 20+ features             │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│   2. Statistical Analysis           │
│   - Distribution tests              │
│   - Autocorrelation                 │
│   - Runs test                       │
│   - Fourier analysis                │
│   - Seed/Nonce patterns            │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│   3. Machine Learning               │
│   - Train 7 models                  │
│   - Time series CV                  │
│   - Feature importance              │
│   - Classification                  │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│   4. Deep Learning                  │
│   - LSTM, GRU, CNN-LSTM            │
│   - Sequence prediction             │
│   - Overfitting analysis            │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│   5. Visualization                  │
│   - Create all plots                │
│   - Save to PNG files               │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│   6. Comprehensive Report           │
│   - Test results                    │
│   - Model performance               │
│   - Conclusions                     │
│   - Recommendations                 │
└─────────────────────────────────────┘
```

---

## 🎓 Educational Value

### What You'll Learn

#### About Cryptography
- ✅ How SHA-256 works
- ✅ Provably fair systems
- ✅ Hash function properties
- ✅ Why cryptographic RNG is secure

#### About Statistics
- ✅ Distribution testing
- ✅ Autocorrelation analysis
- ✅ Runs test
- ✅ Fourier analysis
- ✅ Hypothesis testing

#### About Machine Learning
- ✅ Supervised learning
- ✅ Feature engineering
- ✅ Time series cross-validation
- ✅ Ensemble methods
- ✅ Overfitting detection

#### About Deep Learning
- ✅ Recurrent neural networks
- ✅ LSTM/GRU architectures
- ✅ Sequence modeling
- ✅ Attention mechanisms
- ✅ Training vs validation loss

#### About Gambling
- ✅ House edge mathematics
- ✅ Why systems fail
- ✅ Gambler's fallacy
- ✅ Responsible gambling
- ✅ Problem gambling resources

---

## 📈 Performance Metrics

### Statistical Tests (Expected for Secure RNG)

| Test | Expected | Interpretation |
|------|----------|----------------|
| KS Test p-value | > 0.05 | Distribution is uniform |
| Chi-square p-value | > 0.05 | No bias detected |
| Autocorrelation | < threshold | No sequential patterns |
| Runs Test p-value | > 0.05 | Sequence is random |

### ML Performance (Expected for Secure RNG)

| Metric | Baseline | Good Performance | Bad Performance |
|--------|----------|------------------|-----------------|
| MAE | ~2887 | ≈2887 (<5% improvement) | <2600 (>10% improvement) |
| R² | 0 | <0.05 | >0.1 |
| Improvement | 0% | <5% | >10% |

Note: "Bad performance" indicates overfitting, NOT exploitability!

---

## 🎯 Expected Results

### For Secure RNG (What You Should See)

✅ **Statistical Tests: PASS**
```
Distribution Test: PASS ✅
  KS p-value: 0.234567 (>0.05)
  
Autocorrelation: PASS ✅
  No significant correlations detected
  
Runs Test: PASS ✅
  p-value: 0.456789 (>0.05)
```

✅ **ML Models: No Predictive Power**
```
Best Model: XGBoost
  MAE: 2845.23 (baseline: 2887.45)
  Improvement: 1.46% (<5%)
  R²: 0.0023 (≈0)
```

✅ **Deep Learning: Cannot Learn**
```
Best Model: LSTM
  MAE: 2891.67
  Improvement: -0.15% (worse than baseline!)
  Train Loss: 0.245
  Val Loss: 0.247 (similar to train)
```

### Conclusion
```
✅ The RNG appears cryptographically secure
✅ No exploitable patterns detected
✅ Historical data provides no predictive power
```

---

## ⚠️ Important Disclaimers

### What This Tool CAN Do
✅ Educate about RNG security
✅ Demonstrate ML/DL techniques
✅ Show why gambling systems fail
✅ Verify bet fairness
✅ Track statistics

### What This Tool CANNOT Do
❌ Predict future outcomes
❌ Beat the house edge
❌ Exploit the RNG
❌ Guarantee wins
❌ Make money

### The Reality
1. **SHA-256 is unbreakable** with current technology
2. **Each bet is independent** - past doesn't predict future
3. **Server seed rotates** - patterns become irrelevant
4. **House edge wins** - mathematics guarantees casino profit
5. **Overfitting is not prediction** - train performance ≠ real performance

---

## 🎲 Responsible Gambling

### Before You Use This Tool

⚠️ **Understand:**
- This is educational, not profitable
- The house always wins long-term
- No system beats the math
- Patterns in data ≠ predictive power

⚠️ **Remember:**
- Only gamble what you can afford to lose
- Set strict loss limits
- Never chase losses
- Seek help if needed

### Help Resources
- **NCPG**: 1-800-522-4700 (US)
- **Gamblers Anonymous**: https://www.gamblersanonymous.org/
- **GamCare**: https://www.gamcare.org.uk/ (UK)

---

## 📦 Installation Summary

### GUI Tool
```bash
pip install -r requirements.txt
python duckdice_gui.py
```

### CLI Tool
```bash
pip install -r requirements.txt
python duckdice.py --api-key KEY user-info
```

### RNG Analysis
```bash
cd rng_analysis
pip install -r requirements_analysis.txt
python main_analysis.py
```

---

## 🏆 What Makes This Special

### Comprehensive
- ✅ Complete API implementation
- ✅ Multiple analysis techniques
- ✅ Professional code quality
- ✅ Extensive documentation

### Educational
- ✅ Explains why attacks fail
- ✅ Teaches ML/DL concepts
- ✅ Promotes responsible gambling
- ✅ Cryptography education

### Professional
- ✅ Clean code structure
- ✅ Error handling
- ✅ Unit tests
- ✅ Visualization tools
- ✅ CLI interface

---

## 🚀 Quick Commands

```bash
# GUI: Launch interface
python duckdice_gui.py

# CLI: Check balance
python duckdice.py --api-key KEY user-info

# CLI: Place bet
python duckdice.py --api-key KEY dice --symbol XLM --amount 0.1 --chance 50 --high --faucet

# Analysis: Full run
cd rng_analysis && python main_analysis.py

# Analysis: Quick run
cd rng_analysis && python main_analysis.py --skip-dl --skip-viz

# Analysis: Statistical only
cd rng_analysis && python pattern_analyzer.py
```

---

**Built with ❤️ for education, not exploitation.**

**Remember: The house always wins. Gamble responsibly. 🎲**
