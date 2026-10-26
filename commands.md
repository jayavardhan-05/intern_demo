# Execution Commands

### 1. Smoke Test (Offline Mode)
Runs the quick smoke test against pre-supplied offline extractions to verify logic against `data/smoke/expected.json`:

```powershell
python main.py --payments data/smoke/payments.csv --shipments data/smoke/shipments.jsonl --complaints data/smoke/complaints.jsonl --extractions data/smoke/extractions.json --output smoke_result.json
```

---

### 2. Challenge Dataset (Offline Mode — Required)
Runs the full evaluation using the provided offline extractions (without calling an LLM API):

```powershell
python main.py --payments data/challenge/payments.csv --shipments data/challenge/shipments.jsonl --complaints data/challenge/complaints.jsonl --extractions data/challenge/extractions.json --output result_offline.json
```

---

### 3. Live LLM Mode (Sample Dataset)
Runs extraction dynamically via LLM API calls on the sample dataset (requires your API key set in `.env` or passed via flag):

```powershell
python main.py --payments data/sample/payments.csv --shipments data/sample/shipments.jsonl --complaints data/sample/complaints.jsonl --output result_live.json
```

---

### 4. Sample Dataset (Offline Mode)
If you want to test the sample dataset offline using `extractions.json`:

```powershell
python main.py --payments data/sample/payments.csv --shipments data/sample/shipments.jsonl --complaints data/sample/complaints.jsonl --extractions data/sample/extractions.json --output result_sample.json
```
