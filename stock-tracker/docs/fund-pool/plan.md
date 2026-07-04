# 資金池功能實作計畫

**日期**: 2026-07-04  
**狀態**: 待確認  
**分支**: feature/fund-pool

---

## 1. 需求概述

在現有個股交易帳本之上，新增資金管理層級，追蹤：
- 初始資金投入
- 入金/出金記錄
- 資金成長率（紅正/綠負，亞洲慣例）
- 定期報告（每季/半年/年度）

**核心問題**: 長期下來無法知道資金到底有沒有在投資中成長。

---

## 2. 架構設計

```
┌─────────────────────────────────────┐
│           資金池 (FundPool)            │
│  初始資金 + 入金 - 出金 = 淨投入      │
│  即時總值 = 個股市值總和 + 現金餘額    │
│  成長率 = (總值 / 淨投入 - 1) × 100%  │
├─────────────────────────────────────┤
│      ↓ 讀取現有個股資料自動計算 ↓       │
│  個股1 │ 個股2 │ 個股3 │ ...          │
│  (既有 Portfolio + StockState)        │
└─────────────────────────────────────┘
```

**現金餘額自動推導**（不需手動輸入每筆買賣）：
```
現金 = 淨投入 - 所有買入成本 + 所有賣出淨收入 + 所有股利收入
```
從 Portfolio 各股的 history 自動加總。

---

## 3. 資料模型

### 3.1 新增檔案: `core/fund_pool.py`

```python
from dataclasses import dataclass, field

@dataclass
class FundTransaction:
    date: str              # YYYY-MM-DD
    type: str              # "deposit" | "withdraw" | "initial"
    amount: float
    remark: str = ""

@dataclass
class FundSnapshot:
    date: str              # YYYY-MM-DD
    total_value: float     # 當時總值（市值+現金）
    total_deposits: float  # 累計淨投入
    growth_rate: float     # 成長率 %
    cash_balance: float    # 現金餘額
    period_label: str = "" # "2026-Q1", "2026-H1", "2026-年度"

@dataclass
class FundPool:
    initial_capital: float = 0.0
    transactions: list[FundTransaction] = field(default_factory=list)
    snapshots: list[FundSnapshot] = field(default_factory=list)
    
    def calculate_cash_balance(self, portfolio) -> float:
        """從 Portfolio 自動推導現金餘額"""
        total_deposits = self.initial_capital + sum(
            t.amount for t in self.transactions if t.type == "deposit"
        )
        total_withdrawals = sum(
            t.amount for t in self.transactions if t.type == "withdraw"
        )
        
        # 從 Portfolio 計算
        total_buy_cost = 0.0
        total_sell_proceeds = 0.0
        total_dividends = 0.0
        
        for code, state in portfolio.stocks.items():
            for tx in state.history:
                if tx.action == "buy":
                    total_buy_cost += tx.total_amount + tx.fee
                elif tx.action == "sell":
                    total_sell_proceeds += tx.total_amount - tx.tax
                elif tx.action == "dividend":
                    total_dividends += tx.dividend_total
        
        return (total_deposits - total_withdrawals 
                - total_buy_cost + total_sell_proceeds + total_dividends)
    
    def get_current_value(self, portfolio, prices: dict) -> float:
        """目前總值 = 現金 + 個股市值總和"""
        cash = self.calculate_cash_balance(portfolio)
        portfolio_value = sum(
            (prices.get(code, [None])[0] or 0) * state.shares
            for code, state in portfolio.stocks.items()
        )
        return cash + portfolio_value
    
    def get_growth_rate(self, portfolio, prices: dict) -> float:
        """成長率 = (總值 / 淨投入 - 1) × 100%"""
        net_invested = self.initial_capital + sum(
            t.amount for t in self.transactions if t.type == "deposit"
        ) - sum(
            t.amount for t in self.transactions if t.type == "withdraw"
        )
        if net_invested <= 0:
            return 0.0
        total_value = self.get_current_value(portfolio, prices)
        return (total_value / net_invested - 1) * 100
    
    def to_dict(self):
        return {
            "initial_capital": self.initial_capital,
            "transactions": [
                {"date": t.date, "type": t.type, "amount": t.amount, "remark": t.remark}
                for t in self.transactions
            ],
            "snapshots": [
                {
                    "date": s.date,
                    "total_value": s.total_value,
                    "total_deposits": s.total_deposits,
                    "growth_rate": s.growth_rate,
                    "cash_balance": s.cash_balance,
                    "period_label": s.period_label,
                }
                for s in self.snapshots
            ],
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        pool = cls(initial_capital=data.get("initial_capital", 0.0))
        pool.transactions = [
            FundTransaction(
                date=t["date"], type=t["type"], 
                amount=t["amount"], remark=t.get("remark", "")
            )
            for t in data.get("transactions", [])
        ]
        pool.snapshots = [
            FundSnapshot(
                date=s["date"],
                total_value=s["total_value"],
                total_deposits=s["total_deposits"],
                growth_rate=s["growth_rate"],
                cash_balance=s["cash_balance"],
                period_label=s.get("period_label", ""),
            )
            for s in data.get("snapshots", [])
        ]
        return pool
```

