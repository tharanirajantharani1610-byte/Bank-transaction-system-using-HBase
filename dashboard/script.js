/**
 * NexusBank - HBase Big Data Analytics Dashboard
 * File: dashboard/script.js
 * Description: Interacts with Flask REST API & Apache HBase backend,
 *              renders interactive Chart.js visualizations, manages search/filters,
 *              and provides live CRUD operations.
 */

const API_BASE = window.location.origin.includes(":5000") 
  ? "" 
  : "http://localhost:5000";

let charts = {};

// On DOM Ready
document.addEventListener("DOMContentLoaded", () => {
  initDashboard();
});

async function initDashboard() {
  await checkClusterHealth();
  await loadSummaryKPIs();
  await loadChartStatistics();
  await loadHBaseTransactions();
  await loadSuspiciousTransactions();
}

/**
 * Tab Switching Logic
 */
function switchTab(tabId) {
  document.querySelectorAll(".tab-content").forEach(el => el.classList.remove("active"));
  document.querySelectorAll(".tab-btn").forEach(el => el.classList.remove("active"));

  const targetTab = document.getElementById(tabId);
  if (targetTab) {
    targetTab.classList.add("active");
  }

  // Highlight active button
  const activeBtn = Array.from(document.querySelectorAll(".tab-btn")).find(btn => 
    btn.getAttribute("onclick")?.includes(tabId)
  );
  if (activeBtn) activeBtn.classList.add("active");
}

/**
 * 1. Check Cluster Health
 */
async function checkClusterHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    const data = await res.json();
    if (data.status === "healthy" || data.hbase_connected) {
      document.getElementById("chip-hbase").innerHTML = `
        <span class="status-dot pulse-green"></span>
        <span class="status-label">HBase 2.1: <strong>Connected</strong></span>
      `;
    } else {
      document.getElementById("chip-hbase").innerHTML = `
        <span class="status-dot pulse-amber"></span>
        <span class="status-label">HBase: <strong>Starting Up</strong></span>
      `;
    }
  } catch (err) {
    console.warn("Cluster health check endpoint:", err);
  }
}

/**
 * 2. Load KPI Summary Cards
 */
async function loadSummaryKPIs() {
  try {
    const res = await fetch(`${API_BASE}/api/summary`);
    if (!res.ok) throw new Error("Summary endpoint unavailable");
    const summary = await res.json();

    document.getElementById("metric-total-txns").innerText = Number(summary.total_transactions || 0).toLocaleString();
    document.getElementById("metric-total-volume").innerText = "₹" + Number(summary.total_volume || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 });
    document.getElementById("metric-total-deposits").innerText = "₹" + Number(summary.total_deposits || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 });
    document.getElementById("metric-total-withdrawals").innerText = "₹" + Number(summary.total_withdrawals || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 });

    const successCount = summary.status_distribution?.SUCCESS || 0;
    const failedCount = summary.status_distribution?.FAILED || 0;
    const pendingCount = summary.status_distribution?.PENDING || 0;
    const total = summary.total_transactions || 1;

    document.getElementById("metric-success-txns").innerText = Number(successCount).toLocaleString();
    document.getElementById("metric-failed-txns").innerText = Number(failedCount).toLocaleString();
    document.getElementById("metric-pending-txns").innerText = Number(pendingCount).toLocaleString();
    document.getElementById("metric-suspicious-txns").innerText = Number(summary.suspicious_transactions_count || 0).toLocaleString();

    const rate = ((successCount / total) * 100).toFixed(1);
    document.getElementById("metric-success-rate").innerText = `${rate}% Success Rate`;
  } catch (err) {
    console.error("Failed to load KPIs:", err);
  }
}

/**
 * 3. Render Chart.js Visualizations
 */
