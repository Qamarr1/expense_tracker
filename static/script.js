/**
 * Dashboard script (simple & well-explained)
 *
 * Key behaviors:
 * - We wait for BOTH /api/income and /api/expenses before updating KPIs
 *   and the top "Financial Overview" donut (no partial flicker).
 * - The top donut uses LIVE totals and draws the balance in the center.
 * - Row A (Last 30 Days Expenses):
 *     * Pick the most recent up to 4 expense records within 30 days.
 *     * Left: show those rows.
 *     * Right: bar chart uses ONLY those rows' amounts.
 *       IMPORTANT: we pad to exactly 4 slots with zeros, so you always
 *       see 4 bars worth of space. If you have only 1 record, you get
 *       one bar at the left and empty space for the other 3.
 *       The Y-axis auto-scales to the biggest amount (e.g., €1,000 fits).
 * - Row B (Last 60 Days Income):
 *     * Pick the top up to 4 income records by amount within 60 days.
 *     * Left: show those rows.
 *     * Right: donut uses ONLY those rows as slices; center shows their sum.
 * - The top "Refresh" button reloads everything by calling loadAll().
 */

function runDashboard() {
  // ---------- helpers ----------
  const $ = (sel) => document.querySelector(sel);

  const money = (n) =>
    (+n || 0).toLocaleString(undefined, { style: "currency", currency: "EUR" });

  const toNum = (x) => (typeof x === "string" ? parseFloat(x) : +x || 0);

  const parseISO = (d) => new Date(d);

  const daysAgo = (iso) => {
    const d = parseISO(iso);
    if (isNaN(d)) return Infinity;
    const ONE = 24 * 60 * 60 * 1000;
    return Math.floor((Date.now() - d.getTime()) / ONE);
  };

  async function getJSON(url, fallback = []) {
    try {
      const res = await fetch(url, { headers: { accept: "application/json" } });
      if (!res.ok) return fallback;
      return await res.json();
    } catch {
      return fallback;
    }
  }

  // ---------- elements ----------
  const elIncome   = $("#kpi-income");
  const elExpense  = $("#kpi-expense");
  const elBalance  = $("#kpi-balance");
  const elRecent   = $("#recent-list");
  const elCatList  = $("#category-list");

  const elExp30List = $("#exp30-list");
  const elInc60List = $("#inc60-list");

  const btnRefresh = $("#refresh");

  function setLoading(isLoading) {
    if (btnRefresh) {
      btnRefresh.disabled = isLoading;
      btnRefresh.textContent = isLoading ? "Loading..." : "Refresh";
    }
    if (isLoading) {
      elIncome  && (elIncome.textContent  = "—");
      elExpense && (elExpense.textContent = "—");
      elBalance && (elBalance.textContent = "—");
    }
  }

  // ---------- TOP donut (Financial Overview) ----------
  let donutTop;
  function renderTopDonut(totalIncome, totalExpense, balance) {
    const cv = document.getElementById("donut");
    if (!cv) return;
    if (donutTop) donutTop.destroy();

    const data = [Math.max(balance, 0), totalExpense, totalIncome];
    const labels = ["Total Balance", "Total Expenses", "Total Income"];
    const colors = ["#7c3aed", "#ef4444", "#f59e0b"];

    const centerText = {
      id: "centerText",
      afterDraw(chart) {
        const { ctx } = chart;
        const meta = chart.getDatasetMeta(0);
        const arc0 = meta?.data?.[0];
        if (!arc0) return;
        ctx.save();
        const txt = money(balance);
        const size = Math.max(14, Math.floor(Math.min(chart.width, chart.height) * 0.10));
        ctx.font = `800 ${size}px system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif`;
        ctx.fillStyle = "#e9edf2";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(txt, arc0.x, arc0.y);
        ctx.restore();
      }
    };

    donutTop = new Chart(cv.getContext("2d"), {
      type: "doughnut",
      data: { labels, datasets: [{ data, backgroundColor: colors, borderWidth: 0 }] },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "68%",
        plugins: { legend: { position: "bottom" } }
      },
      plugins: [centerText]
    });
  }

  // ---------- Spending by Category (kept) ----------
  function renderCategoryList(expenses, categories) {
    const el = elCatList;
    if (!el) return;
    const nameById = new Map((categories || []).map(c => [c.id, c.name]));
    const totals = new Map();
    (expenses || []).forEach(e => {
      const cat = nameById.get(e.category_id ?? null) || "Uncategorized";
      totals.set(cat, (totals.get(cat) || 0) + toNum(e.amount));
    });
    const rows = [...totals.entries()].map(([name, sum]) => ({ name, sum }))
      .sort((a,b) => b.sum - a.sum);

    el.innerHTML = rows.length
      ? rows.map(r => `
          <div class="row">
            <div class="row-left">
              <div class="bubble">🧾</div>
              <div class="title">${r.name}</div>
            </div>
            <div class="row-right"><span class="amount neg">-${money(r.sum)}</span></div>
          </div>
        `).join("")
      : `<div class="row"><div class="title">No expenses yet.</div></div>`;
  }

  // ---------- Recent (left of top donut) ----------
  function renderRecent(income, expenses, categories) {
    const el = elRecent;
    if (!el) return;
    const nameById = new Map((categories || []).map(c => [c.id, c.name]));
    const inc = (income || []).map(r => ({ date:r.date, amount:toNum(r.amount), label:"Income", type:"income" }));
    const exp = (expenses || []).map(r => ({ date:r.date, amount:toNum(r.amount), label:nameById.get(r.category_id)||"Uncategorized", type:"expense" }));
    const recent = [...inc, ...exp].filter(r=>r.date)
      .sort((a,b)=> parseISO(b.date) - parseISO(a.date)).slice(0,5);

    el.innerHTML = recent.length
      ? recent.map(r => `
          <div class="row">
            <div class="row-left">
              <div class="bubble">${r.type === "income" ? "💶" : "💸"}</div>
              <div>
                <div class="title">${r.label}</div>
                <div style="color:var(--muted);font-size:.9rem;">${r.date}</div>
              </div>
            </div>
            <div class="row-right">
              <span class="amount ${r.type === "expense" ? "neg" : "text-income"}">
                ${r.type === "expense" ? "-" : "+"}${money(Math.abs(r.amount))}
              </span>
            </div>
          </div>
        `).join("")
      : `<div class="row"><div class="title">No transactions yet.</div></div>`;
  }

  // ---------- Row A: Last 30 Days Expenses (pick 4 records) ----------
  function pickExp30Records(expenses) {
    return (expenses || [])
      .filter(r => r.date && daysAgo(r.date) <= 30)
      .sort((a,b)=> parseISO(b.date) - parseISO(a.date))
      .slice(0, 4); // <= FOUR records
  }

  function renderExp30List(expRows) {
    const el = elExp30List;
    if (!el) return;
    el.innerHTML = expRows.length
      ? expRows.map(r => `
          <div class="row">
            <div class="row-left">
              <div class="bubble">🧾</div>
              <div class="title">${r.name || "Expense"}</div>
            </div>
            <div class="row-right">
              <span style="color:var(--muted);margin-right:8px;">${r.date}</span>
              <span class="amount neg">-${money(toNum(r.amount))}</span>
            </div>
          </div>
        `).join("")
      : `<div class="row"><div class="title">No expenses in last 30 days.</div></div>`;
  }

  let exp30Bar;
  function renderExp30Bar(expRows) {
    const cv = document.getElementById("exp30-bar");
    if (!cv) return;
    if (exp30Bar) exp30Bar.destroy();

    // amounts for present rows
    const amounts = expRows.map(r => toNum(r.amount));
    // pad to exactly 4 slots with zeros (so space remains for missing bars)
    while (amounts.length < 4) amounts.push(0);

    // X-axis: 4 blank labels so we only show bars, no text
    const labels = ["", "", "", ""];

    exp30Bar = new Chart(cv.getContext("2d"), {
      type: "bar",
      data: { labels, datasets: [{ data: amounts, borderWidth: 0 }] },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false }, ticks: { display: false } }, // BLANK X
          y: { beginAtZero: true } // auto-scales to max amount (e.g., €1,000)
        }
      }
    });
  }

  // ---------- Row B: Last 60 Days Income (pick top 4 by amount) ----------
  function pickInc60Records(income) {
    return (income || [])
      .filter(r => r.date && daysAgo(r.date) <= 60)
      .sort((a,b)=> toNum(b.amount) - toNum(a.amount)) // highest first
      .slice(0, 4); // <= FOUR records
  }

  function renderInc60List(incRows) {
    const el = elInc60List;
    if (!el) return;
    el.innerHTML = incRows.length
      ? incRows.map(r => `
          <div class="row">
            <div class="row-left">
              <div class="bubble">💼</div>
              <div class="title">${r.name || "Income"}</div>
            </div>
            <div class="row-right">
              <span style="color:var(--muted);margin-right:8px;">${r.date}</span>
              <span class="amount text-income">+${money(toNum(r.amount))}</span>
            </div>
          </div>
        `).join("")
      : `<div class="row"><div class="title">No income in last 60 days.</div></div>`;
  }

  let inc60Donut;
  function renderInc60Donut(incRows) {
    const cv = document.getElementById("inc60-donut");
    if (!cv) return;
    if (inc60Donut) inc60Donut.destroy();

    // Use those same up-to-4 rows for the donut
    let labels = incRows.map(r => r.name || "Income");
    let values = incRows.map(r => toNum(r.amount));

    // If fewer than 1, show a neutral slice
    if (values.length === 0) {
      labels = ["No data"];
      values = [1];
    }

    // Center text = sum of these slices (NOT all-time income)
    const total = values.reduce((a,b)=> a+b, 0);

    const centerText = {
      id: "centerTextInc",
      afterDraw(chart) {
        const { ctx } = chart;
        const meta = chart.getDatasetMeta(0);
        const arc0 = meta?.data?.[0];
        if (!arc0) return;
        ctx.save();
        const txt = money(total);
        const size = Math.max(14, Math.floor(Math.min(chart.width, chart.height) * 0.10));
        ctx.font = `800 ${size}px system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif`;
        ctx.fillStyle = "#e9edf2";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(txt, arc0.x, arc0.y);
        ctx.restore();
      }
    };

    inc60Donut = new Chart(cv.getContext("2d"), {
      type: "doughnut",
      data: { labels, datasets: [{ data: values, borderWidth: 0 }] },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "68%",
        plugins: { legend: { position: "bottom" } }
      },
      plugins: [centerText]
    });
  }

  // ---------- Load everything together ----------
  async function loadAll() {
    setLoading(true);

    // Wait for BOTH endpoints before computing totals (no partial KPIs)
    const [income, expenses, categories] = await Promise.all([
      getJSON("/api/income", []),
      getJSON("/api/expenses", []),
      getJSON("/api/categories", []),
    ]);

    // Live totals for KPIs + top donut
    const totalIncome  = (income   || []).reduce((a,x)=> a + toNum(x.amount), 0);
    const totalExpense = (expenses || []).reduce((a,x)=> a + toNum(x.amount), 0);
    const balance      = totalIncome - totalExpense;

    // Show negative balance warning
    const banner = document.getElementById("negative-balance-banner");
    if (banner) {
      if (balance < 0) {
        banner.style.display = "block";
      } else {
        banner.style.display = "none";
      }
    }


    elIncome  && (elIncome.textContent  = money(totalIncome));
    elExpense && (elExpense.textContent = money(totalExpense));
    elBalance && (elBalance.textContent = money(balance));

    renderRecent(income, expenses, categories);
    renderTopDonut(totalIncome, totalExpense, balance);
    renderCategoryList(expenses, categories);

    // Row A: pick 4 recent expense records within 30 days -> list + bar (padded to 4)
    const expRows = pickExp30Records(expenses);
    renderExp30List(expRows);
    renderExp30Bar(expRows);

    // Row B: pick 4 top income records within 60 days -> list + donut
    const incRows = pickInc60Records(income);
    renderInc60List(incRows);
    renderInc60Donut(incRows);

    setLoading(false);
  }

  // Refresh button reloads everything
  $("#refresh")?.addEventListener("click", loadAll);

  // First paint
  loadAll();
}

document.addEventListener("DOMContentLoaded", () => {
  const token = localStorage.getItem("access_token");
  if (!token) {
    window.location.href = "/login";
    return;
  }
  runDashboard();
});