---

## 4. 資料持久化

### 4.1 修改: `data/store.py`

新增函數：

```python
def save_fund_pool(fund_pool, path):
    """儲存資金池到 data/fund_pool.json"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(fund_pool.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

def load_fund_pool(path):
    """載入資金池資料"""
    from core.fund_pool import FundPool
    p = Path(path)
    if not p.exists():
        return FundPool()
    data = json.loads(p.read_text(encoding="utf-8"))
    if not data:
        return FundPool()
    return FundPool.from_dict(data)
```

---

## 5. API 端點

### 5.1 修改: `web/api.py`

新增 endpoints：

```python
# 資金池總覽（含自動計算）
@api.route('/api/fund-pool')
def get_fund_pool():
    fund_pool = load_fund_pool(str(DATA_DIR / "fund_pool.json"))
    
    # 計算現金餘額
    cash_balance = fund_pool.calculate_cash_balance(portfolio)
    
    # 計算個股市值
    portfolio_value = 0.0
    for code in portfolio.stock_codes:
        price, _ = _get_cached_price(code)
        if price:
            state = portfolio.get_state(code)
            portfolio_value += price * state.shares
    
    total_value = cash_balance + portfolio_value
    net_invested = (fund_pool.initial_capital 
                   + sum(t.amount for t in fund_pool.transactions if t.type == "deposit")
                   - sum(t.amount for t in fund_pool.transactions if t.type == "withdraw"))
    
    growth_amount = total_value - net_invested
    growth_rate = (growth_amount / net_invested * 100) if net_invested > 0 else 0.0
    
    return jsonify({
        "initial_capital": fund_pool.initial_capital,
        "cash_balance": round(cash_balance, 2),
        "portfolio_value": round(portfolio_value, 2),
        "total_value": round(total_value, 2),
        "net_invested": round(net_invested, 2),
        "growth_amount": round(growth_amount, 2),
        "growth_rate": round(growth_rate, 2),
        "transactions": [
            {"date": t.date, "type": t.type, "amount": t.amount, "remark": t.remark}
            for t in fund_pool.transactions
        ],
        "snapshots": [
            {
                "date": s.date,
                "total_value": s.total_value,
                "total_deposits": s.total_deposits,
                "growth_rate": s.growth_rate,
                "cash_balance": s.cash_balance,
                "period_label": s.period_label,
            }
            for s in fund_pool.snapshots
        ],
    })

# 入金
@api.route('/api/fund-pool/deposit', methods=['POST'])
def fund_pool_deposit():
    from core.fund_pool import FundTransaction, FundPool
    data = request.get_json()
    try:
        amount = float(data['amount'])
        date_str = data.get('date', '')
        remark = data.get('remark', '')
    except (KeyError, ValueError):
        return jsonify({'error': '請輸入有效金額'}), 400
    
    fund_pool = load_fund_pool(str(DATA_DIR / "fund_pool.json"))
    tx = FundTransaction(date=date_str, type="deposit", amount=amount, remark=remark)
    fund_pool.transactions.append(tx)
    save_fund_pool(fund_pool, str(DATA_DIR / "fund_pool.json"))
    return jsonify({'message': f'已入金 ${amount:,.0f}'})

# 出金
@api.route('/api/fund-pool/withdraw', methods=['POST'])
def fund_pool_withdraw():
    from core.fund_pool import FundTransaction
    data = request.get_json()
    try:
        amount = float(data['amount'])
        date_str = data.get('date', '')
        remark = data.get('remark', '')
    except (KeyError, ValueError):
        return jsonify({'error': '請輸入有效金額'}), 400
    
    fund_pool = load_fund_pool(str(DATA_DIR / "fund_pool.json"))
    tx = FundTransaction(date=date_str, type="withdraw", amount=amount, remark=remark)
    fund_pool.transactions.append(tx)
    save_fund_pool(fund_pool, str(DATA_DIR / "fund_pool.json"))
    return jsonify({'message': f'已出金 ${amount:,.0f}'})

# 產生報告
@api.route('/api/fund-pool/snapshot', methods=['POST'])
def fund_pool_snapshot():
    from core.fund_pool import FundSnapshot
    data = request.get_json()
    period_label = data.get('period_label', '')
    
    fund_pool = load_fund_pool(str(DATA_DIR / "fund_pool.json"))
    
    # 計算當前狀態
    cash_balance = fund_pool.calculate_cash_balance(portfolio)
    portfolio_value = 0.0
    for code in portfolio.stock_codes:
        price, _ = _get_cached_price(code)
        if price:
            state = portfolio.get_state(code)
            portfolio_value += price * state.shares
    
    total_value = cash_balance + portfolio_value
    net_invested = (fund_pool.initial_capital 
                   + sum(t.amount for t in fund_pool.transactions if t.type == "deposit")
                   - sum(t.amount for t in fund_pool.transactions if t.type == "withdraw"))
    
    growth_rate = ((total_value / net_invested - 1) * 100) if net_invested > 0 else 0.0
    
    snapshot = FundSnapshot(
        date=datetime.now().strftime('%Y-%m-%d'),
        total_value=round(total_value, 2),
        total_deposits=round(net_invested, 2),
        growth_rate=round(growth_rate, 2),
        cash_balance=round(cash_balance, 2),
        period_label=period_label,
    )
    fund_pool.snapshots.append(snapshot)
    save_fund_pool(fund_pool, str(DATA_DIR / "fund_pool.json"))
    
    return jsonify({
        'message': f'已產生報告: {period_label}',
        'snapshot': {
            'date': snapshot.date,
            'total_value': snapshot.total_value,
            'total_deposits': snapshot.total_deposits,
            'growth_rate': snapshot.growth_rate,
            'cash_balance': snapshot.cash_balance,
            'period_label': snapshot.period_label,
        }
    })

# 匯出資金池
@api.route('/api/fund-pool/export')
def export_fund_pool():
    from flask import make_response
    import csv as csv_module
    import io
    
    fund_pool = load_fund_pool(str(DATA_DIR / "fund_pool.json"))
    
    output = io.StringIO()
    w = csv_module.writer(output)
    w.writerow(['日期', '類型', '金額', '備註'])
    
    type_map = {'deposit': '入金', 'withdraw': '出金', 'initial': '初始資金'}
    
    # 初始資金
    if fund_pool.initial_capital > 0:
        w.writerow(['', '初始資金', fund_pool.initial_capital, ''])
    
    # 交易記錄
    for t in fund_pool.transactions:
        w.writerow([t.date, type_map.get(t.type, t.type), t.amount, t.remark])
    
    # 分隔線
    w.writerow(['---', '定期報告', '---', '---'])
    
    # 快照
    for s in fund_pool.snapshots:
        w.writerow([s.date, f'報告-{s.period_label}', s.total_value, 
                   f'成長率:{s.growth_rate:.2f}%'])
    
    csv_content = output.getvalue()
    today = datetime.now().strftime('%Y-%m-%d')
    filename = f'StockTracker_fundpool_{today}.csv'
    
    response = make_response(csv_content)
    response.headers['Content-Type'] = 'text/csv; charset=utf-8-sig'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

# 同步匯入（交易記錄 + 資金池）
@api.route('/api/import/all', methods=['POST'])
def import_all():
    if 'trades' not in request.files or 'fundpool' not in request.files:
        return jsonify({'error': '缺少檔案，請同時提供交易記錄與資金池'}), 400
    
    trades_file = request.files['trades']
    fund_file = request.files['fundpool']
    
    if not trades_file.filename.endswith('.csv') or not fund_file.filename.endswith('.csv'):
        return jsonify({'error': '僅支援 CSV 格式'}), 400
    
    try:
        # 匯入交易記錄
        global portfolio
        trades_path = str(DATA_DIR / '_upload_trades_temp.csv')
        trades_file.save(trades_path)
        portfolio, n_trades = parse_trades_csv(trades_path, portfolio, cfg)
        Path(trades_path).unlink(missing_ok=True)
        
        # 匯入資金池
        fund_path = str(DATA_DIR / '_upload_fund_temp.csv')
        fund_file.save(fund_path)
        fund_pool = load_fund_pool(str(DATA_DIR / "fund_pool.json"))
        fund_pool = parse_fund_pool_csv(fund_path, fund_pool)
        save_fund_pool(fund_pool, str(DATA_DIR / "fund_pool.json"))
        Path(fund_path).unlink(missing_ok=True)
        
        _save()
        return jsonify({
            'message': f'已匯入 {n_trades} 筆交易 + 資金池記錄',
            'trades_count': n_trades,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def parse_fund_pool_csv(csv_path, fund_pool):
    """解析資金池 CSV"""
    from core.fund_pool import FundTransaction
    import csv
    
    with open(csv_path, encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader, None)
        
        for row in reader:
            if len(row) < 3:
                continue
            date_str, type_str, amount_str = row[0], row[1], row[2]
            remark = row[3] if len(row) > 3 else ''
            
            # 跳過分隔線
            if date_str.startswith('---'):
                continue
            
            try:
                amount = float(amount_str)
            except ValueError:
                continue
            
            type_map = {'入金': 'deposit', '出金': 'withdraw', '初始資金': 'initial'}
            tx_type = type_map.get(type_str, type_str)
            
            if tx_type == 'initial':
                fund_pool.initial_capital = amount
            else:
                tx = FundTransaction(date=date_str, type=tx_type, amount=amount, remark=remark)
                fund_pool.transactions.append(tx)
    
    return fund_pool
```

