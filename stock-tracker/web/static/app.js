// ====== Tab Switching ======
function switchTab(tab) {
    const btn = document.querySelector(`.tab-btn[data-tab="${tab}"]`);
    if (!btn) return;
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + tab).classList.add('active');
    localStorage.setItem('activeTab', tab);
    if (tab === 'dashboard') loadDashboard();
    if (tab === 'fund_pool') loadFundPool();
    if (tab === 'stock') loadStockList();
    if (tab === 'etf') loadEtfList();
    if (tab === 'settings') loadConfig();
    if (tab === 'backtest') loadBacktest();
    if (tab === 'news') loadNews(1);
    if (tab === 'archived') loadArchived();
}

document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
});

// ====== Toast ======
function showToast(msg, type) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.className = 'toast ' + type + ' show';
    setTimeout(() => t.classList.remove('show'), 3000);
}

// ====== API Helper ======
async function api(path, opts) {
    try {
        const res = await fetch(path, { ...opts, headers: { 'Content-Type': 'application/json', ...(opts?.headers || {}) } });
        const data = await res.json();
        if (!res.ok) { showToast(data.error || '請求失敗', 'error'); return null; }
        return data;
    } catch (e) {
        showToast('網路錯誤: ' + e.message, 'error');
        return null;
    }
}