async function loadChartStatistics() {
  try {
    const res = await fetch(`${API_BASE}/api/statistics`);
    if (!res.ok) throw new Error("Statistics endpoint unavailable");
    const stats = await res.json();

    // Chart 1: Monthly Financial Volume Trend
    const monthlyData = stats.monthly_summary || {};
    const months = Object.keys(monthlyData);
    const volumes = months.map(m => monthlyData[m].volume / 100000); // In Lakhs

    renderLineChart("chart-monthly-volume", months, volumes, "Total Volume (₹ Lakhs)", "#6366F1");

    // Chart 2: Transaction Types Breakdown
    const typeData = stats.type_distribution || {};
    renderDoughnutChart("chart-types", Object.keys(typeData), Object.values(typeData), [
      "#6366F1", "#10B981", "#3B82F6", "#F59E0B", "#EC4899", "#8B5CF6"
    ]);

    // Chart 3: Payment Methods
    const methodData = stats.payment_method_distribution || {};
    renderDoughnutChart("chart-methods", Object.keys(methodData), Object.values(methodData), [
      "#06B6D4", "#10B981", "#F59E0B", "#6366F1", "#8B5CF6", "#3B82F6", "#EF4444", "#64748B"
    ]);

    // Chart 4: Status Distribution
    const statusData = stats.status_distribution || {};
    renderPieChart("chart-status", Object.keys(statusData), Object.values(statusData), [
      "#10B981", "#EF4444", "#F59E0B", "#8B5CF6"
    ]);

    // Chart 5: City Distribution (Top 8)
    const cityData = stats.city_distribution || {};
    const sortedCities = Object.entries(cityData).sort((a,b) => b[1] - a[1]).slice(0, 8);
    renderBarChart("chart-cities", sortedCities.map(c => c[0]), sortedCities.map(c => c[1]), "Transactions", "#818CF8");

    // Chart 6: Liquidity Flow
    const liquidity = stats.deposits_vs_withdrawals || {};
    renderBarChart("chart-liquidity", Object.keys(liquidity), Object.values(liquidity).map(v => v / 100000), "Volume (₹ Lakhs)", "#10B981");

    // Chart 7: Top Active Customers
    const topCust = stats.top_customers || [];
    renderHorizontalBarChart("chart-customers", topCust.map(c => c[0].split(" ")[0]), topCust.map(c => c[1]), "Transaction Count", "#F59E0B");

  } catch (err) {
    console.error("Failed to load chart stats:", err);
  }
}

function renderLineChart(canvasId, labels, data, label, color) {
  const ctx = document.getElementById(canvasId)?.getContext("2d");
  if (!ctx) return;
  if (charts[canvasId]) charts[canvasId].destroy();

  charts[canvasId] = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [{
        label: label,
        data: data,
        borderColor: color,
        backgroundColor: "rgba(99, 102, 241, 0.15)",
        borderWidth: 3,
        fill: true,
        tension: 0.35,
        pointBackgroundColor: color,
        pointBorderColor: "#FFF",
        pointRadius: 4
      }]
    },
    options: getChartBaseOptions()
  });
}

function renderDoughnutChart(canvasId, labels, data, colors) {
  const ctx = document.getElementById(canvasId)?.getContext("2d");
  if (!ctx) return;
  if (charts[canvasId]) charts[canvasId].destroy();

  charts[canvasId] = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: colors,
        borderWidth: 2,
        borderColor: "#111827"
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "right", labels: { color: "#9CA3AF", font: { family: "Plus Jakarta Sans" } } }
      }
    }
  });
}

function renderPieChart(canvasId, labels, data, colors) {
  const ctx = document.getElementById(canvasId)?.getContext("2d");
  if (!ctx) return;
  if (charts[canvasId]) charts[canvasId].destroy();

  charts[canvasId] = new Chart(ctx, {
    type: "pie",
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: colors,
        borderWidth: 2,
        borderColor: "#111827"
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "right", labels: { color: "#9CA3AF" } }
      }
    }
  });
}

function renderBarChart(canvasId, labels, data, label, color) {
  const ctx = document.getElementById(canvasId)?.getContext("2d");
  if (!ctx) return;
  if (charts[canvasId]) charts[canvasId].destroy();

  charts[canvasId] = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [{
        label: label,
        data: data,
        backgroundColor: color,
        borderRadius: 6
      }]
    },
    options: getChartBaseOptions()
  });
}

function renderHorizontalBarChart(canvasId, labels, data, label, color) {
  const ctx = document.getElementById(canvasId)?.getContext("2d");
  if (!ctx) return;
  if (charts[canvasId]) charts[canvasId].destroy();

  charts[canvasId] = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [{
        label: label,
        data: data,
        backgroundColor: color,
        borderRadius: 6
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#9CA3AF" } },
        y: { grid: { display: false }, ticks: { color: "#9CA3AF" } }
      },
      plugins: { legend: { display: false } }
    }
  });
}

