# Inventory Reorder Prediction System

A production-ready **FastAPI** application designed for intelligent inventory replenishment and stockout prevention, structured around a **4-stage pipeline**:

```
[ Stage 1: Stock Data ] ──> [ Stage 2: Consumption Data ] ──> [ Stage 3: Forecasting ] ──> [ Stage 4: Reorder Recommendations ]
```

---

## The 4 Pipeline Stages

### 1. Stage 1: Stock Data Management
- **Master Data**: Manages SKUs, product names, categories, on-hand stock, lead times (days), unit costs, ordering fixed costs ($S$), and annual holding rates ($H$).
- **Stock Thresholds**: Minimum and maximum warehouse stock constraints.
- **Stock Adjustments**: Real-time logging of positive (restocks, returns) or negative (breakage, shrinkage) inventory movements.
- **Batch CSV Import**: Ingest existing inventory catalogs directly from spreadsheets or ERP exports.

### 2. Stage 2: Consumption Data & Demand Analytics
- **Transaction Ingestion**: Logs individual retail, e-commerce, or B2B customer sales.
- **Continuous Daily Series**: Fills gap days with zero demand to construct true chronological series.
- **Statistical Demand Metrics**:
  - Average Daily Demand ($\bar{d}$)
  - Demand Standard Deviation ($\sigma_d$)
  - Volatility Index / Coefficient of Variation ($CV = \sigma_d / \bar{d}$)

### 3. Stage 3: Demand Forecasting Engine
- **Supported Algorithms**:
  - **Simple Moving Average (SMA)**: Window-based average for steady items.
  - **Weighted Moving Average (WMA)**: Prioritizes recent momentum.
  - **Single Exponential Smoothing (SES)**: Continuous smoothing with configurable $\alpha$.
  - **Linear Trend Projection (OLS)**: Handles trend-driven growing or declining items.
- **Auto Best-Fit Selection**: Automatically validates all candidate models against historical hold-out data and selects the model with the lowest **Mean Absolute Error (MAE)**.
- **Prediction Intervals**: Computes 95% upper and lower confidence bands for demand uncertainty.

### 4. Stage 4: Reorder Recommendation Engine
- **Lead Time Demand (LTD)**:
  $$\text{LTD} = \bar{d}_{\text{forecast}} \times \text{Lead Time (days)}$$
- **Dynamic Safety Stock (SS)**:
  $$\text{SS} = \lceil Z \times \sigma_d \times \sqrt{\text{Lead Time}} \rceil$$
  *(Supports configurable service level targets: 90%, 95%, 98%, 99%)*
- **Reorder Point (ROP)**:
  $$\text{ROP} = \lceil \text{LTD} + \text{SS} \rceil$$
- **Economic Order Quantity (EOQ)**:
  $$\text{EOQ} = \sqrt{\frac{2 \times D_{\text{annual}} \times S}{H}}$$
- **Urgency Risk Classification**:
  - `CRITICAL`: Current stock $\le$ Safety Stock (Stockout imminent).
  - `REORDER_NOW`: Current stock $\le$ Reorder Point (ROP).
  - `REORDER_SOON`: Current stock within 15% buffer of ROP.
  - `HEALTHY`: Stock levels adequate and balanced.
  - `OVERSTOCK`: Current stock $>$ Max Stock Level.
- **Actionable Order Output**: Suggested purchase quantities and total expected capital investment ($).

---

## Quick Start Guide

### 1. Activate Environment & Install Dependencies
```bash
cd inventory_reorder_system
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Seed Sample Database (Optional)
The application auto-seeds sample retail and electronics items upon initial startup, or you can seed manually:
```bash
python -m data.seed_data
```

### 3. Start the FastAPI Server
```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- **Interactive UI Dashboard**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Interactive Swagger API Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## Running Automated Tests

Run the full pytest suite:
```bash
.venv\Scripts\pytest -v
```

---

## API Endpoints Summary

| Stage | Method | Endpoint | Description |
|---|---|---|---|
| **Stage 1** | `GET` | `/api/v1/stock/items` | List inventory items with filters |
| **Stage 1** | `POST` | `/api/v1/stock/items` | Add new item / SKU |
| **Stage 1** | `POST` | `/api/v1/stock/items/{id}/adjust` | Record stock adjustment (+/-) |
| **Stage 1** | `GET` | `/api/v1/stock/overview` | Health and valuation overview |
| **Stage 1** | `POST` | `/api/v1/stock/upload-csv` | Bulk import items CSV |
| **Stage 2** | `POST` | `/api/v1/consumption/items/{id}` | Log individual sale/consumption |
| **Stage 2** | `POST` | `/api/v1/consumption/bulk` | Bulk log consumption records |
| **Stage 2** | `GET` | `/api/v1/consumption/items/{id}/metrics` | Compute $\bar{d}$, $\sigma_d$, and CV |
| **Stage 2** | `POST` | `/api/v1/consumption/upload-csv` | Bulk import historical sales CSV |
| **Stage 3** | `POST` | `/api/v1/forecast/items/{id}` | Generate demand forecast & confidence bands |
| **Stage 3** | `GET` | `/api/v1/forecast/models` | List available models & descriptions |
| **Stage 4** | `POST` | `/api/v1/recommendations/items/{id}` | Calculate ROP, EOQ & Urgency for item |
| **Stage 4** | `GET` | `/api/v1/recommendations/critical` | Filter all urgent reorder items |
| **Pipeline** | `POST` | `/api/v1/pipeline/run` | Execute 4-stage pipeline across all items |