---

## 6. 前端視覺

### 6.1 修改: `web/templates/base.html`

新增導航按鈕：

```html
<button class="tab-btn" data-tab="fund_pool">
  <span class="icon">&#x1F4B0;</span>資金池
</button>
```

新增 content div：

```html
<div id="tab-fund_pool" class="tab-content">{% block fund_pool %}{% endblock %}</div>
```

### 6.2 修改: `web/templates/dashboard.html`

在總覽頁面新增資金池摘要區塊（放在現有 card-grid 下方）：

```html
{% block dashboard %}
<div class="page-title">持有總覽</div>

<!-- 現有摘要卡片 -->
<div id="dashboard-cards" class="card-grid">...</div>

<!-- 新增：資金池摘要區塊 -->
<div class="fund-pool-summary" style="margin-top:20px">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
    <div style="font-size:16px;font-weight:600;color:var(--gray-800)">💰 資金池總覽</div>
    <button class="btn btn-sm btn-gray" onclick="switchTab('fund_pool')">詳細 →</button>
  </div>
  <div class="card-grid-4">
    <div class="card">
      <div class="card-label">初始資金</div>
      <div class="card-value small" id="fp-initial">$0</div>
    </div>
    <div class="card">
      <div class="card-label">目前總值</div>
      <div class="card-value small" id="fp-total">$0</div>
    </div>
    <div class="card">
      <div class="card-label">總成長</div>
      <div class="card-value small" id="fp-growth">$0</div>
    </div>
    <div class="card">
      <div class="card-label">成長率</div>
      <div class="card-value small" id="fp-rate">0%</div>
    </div>
  </div>
  <!-- 迷你圖表 -->
  <div style="margin-top:12px;padding:12px;background:var(--bg-card);border-radius:8px">
    <canvas id="fp-mini-chart" height="80"></canvas>
  </div>
</div>

<!-- 後續內容不變 -->
...
{% endblock %}
```