// ====== Dashboard ======
async function loadDashboard() {
    const data = await api('/api/portfolio');
    if (!data) return;

    document.getElementById('d-count').textContent = data.count;
    document.getElementById('d-investment-total').textContent = '$' + fmt(data.investment_total);
    const plEl = document.getElementById('d-pl');
    plEl.textContent = '$' + fmtPL(data.total_pl);
    plEl.className = 'card-value ' + (data.total_pl >= 0 ? 'positive' : 'negative');
    const roiEl = document.getElementById('d-roi');
    roiEl.textContent = fmtPL(data.total_roi) + '%';
    roiEl.className = 'card-value ' + (data.total_roi >= 0 ? 'positive' : 'negative');

    document.getElementById('d-zc').textContent = '已達成：' + data.zc_count + ' 檔 | 未達成：' + (data.count - data.zc_count) + ' 檔';

    const tbody = document.getElementById('d-table-body');
    tbody.innerHTML = '';
    for (const s of data.stocks) {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${s.code}${s.name ? '<br><span class="stock-name">' + s.name + '</span>' : ''}</td>
            <td><span class="badge ${s.type === 'ETF' ? 'badge-etf' : 'badge-stock'}">${s.type}</span></td>
            <td class="right">${fmt(s.shares)}</td>
            <td class="right">${fmt(s.avg_cost)}</td>
            <td class="right">${s.current_price ? fmt(s.current_price) : 'N/A'}</td>
            <td class="right">${fmt(s.market_value)}</td>
            <td class="right ${s.unrealized_pl >= 0 ? 'card-value positive' : 'card-value negative'}" style="font-size:13px">${fmtPL(s.unrealized_pl)}</td>
            <td class="right ${s.unrealized_pl_pct >= 0 ? 'card-value positive' : 'card-value negative'}" style="font-size:13px">${fmtPL(s.unrealized_pl_pct)}%</td>
            <td class="center" style="color:${s.is_zero_cost ? 'var(--success)' : 'inherit'}">${s.is_zero_cost ? 'O' : 'X'}</td>
        `;
        tbody.appendChild(tr);
    }

    renderPieChart(data.stocks);
    loadFundPoolSummary();
}

async function loadFundPoolSummary() {
    const data = await api('/api/fund-pool');
    if (!data) return;

    const summaryEl = document.getElementById('fund-pool-summary');
    if (summaryEl) summaryEl.style.display = 'block';

    document.getElementById('fp-initial-summary').textContent = '$' + fmt(data.initial_capital);
    document.getElementById('fp-total-summary').textContent = '$' + fmt(data.total_value);
    document.getElementById('fp-cash-summary').textContent = '$' + fmt(data.cash_balance);

    const rateEl = document.getElementById('fp-rate-summary');
    rateEl.textContent = fmtPL(data.growth_rate) + '%';
    rateEl.className = 'card-value small ' + getGrowthColor(data.growth_rate);
}

function renderPieChart(stocks) {
    const total = stocks.reduce((s, x) => s + x.market_value, 0);
    const pie = document.getElementById('pie-chart');
    const legend = document.getElementById('pie-legend');
    if (total === 0) {
        pie.style.background = '#e5e7eb';
        legend.innerHTML = '<span style="color:var(--gray-400)">無持股</span>';
        return;
    }
    const colors = ['#2563eb', '#16a34a', '#d97706', '#7c3aed', '#dc2626', '#0891b2', '#be123c', '#4f46e5'];
    let conic = '';
    let angle = 0;
    legend.innerHTML = '';
    stocks.forEach((s, i) => {
        const pct = s.market_value / total;
        const deg = pct * 360;
        const c = colors[i % colors.length];
        conic += `${c} ${angle}deg ${angle + deg}deg, `;
        angle += deg;
        const item = document.createElement('div');
        item.className = 'pie-legend-item';
        item.innerHTML = `<span class="legend-dot" style="background:${c}"></span> ${s.code} ${(pct * 100).toFixed(1)}%`;
        legend.appendChild(item);
    });
    pie.style.background = `conic-gradient(${conic.slice(0, -2)})`;
}

// ====== Stock / ETF List ======
async function loadStockList() {
    const data = await api('/api/portfolio');
    const combo = document.getElementById('s-combo');
    const prev = localStorage.getItem('selectedStock');
    combo.innerHTML = '<option value="">-- 選擇股票 --</option>';
    if (!data) return;
    for (const s of data.stocks.filter(x => x.type === '個股')) {
        const opt = document.createElement('option');
        opt.value = s.code; opt.textContent = s.code + (s.name ? ' - ' + s.name : '');
        if (s.code === prev) opt.selected = true;
        combo.appendChild(opt);
    }
    document.getElementById('s-detail').innerHTML = '';
    if (prev && [...combo.options].some(o => o.value === prev)) loadStockDetail();
}

async function loadEtfList() {
    const data = await api('/api/portfolio');
    const combo = document.getElementById('e-combo');
    const prev = localStorage.getItem('selectedEtf');
    combo.innerHTML = '<option value="">-- 選擇 ETF --</option>';
    if (!data) return;
    for (const s of data.stocks.filter(x => x.type === 'ETF')) {
        const opt = document.createElement('option');
        opt.value = s.code; opt.textContent = s.code + (s.name ? ' - ' + s.name : '');
        if (s.code === prev) opt.selected = true;
        combo.appendChild(opt);
    }
    document.getElementById('e-detail').innerHTML = '';
    if (prev && [...combo.options].some(o => o.value === prev)) loadEtfDetail();
}

async function loadStockDetail() {
    const code = document.getElementById('s-combo').value;
    if (!code) { document.getElementById('s-detail').innerHTML = ''; localStorage.removeItem('selectedStock'); return; }
    localStorage.setItem('selectedStock', code);
    await loadDetail(code, 's-detail');
}

async function loadEtfDetail() {
    const code = document.getElementById('e-combo').value;
    if (!code) { document.getElementById('e-detail').innerHTML = ''; localStorage.removeItem('selectedEtf'); return; }
    localStorage.setItem('selectedEtf', code);
    await loadDetail(code, 'e-detail');
}

async function loadDetail(code, containerId) {
    const data = await api('/api/portfolio/' + code);
    if (!data) return;
    const el = document.getElementById(containerId);
    el.innerHTML = `
        <div class="detail-title">${data.code} ${data.name ? '- ' + data.name : ''}</div>
        <div class="card-grid-6">
            <div class="card"><div class="card-label">股數</div><div class="card-value small">${fmt(data.shares)}</div></div>
            <div class="card"><div class="card-label">總成本</div><div class="card-value small">${fmt(data.total_cost)}</div></div>
            <div class="card"><div class="card-label">均價</div><div class="card-value small">${fmt(data.avg_cost)}</div></div>
            <div class="card"><div class="card-label">現價</div><div class="card-value small ${data.current_price ? (data.current_price >= data.avg_cost ? 'positive' : 'negative') : ''}">${data.current_price ? fmt(data.current_price) : 'N/A'}</div></div>
            <div class="card"><div class="card-label">市值</div><div class="card-value small">${fmt(data.market_value)}</div></div>
            <div class="card"><div class="card-label">未實現</div><div class="card-value small ${data.unrealized_pl >= 0 ? 'positive' : 'negative'}">${fmtPL(data.unrealized_pl)}</div></div>
        </div>
        <div class="action-bar">
            <button class="btn btn-primary" onclick="showTxnDialog('${code}','buy')">+ 買入</button>
            <button class="btn btn-danger" onclick="showTxnDialog('${code}','sell')">- 賣出</button>
            <button class="btn btn-success" onclick="showTxnDialog('${code}','dividend')">\$ 現金股利</button>
            <button class="btn btn-warning" onclick="showTxnDialog('${code}','stock_dividend')">~ 股票股利</button>
            <button class="btn btn-purple" onclick="showTxnDialog('${code}','dividend_reinvest')">&#x21BB; 再投資</button>
            <button class="btn btn-gray" onclick="deleteStock('${code}')">刪除此檔</button>
        </div>
        <div class="table-wrap">
            <table class="data-table">
                <thead><tr>
                    <th>日期</th><th>類型</th><th class="right">價格</th><th class="right">股數</th>
                    <th class="right">金額</th><th class="right">手續費</th><th class="right">稅</th><th>備註</th><th></th>
                </tr></thead>
                <tbody>
                    ${data.history.map((tx, i) => {
                        let badgeClass = 'badge-txn';
                        if (tx.action === '買入' || tx.action === '初始') badgeClass = 'badge-buy';
                        const canDelete = tx.action !== 'init';
                        return `<tr>
                            <td>${tx.date}</td>
                            <td><span class="${badgeClass}">${tx.action}</span></td>
                            <td class="right">${tx.price ? fmt(tx.price) : '-'}</td>
                            <td class="right">${tx.shares ? fmt(tx.shares) : '-'}</td>
                            <td class="right">${fmt(tx.total_amount)}</td>
                            <td class="right">${tx.fee ? fmt(tx.fee) : '-'}</td>
                            <td class="right">${tx.tax ? fmt(tx.tax) : '-'}</td>
                            <td style="font-size:12px;color:var(--gray-500);max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${tx.remark || ''}">${tx.remark || ''}</td>
                            <td>${canDelete ? `<button class="btn btn-danger btn-sm" onclick="deleteTransaction('${code}', ${i})">&#x2716;</button>` : ''}</td>
                        </tr>`;
                    }).join('')}
                </tbody>
            </table>
        </div>
    `;
}

// ====== Dialogs ======
function showModal(html) {
    document.getElementById('modal-content').innerHTML = html;
    document.getElementById('modal-overlay').classList.add('show');
}

function hideModal() {
    document.getElementById('modal-overlay').classList.remove('show');
}

function showHoldingDialog() {
    showModal(`
        <h3>&#x1F4C5; 新增初始持倉</h3>
        <div class="form-grid">
            <div class="form-label">股票代碼</div><input class="form-input" id="hd-code" type="text">
            <div class="form-label">股數</div><input class="form-input" id="hd-shares" type="number">
            <div class="form-label">總成本 (含手續費)</div><input class="form-input" id="hd-cost" type="number" step="0.01">
            <div class="form-label">日期</div><input class="form-input" id="hd-date" type="date" value="${today()}">
        </div>
        <div class="btn-group" style="margin-top:16px">
            <button class="btn btn-primary" onclick="submitHolding()">確定</button>
            <button class="btn btn-gray" onclick="hideModal()">取消</button>
        </div>
    `);
}

let _isSubmitting = false;

async function submitHolding() {
    if (_isSubmitting) return;
    _isSubmitting = true;
    try {
        const code = document.getElementById('hd-code').value.trim();
        const shares = parseInt(document.getElementById('hd-shares').value);
        const total_cost = parseFloat(document.getElementById('hd-cost').value);
        const date = document.getElementById('hd-date').value;
        if (!code || !shares || !total_cost) { showToast('請填寫所有欄位', 'error'); return; }
        const result = await api('/api/holdings', { method: 'POST', body: JSON.stringify({ code, shares, total_cost, date }) });
        if (result) { hideModal(); showToast(result.message, 'success'); loadDashboard(); loadStockList(); loadEtfList(); }
    } finally {
        _isSubmitting = false;
    }
}

function showTxnDialog(code, action) {
    const labels = { buy: '買入', sell: '賣出', dividend: '現金股利', stock_dividend: '股票股利', dividend_reinvest: '再投資' };
    let fields = '';
    let modeSwitch = '';

    if (action === 'buy') {
        modeSwitch = buildModeSwitch('buy-mode', '手續費', '總支出');
        fields = `
            <div class="form-label">日期</div><input class="form-input" id="tx-date" type="date" value="${today()}">
            <div class="form-label">價格</div><input class="form-input" id="tx-price" type="number" step="0.01">
            <div class="form-label">股數</div><input class="form-input" id="tx-shares" type="number">
            <div class="form-label" id="tx-buy-label">手續費</div><input class="form-input" id="tx-buy-fee" type="number" step="0.01" value="0">`;
    } else if (action === 'sell') {
        modeSwitch = buildModeSwitch('sell-mode', '明細', '總收入');
        fields = `
            <div class="form-label">日期</div><input class="form-input" id="tx-date" type="date" value="${today()}">
            <div class="form-label">價格</div><input class="form-input" id="tx-price" type="number" step="0.01">
            <div class="form-label">股數</div><input class="form-input" id="tx-shares" type="number">
            <span id="tx-sell-fields">
                <div class="form-label">手續費</div><input class="form-input" id="tx-fee" type="number" step="0.01" value="0">
                <div class="form-label">交易稅</div><input class="form-input" id="tx-tax" type="number" step="0.01" value="0">
            </span>`;
    } else if (action === 'dividend') {
        fields = `
            <div class="form-label">日期</div><input class="form-input" id="tx-date" type="date" value="${today()}">
            <div class="form-label">股利總額</div><input class="form-input" id="tx-total" type="number" step="0.01">`;
    } else if (action === 'dividend_reinvest') {
        modeSwitch = buildModeSwitch('reinvest-mode', '手續費', '總支出');
        fields = `
            <div class="form-label">日期</div><input class="form-input" id="tx-date" type="date" value="${today()}">
            <div class="form-label">價格</div><input class="form-input" id="tx-price" type="number" step="0.01">
            <div class="form-label">股數</div><input class="form-input" id="tx-shares" type="number">
            <div class="form-label" id="tx-buy-label">手續費</div><input class="form-input" id="tx-buy-fee" type="number" step="0.01" value="0">`;
    } else if (action === 'stock_dividend') {
        fields = `
            <div class="form-label">日期</div><input class="form-input" id="tx-date" type="date" value="${today()}">
            <div class="form-label">增加股數</div><input class="form-input" id="tx-shares" type="number">`;
    }

    showModal(`
        <h3>${labels[action]} - ${code}</h3>
        ${modeSwitch}
        <div class="form-grid">${fields}</div>
        <div class="btn-group" style="margin-top:16px">
            <button class="btn btn-primary" onclick="submitTxn('${code}','${action}')">確定</button>
            <button class="btn btn-gray" onclick="hideModal()">取消</button>
        </div>
    `);

    if (action === 'sell') {
        setupSellModeSwitch();
    }
    if (action === 'buy' || action === 'dividend_reinvest') {
        setupBuyModeSwitch();
    }
}

function buildModeSwitch(id, labelA, labelB) {
    return `
    <div style="margin-bottom:12px;font-size:13px">
        <label style="cursor:pointer;margin-right:12px">
            <input type="radio" name="${id}" value="a" checked onchange="onModeChange('${id}')"> ${labelA}
        </label>
        <label style="cursor:pointer">
            <input type="radio" name="${id}" value="b" onchange="onModeChange('${id}')"> ${labelB}
        </label>
    </div>`;
}

function onModeChange(groupId) {
    const val = document.querySelector(`input[name="${groupId}"]:checked`).value;
    if (groupId === 'buy-mode' || groupId === 'reinvest-mode') {
        const label = document.getElementById('tx-buy-label');
        if (label) label.textContent = val === 'b' ? '總支出' : '手續費';
        const input = document.getElementById('tx-buy-fee');
        if (input) { input.value = 0; input.placeholder = val === 'b' ? '含手續費的總金額' : ''; }
    } else if (groupId === 'sell-mode') {
        const container = document.getElementById('tx-sell-fields');
        if (val === 'b') {
            container.innerHTML = `
                <div class="form-label">總收入 (淨額)</div><input class="form-input" id="tx-total-received" type="number" step="0.01">`;
        } else {
            container.innerHTML = `
                <div class="form-label">手續費</div><input class="form-input" id="tx-fee" type="number" step="0.01" value="0">
                <div class="form-label">交易稅</div><input class="form-input" id="tx-tax" type="number" step="0.01" value="0">`;
        }
    }
}

function setupBuyModeSwitch() {}
function setupSellModeSwitch() {}

async function submitTxn(code, action) {
    if (_isSubmitting) return;
    _isSubmitting = true;
    try {
        const data = { code, action, date: document.getElementById('tx-date')?.value || '' };
        if (action === 'buy') {
            data.price = parseFloat(document.getElementById('tx-price').value);
            data.shares = parseInt(document.getElementById('tx-shares').value);
            const isTotalCost = document.querySelector('input[name="buy-mode"]:checked')?.value === 'b';
            if (isTotalCost) {
                data.total_paid = parseFloat(document.getElementById('tx-buy-fee').value);
            } else {
                data.fee = parseFloat(document.getElementById('tx-buy-fee').value || 0);
            }
        } else if (action === 'sell') {
            data.price = parseFloat(document.getElementById('tx-price').value);
            data.shares = parseInt(document.getElementById('tx-shares').value);
            const isTotalIncome = document.querySelector('input[name="sell-mode"]:checked')?.value === 'b';
            if (isTotalIncome) {
                data.total_received = parseFloat(document.getElementById('tx-total-received').value);
            } else {
                data.fee = parseFloat(document.getElementById('tx-fee')?.value || 0);
                data.tax = parseFloat(document.getElementById('tx-tax')?.value || 0);
            }
        } else if (action === 'dividend') {
            data.total = parseFloat(document.getElementById('tx-total').value);
        } else if (action === 'dividend_reinvest') {
            data.price = parseFloat(document.getElementById('tx-price').value);
            data.shares = parseInt(document.getElementById('tx-shares').value);
            const isTotalCost = document.querySelector('input[name="reinvest-mode"]:checked')?.value === 'b';
            if (isTotalCost) {
                data.total_paid = parseFloat(document.getElementById('tx-buy-fee').value);
            } else {
                data.fee = 0;
            }
        } else if (action === 'stock_dividend') {
            data.shares = parseInt(document.getElementById('tx-shares').value);
        }
        const result = await api('/api/transactions', { method: 'POST', body: JSON.stringify(data) });
        if (result) {
            hideModal();
            showToast(result.message, 'success');
            loadDashboard(); loadStockList(); loadEtfList();
            const tab = document.querySelector('.tab-btn.active');
            if (tab && tab.dataset.tab === 'stock') loadStockDetail();
            if (tab && tab.dataset.tab === 'etf') loadEtfDetail();
        }
    } finally {
        _isSubmitting = false;
    }
}

async function deleteStock(code) {
    if (!confirm('確定刪除 ' + code + ' 的所有資料？\n此動作無法復原。')) return;
    const result = await api('/api/portfolio/' + code, { method: 'DELETE' });
    if (result) { showToast(result.message, 'success'); loadDashboard(); loadStockList(); loadEtfList(); }
}

async function deleteTransaction(code, index) {
    if (!confirm('確定刪除此筆交易？\n刪除後將重新計算持倉狀態。')) return;
    const result = await api('/api/portfolio/' + code + '/transactions/' + index, { method: 'DELETE' });
    if (result) {
        showToast(result.message, 'success');
        loadDashboard(); loadStockList(); loadEtfList();
        const sel = document.getElementById('s-combo');
        if (sel && sel.value === code) loadStockDetail();
        const sel2 = document.getElementById('e-combo');
        if (sel2 && sel2.value === code) loadEtfDetail();
    }
}

// ====== Prices ======
async function refreshPrices() {
    const result = await api('/api/prices/refresh', { method: 'POST' });
    if (result) { showToast(result.message, 'success'); loadDashboard(); }
}

// ====== Import / Export ======
async function importCsv() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.csv';
    input.onchange = async () => {
        const file = input.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await fetch('/api/import/csv', { method: 'POST', body: formData });
            const data = await res.json();
            if (res.ok) {
                showToast(data.message, 'success');
                loadDashboard();
            } else {
                showToast(data.error || '匯入失敗', 'error');
            }
        } catch (e) {
            showToast('匯入失敗: ' + e.message, 'error');
        }
    };
    input.click();
}

async function exportCsv() {
    try {
        const res = await fetch('/api/export/csv');
        if (!res.ok) {
            const data = await res.json();
            showToast(data.error || '匯出失敗', 'error');
            return;
        }
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        const date = new Date().toISOString().split('T')[0];
        link.download = `StockTracker_${date}.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
        showToast('匯出成功', 'success');
    } catch (e) {
        showToast('匯出失敗: ' + e.message, 'error');
    }
}

// ====== Config ======
async function loadConfig() {
    const data = await api('/api/config');
    if (!data) return;
    document.getElementById('s-fee_rate').value = data.fee_rate;
    document.getElementById('s-tax_listed').value = data.tax_rate_listed;
    document.getElementById('s-tax_otc').value = data.tax_rate_otc;
    document.getElementById('s-tax_etf').value = data.tax_rate_etf;
    document.getElementById('s-reinvest_mode').value = data.reinvest_mode || 'direct';
}

async function saveConfig() {
    const reinvestMode = document.getElementById('s-reinvest_mode').value;
    const result = await api('/api/config', { method: 'PUT', body: JSON.stringify({
        fee_rate: parseFloat(document.getElementById('s-fee_rate').value),
        tax_rate_listed: parseFloat(document.getElementById('s-tax_listed').value),
        tax_rate_otc: parseFloat(document.getElementById('s-tax_otc').value),
        tax_rate_etf: parseFloat(document.getElementById('s-tax_etf').value),
        reinvest_mode: reinvestMode,
    })});
    if (result) showToast(result.message, 'success');
}

async function resetConfig() {
    const result = await api('/api/config', { method: 'PUT', body: JSON.stringify({
        fee_rate: 0.001425, tax_rate_listed: 0.003, tax_rate_otc: 0.003, tax_rate_etf: 0.001,
        reinvest_mode: 'direct'
    })});
    if (result) { loadConfig(); showToast('已恢復預設值', 'success'); }
}

async function clearCache() {
    const result = await api('/api/cache/clear', { method: 'POST' });
    if (result) showToast(result.message, 'success');
}

// ====== Utils ======
function fmt(n) { return Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 }); }
function fmtPL(n) { const v = Number(n || 0); return (v >= 0 ? '+' : '') + v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
function today() { return new Date().toISOString().split('T')[0]; }

// ====== Backtest ======
async function loadBacktest() {
    const combo = document.getElementById('bt-code');
    const prev = combo.value;
    const data = await api('/api/portfolio');
    combo.innerHTML = '<option value="">-- 整體投資組合 --</option>';
    if (data) {
        for (const s of data.stocks) {
            const opt = document.createElement('option');
            opt.value = s.code;
            opt.textContent = s.code + (s.name ? ' - ' + s.name : '');
            if (s.code === prev) opt.selected = true;
            combo.appendChild(opt);
        }
    }
    const statusEl = document.getElementById('bt-history-status');
    const status = await api('/api/backtest/history-status');
    if (status) {
        const entries = Object.entries(status);
        const ok = entries.filter(([, v]) => v).length;
        statusEl.innerHTML = `<span style="font-size:13px;color:var(--gray-500)">歷史資料：${ok}/${entries.length} 檔已下載</span>`;
    }
}

async function downloadHistory() {
    const result = await api('/api/backtest/download-history', { method: 'POST' });
    if (result) {
        showToast(result.message, 'success');
        loadBacktest();
    }
}

async function runBacktest() {
    const code = document.getElementById('bt-code').value;
    const years = document.getElementById('bt-years').value;

    document.getElementById('bt-loading').style.display = 'block';
    document.getElementById('bt-metrics').style.display = 'none';
    document.getElementById('bt-charts').style.display = 'none';
    document.getElementById('bt-table-container').style.display = 'none';

    let data;
    if (code) {
        data = await api('/api/backtest/stock/' + code + '?years=' + years);
    } else {
        data = await api('/api/backtest/portfolio?years=' + years);
    }

    document.getElementById('bt-loading').style.display = 'none';
    if (!data) return;
    if (data.error) { showToast(data.error, 'error'); return; }

    renderBtMetrics(data.metrics);
    renderBtTable(data);
    setTimeout(() => renderBtCharts(data), 50);
}

function renderBtMetrics(m) {
    const el = document.getElementById('bt-metrics');
    el.style.display = 'grid';
    el.innerHTML = `
        <div class="card"><div class="card-label">總報酬率</div><div class="card-value ${m.total_return >= 0 ? 'positive' : 'negative'}">${fmtPL(m.total_return)}%</div></div>
        <div class="card"><div class="card-label">年化報酬 (CAGR)</div><div class="card-value ${m.cagr >= 0 ? 'positive' : 'negative'}">${fmtPL(m.cagr)}%</div></div>
        <div class="card"><div class="card-label">最大回撤</div><div class="card-value negative">${fmtPL(m.max_drawdown)}%</div></div>
        <div class="card"><div class="card-label">大盤報酬</div><div class="card-value ${m.benchmark_return >= 0 ? 'positive' : 'negative'}">${fmtPL(m.benchmark_return)}%</div></div>
        <div class="card"><div class="card-label">年化波動率</div><div class="card-value">${fmtPL(m.annual_volatility)}%</div></div>
        <div class="card"><div class="card-label">Sharpe Ratio</div><div class="card-value ${m.sharpe_ratio >= 1 ? 'positive' : (m.sharpe_ratio >= 0 ? '' : 'negative')}">${m.sharpe_ratio}</div></div>
    `;
}

function renderBtCharts(data) {
    document.getElementById('bt-charts').style.display = 'block';
    document.getElementById('bt-table-container').style.display = 'block';

    if (typeof Chart === 'undefined') {
        document.getElementById('bt-charts').innerHTML = '<p style="text-align:center;color:var(--gray-500);padding:20px">Chart.js 未載入，無法顯示圖表</p>';
        return;
    }

    try {
        const dates = data.dates;
        const eqCtx = document.getElementById('bt-equity-chart').getContext('2d');

        const eqDatasets = [
            {
                label: '投資組合',
                data: data.portfolio_values,
                borderColor: '#2563eb',
                backgroundColor: 'rgba(37, 99, 235, 0.05)',
                borderWidth: 2,
                pointRadius: 0,
                fill: false,
                yAxisID: 'y',
            },
            {
                label: '成本線',
                data: data.cost_basis,
                borderColor: '#9ca3af',
                borderWidth: 1,
                borderDash: [4, 4],
                pointRadius: 0,
                fill: false,
                yAxisID: 'y',
            },
        ];

        const hasBenchmark = data.benchmark_values && data.benchmark_values.some(v => v !== null);
        if (hasBenchmark) {
            eqDatasets.push({
                label: '加權指數 (^TWII)',
                data: data.benchmark_values,
                borderColor: '#16a34a',
                backgroundColor: 'rgba(22, 163, 74, 0.05)',
                borderWidth: 2,
                pointRadius: 0,
                fill: false,
                borderDash: [6, 3],
                yAxisID: 'y',
            });
        }

        if (window._btEquityChart) window._btEquityChart.destroy();
        window._btEquityChart = new Chart(eqCtx, {
            type: 'line',
            data: { labels: dates, datasets: eqDatasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { intersect: false, mode: 'index' },
                plugins: {
                    legend: { position: 'bottom', labels: { usePointStyle: true, padding: 16 } },
                    tooltip: {
                        callbacks: {
                            label: function(ctx) {
                                return ctx.dataset.label + ': $' + Number(ctx.parsed.y).toLocaleString('en-US', { minimumFractionDigits: 2 });
                            }
                        }
                    }
                },
                scales: {
                    x: { display: true, ticks: { maxTicksLimit: 12, font: { size: 10 } }, grid: { display: false } },
                    y: {
                        display: true,
                        ticks: { callback: v => '$' + Number(v).toLocaleString('en-US', { maximumFractionDigits: 0 }) },
                    },
                },
            },
        });

        const ddCtx = document.getElementById('bt-dd-chart').getContext('2d');
        if (window._btDdChart) window._btDdChart.destroy();
        window._btDdChart = new Chart(ddCtx, {
            type: 'line',
            data: {
                labels: dates,
                datasets: [{
                    label: '回撤',
                    data: data.drawdowns,
                    borderColor: '#dc2626',
                    backgroundColor: 'rgba(220, 38, 38, 0.1)',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    fill: true,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: ctx => ctx.parsed.y.toFixed(2) + '%',
                        },
                    },
                },
                scales: {
                    x: { display: true, ticks: { maxTicksLimit: 8, font: { size: 10 } }, grid: { display: false } },
                    y: {
                        display: true,
                        ticks: { callback: v => v.toFixed(1) + '%' },
                    },
                },
            },
        });
    } catch (e) {
        console.error('Chart render error:', e);
        document.getElementById('bt-charts').innerHTML = '<p style="text-align:center;color:var(--danger);padding:20px">圖表渲染錯誤：' + e.message + '</p>';
    }
}

function renderBtTable(data) {
    const tbody = document.getElementById('bt-table-body');
    tbody.innerHTML = '';
    for (let i = 0; i < data.dates.length; i += Math.max(1, Math.floor(data.dates.length / 500))) {
        const tr = document.createElement('tr');
        const ret = data.returns_pct[i];
        const dd = data.drawdowns[i];
        tr.innerHTML = `
            <td>${data.dates[i]}</td>
            <td class="right">${fmt(data.portfolio_values[i])}</td>
            <td class="right">${fmt(data.cost_basis[i])}</td>
            <td class="right ${ret >= 0 ? 'card-value positive' : 'card-value negative'}" style="font-size:13px">${fmtPL(ret)}%</td>
            <td class="right ${dd < 0 ? 'card-value negative' : ''}" style="font-size:13px">${fmtPL(dd)}%</td>
        `;
        tbody.appendChild(tr);
    }
}

// ====== News ======
let _newsCurrentPage = 1;

async function loadNews(page) {
    _newsCurrentPage = page || 1;
    const query = '/api/news?page=' + _newsCurrentPage + '&per_page=20';
    try {
        const res = await fetch(query);
        const data = await res.json();
        if (!res.ok) { showToast(data.error || '載入失敗', 'error'); return; }
        renderNews(data);
    } catch (e) {
        showToast('新聞載入失敗: ' + e.message, 'error');
    }
}

function renderNews(data) {
    const el = document.getElementById('news-list');
    const statusEl = document.getElementById('news-status');

    if (data.cooldown_remaining > 0) {
        const min = Math.ceil(data.cooldown_remaining / 60);
        statusEl.textContent = '已更新 · 還剩 ' + min + ' 分鐘可重新整理';
    } else {
        const lastRefresh = data.last_refresh_at ? new Date(data.last_refresh_at * 1000).toLocaleString('zh-TW') : '尚未更新';
        statusEl.textContent = '上次更新：' + lastRefresh;
    }

    if (!data.articles || data.articles.length === 0) {
        el.innerHTML = '<div style="text-align:center;padding:40px;color:var(--gray-400)">暫無新聞</div>';
        document.getElementById('news-pagination').innerHTML = '';
        return;
    }

    var html = '';
    for (var i = 0; i < data.articles.length; i++) {
        var a = data.articles[i];
        var date = a.published ? new Date(a.published).toLocaleDateString('zh-TW') : '';
        var stocksHtml = '';
        if (a.related_stocks && a.related_stocks.length > 0) {
            stocksHtml = '<div style="margin-top:4px"><span style="font-size:12px;color:var(--gray-500)">' + a.related_stocks.join(', ') + '</span></div>';
        }
        html += '<div class="news-item" onclick="window.open(\'' + a.url + '\',\'_blank\')" style="cursor:pointer;padding:14px;border:1px solid var(--border);border-radius:8px;margin-bottom:10px;transition:background 0.2s" onmouseover="this.style.background=\'var(--bg-hover)\'" onmouseout="this.style.background=\'\'">';
        html += '<div style="display:flex;justify-content:space-between;align-items:flex-start">';
        html += '<div style="font-weight:600;color:var(--gray-800);margin-bottom:4px;flex:1">' + a.title + '</div>';
        html += '<div style="font-size:12px;color:var(--gray-400);white-space:nowrap;margin-left:12px">' + date + '</div>';
        html += '</div>';
        html += '<div style="font-size:13px;color:var(--gray-500);margin-bottom:4px">' + a.summary + '</div>';
        html += '<div style="font-size:12px;color:var(--gray-400)"> Yahoo Finance</div>';
        html += stocksHtml;
        html += '</div>';
    }
    el.innerHTML = html;
    renderNewsPagination(data);
}

function renderNewsPagination(data) {
    var el = document.getElementById('news-pagination');
    if (data.total_pages <= 1) { el.innerHTML = ''; return; }
    var html = '<div style="text-align:center;padding:12px">';
    if (data.page > 1) {
        html += '<button class="btn btn-sm btn-gray" onclick="loadNews(' + (data.page - 1) + ')" style="margin-right:8px">上一頁</button>';
    }
    html += '<span style="font-size:13px;color:var(--gray-500);margin:0 12px">第 ' + data.page + ' / ' + data.total_pages + ' 頁</span>';
    if (data.page < data.total_pages) {
        html += '<button class="btn btn-sm btn-gray" onclick="loadNews(' + (data.page + 1) + ')" style="margin-left:8px">下一頁</button>';
    }
    html += '</div>';
    el.innerHTML = html;
}

async function refreshNews() {
    try {
        const res = await fetch('/api/news/refresh', { method: 'POST' });
        const data = await res.json();
        if (!res.ok) {
            if (data.cooldown_remaining) {
                const min = Math.ceil(data.cooldown_remaining / 60);
                showToast('冷卻中，剩 ' + min + ' 分鐘', 'warning');
            } else {
                showToast(data.error || '重新整理失敗', 'error');
            }
            return;
        }
        showToast('新聞已更新', 'success');
        renderNews(data);
        loadNews(1);
    } catch (e) {
        showToast('重新整理失敗: ' + e.message, 'error');
    }
}

// ====== Archived ======
async function loadArchived() {
    const data = await api('/api/portfolio/archived');
    if (!data) return;

    const el = document.getElementById('archived-list');
    if (!data.stocks || data.stocks.length === 0) {
        el.innerHTML = '<div style="text-align:center;padding:40px;color:var(--gray-400)">尚無已封存的股票</div>';
        return;
    }

    let html = '<div class="table-wrap"><table class="data-table"><thead><tr>';
    html += '<th>代碼</th><th>類型</th><th>總成本</th><th>交易次數</th><th>最後交易日期</th>';
    html += '</tr></thead><tbody>';

    for (const s of data.stocks) {
        const lastTx = s.history && s.history.length > 0 ? s.history[s.history.length - 1] : null;
        const lastDate = lastTx ? lastTx.date : 'N/A';
        const txCount = s.history ? s.history.length : 0;
        html += `<tr>
            <td>${s.code}${s.name ? '<br><span class="stock-name">' + s.name + '</span>' : ''}</td>
            <td><span class="badge ${s.type === 'ETF' ? 'badge-etf' : 'badge-stock'}">${s.type}</span></td>
            <td class="right">${fmt(s.total_cost)}</td>
            <td class="right">${txCount}</td>
            <td>${lastDate}</td>
        </tr>`;
    }
    html += '</tbody></table></div>';
    el.innerHTML = html;
}

// ====== Fund Pool ======
async function loadFundPool() {
    const data = await api('/api/fund-pool');
    if (!data) return;

    document.getElementById('fp-initial').textContent = '$' + fmt(data.initial_capital);
    document.getElementById('fp-total').textContent = '$' + fmt(data.total_value);
    document.getElementById('fp-cash').textContent = '$' + fmt(data.cash_balance);

    const rateEl = document.getElementById('fp-rate');
    rateEl.textContent = fmtPL(data.growth_rate) + '%';
    rateEl.className = 'card-value ' + getGrowthColor(data.growth_rate);

    renderFundSnapshots(data.snapshots);
    renderFundChart(data.snapshots, data.initial_capital);
}

function getGrowthColor(rate) {
    return rate >= 0 ? 'positive' : 'negative';
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
            <td>${s.date}</td>
            <td class="right">$${fmt(s.total_value)}</td>
            <td class="right ${getGrowthColor(s.growth_rate)}">${fmtPL(s.growth_rate)}%</td>
            <td class="right">$${fmt(s.cash_balance)}</td>
            <td class="right">$${fmt(s.market_value)}</td>
        </tr>
    `).join('');
}

function renderFundChart(snapshots, initialCapital) {
    const canvas = document.getElementById('fp-chart');
    if (!canvas) return;
    if (typeof Chart === 'undefined') return;

    const ctx = canvas.getContext('2d');
    if (window._fpChart) window._fpChart.destroy();

    if (!snapshots || snapshots.length === 0) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.font = '14px sans-serif';
        ctx.fillStyle = '#9ca3af';
        ctx.textAlign = 'center';
        ctx.fillText('尚無報告資料', canvas.width / 2, canvas.height / 2);
        return;
    }

    const labels = snapshots.map(s => s.date);
    const totalValues = snapshots.map(s => s.total_value);

    window._fpChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: '投資總值',
                    data: totalValues,
                    borderColor: '#2563eb',
                    backgroundColor: 'rgba(37, 99, 235, 0.1)',
                    borderWidth: 2,
                    pointRadius: 4,
                    fill: true,
                    tension: 0.3,
                },
                {
                    label: '初始本金',
                    data: labels.map(() => initialCapital),
                    borderColor: '#9ca3af',
                    borderWidth: 1,
                    borderDash: [5, 5],
                    pointRadius: 0,
                    fill: false,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: true, position: 'top' },
                tooltip: {
                    callbacks: {
                        label: ctx => ctx.dataset.label + ': $' + fmt(ctx.parsed.y)
                    }
                }
            },
            scales: {
                x: { display: true },
                y: {
                    display: true,
                    ticks: {
                        callback: v => '$' + fmt(v)
                    }
                }
            }
        }
    });
}

function showSnapshotDialog() {
    const result = confirm('確定要產生本月報告？');
    if (!result) return;

    api('/api/fund-pool/snapshot', { method: 'POST', body: JSON.stringify({}) })
        .then(data => {
            if (data) {
                showToast(data.message, 'success');
                loadFundPool();
            }
        });
}

// ====== Init ======
const savedTab = localStorage.getItem('activeTab') || 'dashboard';
switchTab(savedTab);