function getChartBaseOptions() {
  return {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: { grid: { color: "rgba(255, 255, 255, 0.05)" }, ticks: { color: "#9CA3AF" } },
      y: { grid: { color: "rgba(255, 255, 255, 0.05)" }, ticks: { color: "#9CA3AF" } }
    },
    plugins: {
      legend: { labels: { color: "#9CA3AF" } }
    }
  };
}

/**
 * 4. Load Live HBase Transactions
 */
async function loadHBaseTransactions() {
  const tbody = document.getElementById("table-body");
  tbody.innerHTML = `<tr><td colspan="11" class="loading-cell"><i class="fa-solid fa-spinner fa-spin"></i> Querying Apache HBase container...</td></tr>`;

  const searchVal = document.getElementById("search-input").value.trim();
  const statusVal = document.getElementById("filter-status").value;
  const typeVal = document.getElementById("filter-type").value;

  let url = `${API_BASE}/api/transactions?limit=60`;
  if (searchVal.startsWith("CUST")) {
    url += `&customer_id=${encodeURIComponent(searchVal)}`;
  }
  if (statusVal) url += `&status=${encodeURIComponent(statusVal)}`;
  if (typeVal) url += `&type=${encodeURIComponent(typeVal)}`;

  try {
    const res = await fetch(url);
    const data = await res.json();
    const list = data.transactions || [];

    document.getElementById("table-record-count").innerText = `Showing ${list.length} records`;

    if (list.length === 0) {
      tbody.innerHTML = `<tr><td colspan="11" style="text-align: center; padding: 2rem; color: #9CA3AF;">No transactions found in HBase matching filters.</td></tr>`;
      return;
    }

    tbody.innerHTML = list.map(tx => {
      const statusBadge = getStatusBadge(tx.transaction_status);
      const rowKey = tx.row_key || `${tx.customer_id}#${tx.transaction_date}#${tx.transaction_id}`;
      return `
        <tr>
          <td class="rowkey-cell" title="${rowKey}">${escapeHtml(rowKey)}</td>
          <td><strong>${escapeHtml(tx.transaction_id || '')}</strong></td>
          <td>${escapeHtml(tx.customer_name || tx.customer_id || '')}</td>
          <td><span class="badge badge-purple">${escapeHtml(tx.transaction_type || '')}</span></td>
          <td style="font-weight: 700;">₹${Number(tx.amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
          <td>₹${Number(tx.balance_after_transaction || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
          <td><span class="badge badge-cyan">${escapeHtml(tx.payment_method || '')}</span></td>
          <td>${escapeHtml(tx.city || '')} / ${escapeHtml(tx.branch || '')}</td>
          <td>${escapeHtml(tx.transaction_date || '')} ${escapeHtml(tx.transaction_time || '')}</td>
          <td>${statusBadge}</td>
          <td>
            <button class="btn btn-secondary" style="padding: 0.3rem 0.6rem; font-size: 0.75rem;" onclick="deleteHBaseRow('${encodeURIComponent(rowKey)}')">
              <i class="fa-solid fa-trash text-crimson"></i>
            </button>
          </td>
        </tr>
      `;
    }).join("");

  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="11" style="text-align: center; color: #EF4444; padding: 2rem;">Error querying HBase: ${err.message}</td></tr>`;
  }
}

function handleSearchKey(event) {
  if (event.key === "Enter") {
    loadHBaseTransactions();
  }
}

function resetFilters() {
  document.getElementById("search-input").value = "";
  document.getElementById("filter-status").value = "";
  document.getElementById("filter-type").value = "";
  loadHBaseTransactions();
}

function getStatusBadge(status) {
  switch ((status || "").toUpperCase()) {
    case "SUCCESS": return `<span class="badge badge-success"><i class="fa-solid fa-check"></i> SUCCESS</span>`;
    case "FAILED": return `<span class="badge badge-crimson"><i class="fa-solid fa-xmark"></i> FAILED</span>`;
    case "PENDING": return `<span class="badge badge-amber"><i class="fa-solid fa-clock"></i> PENDING</span>`;
    case "REVERSED": return `<span class="badge badge-purple"><i class="fa-solid fa-rotate-left"></i> REVERSED</span>`;
    default: return `<span class="badge badge-info">${status}</span>`;
  }
}

/**
 * 5. Load Suspicious Transactions
 */
async function loadSuspiciousTransactions() {
  const tbody = document.getElementById("suspicious-table-body");
  try {
    const res = await fetch(`${API_BASE}/api/suspicious?limit=80`);
    const data = await res.json();
    const list = data.records || [];

    document.getElementById("suspicious-count-badge").innerText = `${data.total_suspicious || list.length} High-Risk Flags`;

    if (list.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; padding: 2rem;">No suspicious anomalies identified.</td></tr>`;
      return;
    }

    tbody.innerHTML = list.map(item => {
      const riskScore = item.risk_score || 50;
      const riskClass = riskScore >= 70 ? 'badge-crimson' : 'badge-amber';
      const reasons = (item.risk_reasons || []).join("<br>• ");
      return `
        <tr>
          <td><strong>${escapeHtml(item.transaction_id)}</strong></td>
          <td>${escapeHtml(item.customer_name)} (${escapeHtml(item.customer_id)})</td>
          <td><code>${escapeHtml(item.account_id)}</code></td>
          <td style="font-weight: 700; color: #EF4444;">₹${Number(item.amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
          <td>${escapeHtml(item.transaction_type)}</td>
          <td>${escapeHtml(item.payment_method)}</td>
          <td>${getStatusBadge(item.status)}</td>
          <td><span class="badge ${riskClass}">${riskScore} Risk</span></td>
          <td style="font-size: 0.8rem; color: #FCA5A5;">• ${reasons}</td>
        </tr>
      `;
    }).join("");

  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: #EF4444;">Error loading suspicious radar: ${err.message}</td></tr>`;
  }
}