### 6.3 新增: `web/templates/fund_pool.html`

```html
{% extends "base.html" %}
{% block fund_pool %}
<div class="page-title">💰 資金池管理</div>

<!-- 完整摘要卡片 -->
<div class="card-grid-4">
  <div class="card">
    <div class="card-label">初始資金</div>
    <div class="card-value" id="fp-initial-full">$0</div>
  </div>
  <div class="card">
    <div class="card-label">淨投入</div>
    <div class="card-value" id="fp-net-invested">$0</div>
  </div>
  <div class="card">
    <div class="card-label">目前總值</div>
    <div class="card-value" id="fp-total-full">$0</div>
  </div>
  <div class="card">
    <div class="card-label">成長率</div>
    <div class="card-value" id="fp-rate-full">0%</div>
  </div>
</div>

<!-- 操作按鈕 -->
<div class="action-bar">
  <button class="btn btn-success" onclick="showDepositDialog()">💵 入金</button>
  <button class="btn btn-warning" onclick="showWithdrawDialog()">💸 出金</button>
  <button class="btn btn-primary" onclick="showSnapshotDialog()">📊 產生報告</button>
</div>

<!-- 資金異動表 -->
<div class="section-card">
  <div class="section-card-title">資金異動記錄</div>
  <div class="table-wrap">
    <table class="data-table">
      <thead>
        <tr><th>日期</th><th>類型</th><th class="right">金額</th><th>備註</th><th></th></tr>
      </thead>
      <tbody id="fp-transactions"></tbody>
    </table>
  </div>
</div>

<!-- 定期報告區 -->
<div class="section-card">
  <div class="section-card-title">定期報告</div>
  <div class="table-wrap">
    <table class="data-table">
      <thead>
        <tr><th>期間</th><th>日期</th><th class="right">總值</th><th class="right">淨投入</th><th class="right">成長率</th></tr>
      </thead>
      <tbody id="fp-snapshots"></tbody>
    </table>
  </div>
</div>
{% endblock %}
```