/**
 * 6. CRUD: CREATE Operation (Submit New Transaction to HBase)
 */
async function submitNewTransaction(e) {
  e.preventDefault();
  const btn = document.getElementById("btn-submit-txn");
  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Writing to HBase...`;

  const payload = {
    customer_id: document.getElementById("new-cust-id").value.trim(),
    customer_name: document.getElementById("new-cust-name").value.trim(),
    account_type: document.getElementById("new-acc-type").value,
    transaction_type: document.getElementById("new-txn-type").value,
    amount: parseFloat(document.getElementById("new-amount").value),
    payment_method: document.getElementById("new-payment-method").value,
    branch: document.getElementById("new-branch").value.trim(),
    city: document.getElementById("new-city").value.trim(),
    description: document.getElementById("new-desc").value.trim(),
    transaction_status: "SUCCESS"
  };

  try {
    const res = await fetch(`${API_BASE}/api/transactions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await res.json();
    if (res.ok) {
      showToast(`Transaction stored in HBase! Key: ${result.row_key}`, "success");
      closeModal("modal-create-txn");
      document.getElementById("form-create-txn").reset();
      await loadHBaseTransactions();
      await loadSummaryKPIs();
    } else {
      showToast(`HBase Error: ${result.error}`, "error");
    }
  } catch (err) {
    showToast(`Failed to connect to backend: ${err.message}`, "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="fa-solid fa-cloud-arrow-up"></i> Put into HBase`;
  }
}

/**
 * 7. CRUD: DELETE Operation (Delete HBase Row)
 */
async function deleteHBaseRow(encodedRowKey) {
  if (!confirm(`Delete HBase record row: ${decodeURIComponent(encodedRowKey)}?`)) return;

  try {
    const res = await fetch(`${API_BASE}/api/transactions/${encodedRowKey}`, {
      method: "DELETE"
    });
    const result = await res.json();
    if (res.ok) {
      showToast(result.message || "Row deleted from HBase", "success");
      await loadHBaseTransactions();
      await loadSummaryKPIs();
    } else {
      showToast(`Delete failed: ${result.error}`, "error");
    }
  } catch (err) {
    showToast(`Error: ${err.message}`, "error");
  }
}

/**
 * UI Utilities (Modal & Toasts)
 */
function openModal(id) {
  document.getElementById(id)?.classList.add("open");
}

function closeModal(id) {
  document.getElementById(id)?.classList.remove("open");
}

function showToast(message, type = "success") {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <i class="fa-solid ${type === 'success' ? 'fa-circle-check text-success' : 'fa-triangle-exclamation text-crimson'}"></i>
    <span>${escapeHtml(message)}</span>
  `;
  container.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 4500);
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