### 6.4 修改: `web/static/app.js`

新增資金池相關函數：

```javascript
// ====== Fund Pool ======
async function loadFundPool() {
  const data = await api('/api/fund-pool');
  if (!data) return;
  
  // 更新總覽卡片
  document.getElementById('fp-initial').textContent = '$' + fmt(data.initial_capital);
  document.getElementById('fp-total').textContent = '$' + fmt(data.total_value);
  
  const growthEl = document.getElementById('fp-growth');
  growthEl.textContent = '$' + fmtPL(data.growth_amount);
  growthEl.className = 'card-value small ' + getGrowthColor(data.growth_rate);
  
  const rateEl = document.getElementById('fp-rate');
  rateEl.textContent = fmtPL(data.growth_rate) + '%';
  rateEl.className = 'card-value small ' + getGrowthColor(data.growth_rate);
  
  // 更新完整頁面卡片
  if (document.getElementById('fp-initial-full')) {
    document.getElementById('fp-initial-full').textContent = '$' + fmt(data.initial_capital);
    document.getElementById('fp-net-invested').textContent = '$' + fmt(data.net_invested);
    document.getElementById('fp-total-full').textContent = '$' + fmt(data.total_value);
    
    const rateFullEl = document.getElementById('fp-rate-full');
    rateFullEl.textContent = fmtPL(data.growth_rate) + '%';
    rateFullEl.className = 'card-value ' + getGrowthColor(data.growth_rate);
  }
  
  // 渲染交易記錄
  renderFundTransactions(data.transactions);
  
  // 渲染報告
  renderFundSnapshots(data.snapshots);
  
  // 渲染迷你圖表
  renderFundMiniChart(data.snapshots);
}

function getGrowthColor(rate) {
  // 亞洲慣例：紅=漲，綠=跌
  return rate >= 0 ? 'positive' : 'negative';
}

function renderFundTransactions(transactions) {
  const tbody = document.getElementById('fp-transactions');
  if (!tbody) return;
  
  if (!transactions || transactions.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--gray-400)">尚無記錄</td></tr>';
    return;
  }
  
  const typeMap = { deposit: '入金', withdraw: '出金', initial: '初始資金' };
  
  tbody.innerHTML = transactions.map(t => `
    <tr>
      <td>${t.date}</td>
      <td><span class="badge ${t.type === 'deposit' ? 'badge-buy' : 'badge-sell'}">${typeMap[t.type] || t.type}</span></td>
      <td class="right">$${fmt(t.amount)}</td>
      <td style="font-size:12px;color:var(--gray-500)">${t.remark || ''}</td>
      <td></td>
    </tr>
  `).join('');
}

function renderFundSnapshots(snapshots) {
  const tbody = document.getElementById('fp-snapshots');
  if (!tbody) return;
  
  if (!snapshots || snapshots.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--gray-400)">尚無報告</td></tr>';
    return;
  }
  
  tbody.innerHTML = snapshots.map(s => `
    <tr>
      <td>${s.period_label}</td>
      <td>${s.date}</td>
      <td class="right">$${fmt(s.total_value)}</td>
      <td class="right">$${fmt(s.total_deposits)}</td>
      <td class="right ${getGrowthColor(s.growth_rate)}">${fmtPL(s.growth_rate)}%</td>
    </tr>
  `).join('');
}

function renderFundMiniChart(snapshots) {
  const canvas = document.getElementById('fp-mini-chart');
  if (!canvas || !snapshots || snapshots.length === 0) return;
  
  if (typeof Chart === 'undefined') return;
  
  const ctx = canvas.getContext('2d');
  if (window._fpMiniChart) window._fpMiniChart.destroy();
  
  const labels = snapshots.map(s => s.period_label || s.date);
  const data = snapshots.map(s => s.growth_rate);
  
  window._fpMiniChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: '成長率 %',
        data: data,
        borderColor: '#2563eb',
        backgroundColor: 'rgba(37, 99, 235, 0.1)',
        borderWidth: 2,
        pointRadius: 3,
        fill: true,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => ctx.parsed.y.toFixed(2) + '%'
          }
        }
      },
      scales: {
        x: { display: true, ticks: { font: { size: 10 } } },
        y: { 
          display: true, 
          ticks: { 
            callback: v => v.toFixed(1) + '%',
            font: { size: 10 }
          } 
        }
      }
    }
  });
}

function showDepositDialog() {
  showModal(`
    <h3>💵 入金</h3>
    <div class="form-grid">
      <div class="form-label">日期</div><input class="form-input" id="fp-date" type="date" value="${today()}">
      <div class="form-label">金額</div><input class="form-input" id="fp-amount" type="number" step="0.01">
      <div class="form-label">備註</div><input class="form-input" id="fp-remark" type="text">
    </div>
    <div class="btn-group" style="margin-top:16px">
      <button class="btn btn-primary" onclick="submitDeposit()">確定</button>
      <button class="btn btn-gray" onclick="hideModal()">取消</button>
    </div>
  `);
}

async function submitDeposit() {
  const date = document.getElementById('fp-date').value;
  const amount = parseFloat(document.getElementById('fp-amount').value);
  const remark = document.getElementById('fp-remark').value;
  
  if (!amount || amount <= 0) {
    showToast('請輸入有效金額', 'error');
    return;
  }
  
  const result = await api('/api/fund-pool/deposit', {
    method: 'POST',
    body: JSON.stringify({ date, amount, remark })
  });
  
  if (result) {
    hideModal();
    showToast(result.message, 'success');
    loadFundPool();
    loadDashboard();
  }
}

function showWithdrawDialog() {
  showModal(`
    <h3>💸 出金</h3>
    <div class="form-grid">
      <div class="form-label">日期</div><input class="form-input" id="fp-date" type="date" value="${today()}">
      <div class="form-label">金額</div><input class="form-input" id="fp-amount" type="number" step="0.01">
      <div class="form-label">備註</div><input class="form-input" id="fp-remark" type="text">
    </div>
    <div class="btn-group" style="margin-top:16px">
      <button class="btn btn-primary" onclick="submitWithdraw()">確定</button>
      <button class="btn btn-gray" onclick="hideModal()">取消</button>
    </div>
  `);
}

async function submitWithdraw() {
  const date = document.getElementById('fp-date').value;
  const amount = parseFloat(document.getElementById('fp-amount').value);
  const remark = document.getElementById('fp-remark').value;
  
  if (!amount || amount <= 0) {
    showToast('請輸入有效金額', 'error');
    return;
  }
  
  const result = await api('/api/fund-pool/withdraw', {
    method: 'POST',
    body: JSON.stringify({ date, amount, remark })
  });
  
  if (result) {
    hideModal();
    showToast(result.message, 'success');
    loadFundPool();
    loadDashboard();
  }
}

function showSnapshotDialog() {
  showModal(`
    <h3>📊 產生定期報告</h3>
    <div class="form-grid">
      <div class="form-label">期間標籤</div>
      <select class="form-input" id="fp-period">
        <option value="2026-Q1">2026-Q1</option>
        <option value="2026-Q2">2026-Q2</option>
        <option value="2026-Q3">2026-Q3</option>
        <option value="2026-Q4">2026-Q4</option>
        <option value="2026-H1">2026-H1</option>
        <option value="2026-H2">2026-H2</option>
        <option value="2026-年度">2026-年度</option>
      </select>
    </div>
    <div class="btn-group" style="margin-top:16px">
      <button class="btn btn-primary" onclick="submitSnapshot()">產生</button>
      <button class="btn btn-gray" onclick="hideModal()">取消</button>
    </div>
  `);
}

async function submitSnapshot() {
  const period_label = document.getElementById('fp-period').value;
  
  const result = await api('/api/fund-pool/snapshot', {
    method: 'POST',
    body: JSON.stringify({ period_label })
  });
  
  if (result) {
    hideModal();
    showToast(result.message, 'success');
    loadFundPool();
  }
}

// 修改 switchTab 函數
function switchTab(tab) {
  // ... 現有邏輯 ...
  if (tab === 'fund_pool') loadFundPool();
}

// 修改 loadDashboard 函數，加入資金池載入
async function loadDashboard() {
  // ... 現有邏輯 ...
  loadFundPool();  // 載入資金池摘要
}
```

### 6.5 修改: `web/static/style.css`

新增樣式：

```css
/* 資金池摘要 */
.fund-pool-summary {
  margin-top: 20px;
  padding: 16px;
  background: var(--bg-card);
  border-radius: 12px;
  border: 1px solid var(--border);
}

.card-grid-4 {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

/* 成長顏色 - 亞洲慣例 */
.card-value.positive {
  color: #dc2626;  /* 紅色 = 正成長 */
}

.card-value.negative {
  color: #16a34a;  /* 綠色 = 負成長 */
}
```

---

## 7. 匯入/匯出功能

### 7.1 修改: `web/static/app.js`

```javascript
// 修改匯出功能（同步兩筆）
async function exportAll() {
  // 1. 匯出交易記錄
  const tradesRes = await fetch('/api/export/csv');
  const tradesBlob = await tradesRes.blob();
  const tradesUrl = URL.createObjectURL(tradesBlob);
  const tradesLink = document.createElement('a');
  tradesLink.href = tradesUrl;
  tradesLink.download = `StockTracker_trades_${today()}.csv`;
  document.body.appendChild(tradesLink);
  tradesLink.click();
  document.body.removeChild(tradesLink);
  
  // 2. 匯出資金池
  setTimeout(() => {
    const fundRes = await fetch('/api/fund-pool/export');
    const fundBlob = await fundRes.blob();
    const fundUrl = URL.createObjectURL(fundBlob);
    const fundLink = document.createElement('a');
    fundLink.href = fundUrl;
    fundLink.download = `StockTracker_fundpool_${today()}.csv`;
    document.body.appendChild(fundLink);
    fundLink.click();
    document.body.removeChild(fundLink);
  }, 500);
}

// 修改匯入功能（要求兩筆）
async function importAll() {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '.csv';
  input.multiple = true;
  
  input.onchange = async () => {
    const files = input.files;
    if (files.length !== 2) {
      showToast('請同時選擇交易記錄與資金池兩筆檔案', 'error');
      return;
    }
    
    const hasTrades = [...files].some(f => f.name.includes('trades'));
    const hasFund = [...files].some(f => f.name.includes('fundpool'));
    
    if (!hasTrades || !hasFund) {
      showToast('檔名不符，請使用系統匯出的檔案', 'error');
      return;
    }
    
    const formData = new FormData();
    formData.append('trades', files.find(f => f.name.includes('trades')));
    formData.append('fundpool', files.find(f => f.name.includes('fundpool')));
    
    const res = await fetch('/api/import/all', { method: 'POST', body: formData });
    const data = await res.json();
    if (res.ok) {
      showToast('匯入成功', 'success');
      loadDashboard();
      loadFundPool();
    } else {
      showToast(data.error || '匯入失敗', 'error');
    }
  };
  
  input.click();
}
```

---

## 8. 實作順序

1. **Phase 1**: 資料模型 + 持久化
   - `core/fund_pool.py`
   - `data/store.py` 新增函數

2. **Phase 2**: API 端點
   - `web/api.py` 新增 endpoints

3. **Phase 3**: 前端視覺
   - `base.html` 新增導航
   - `dashboard.html` 新增摘要區塊
   - `fund_pool.html` 新增完整頁面
   - `app.js` 新增函數
   - `style.css` 新增樣式

4. **Phase 4**: 匯入/匯出
   - API endpoints
   - 前端函數

5. **Phase 5**: 測試 + 調整

---

## 9. 待確認事項

- [ ] 視覺呈現組合方案（摘要卡片 + 迷你圖表）是否 OK
- [ ] 匯出檔名格式：`StockTracker_trades_YYYY-MM-DD.csv` + `StockTracker_fundpool_YYYY-MM-DD.csv`
- [ ] 匯入時是否強制要求兩筆檔案同時存在

---

**狀態**: 待確認後開始實作
