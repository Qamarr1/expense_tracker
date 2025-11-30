/**
 * expenses.js
 * Orchestrates expense CRUD, filtering, chart updates, and inline validation.
 * Key behaviors: keep categories in sync, block invalid input early,
 * respect date filters (dd/mm/yyyy or yyyy-mm-dd), and keep list/chart aligned.
 */

if (window.__EXPENSES_APP_INITIALIZED__) {
  console.warn("expenses.js already initialized; skipping duplicate load");
} else {
  window.__EXPENSES_APP_INITIALIZED__ = true;

(function () {
  // helpers 
  const $ = (s) => document.querySelector(s);
  const money = (n) => (+n || 0).toLocaleString(undefined, { style: "currency", currency: "EUR" });
  const toNum = (x) => (typeof x === "string" ? parseFloat(x) : +x || 0);
  const parseISO = (d) => new Date(d);
  const fmtDay = (iso) => {
    const d = parseISO(iso);
    return isNaN(d) ? "" : d.toLocaleDateString(undefined, { day: "2-digit", month: "short" });
  };
  const httpText = async (res) => {
    let raw = ""; try { raw = await res.text(); } catch {}
    try {
      const j = JSON.parse(raw);
      if (Array.isArray(j?.detail) && j.detail[0]) return j.detail[0].msg || "Validation error";
      return j?.detail || JSON.stringify(j);
    } catch { return raw || res.statusText || "Unknown error"; }
  };
  const getJSON = async (url, fb = []) => {
    try { const r = await fetch(url, { headers: { accept: "application/json" } }); return r.ok ? r.json() : fb; }
    catch { return fb; }
  };

  function todayISO() {
    const t = new Date();
    const y = t.getFullYear(), m = String(t.getMonth() + 1).padStart(2, "0"), d = String(t.getDate()).padStart(2, "0");
    return `${y}-${m}-${d}`;
  }
  function toISODate(s) {
    if (!s) return "";
    if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
    const m = s.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
    return m ? `${m[3]}-${m[2]}-${m[1]}` : s;
  }

  const LARGE_EXPENSE_THRESHOLD = 500;

  // Convert dd/mm/yyyy or ISO to Date; returns null on bad input.
  function parseFilterDate(str) {
    if (!str) return null;
    if (/^\d{4}-\d{2}-\d{2}$/.test(str)) {
      const d = new Date(str);
      return isNaN(d) ? null : d;
    }
    const parts = str.split("/");
    if (parts.length === 3) {
      const [d, m, y] = parts.map((p) => parseInt(p, 10));
      if (!d || !m || !y) return null;
      const dt = new Date(y, m - 1, d);
      return isNaN(dt) ? null : dt;
    }
    return null;
  }

  // Guard rails: only allow ranges where from <= to (or missing)
  function isValidDateRange(fromStr, toStr) {
    const from = parseFilterDate(fromStr);
    const to = parseFilterDate(toStr);
    if (!from || !to) return true;
    return from <= to;
  }

  //  UI pieces 
  const listEl = $("#expense-list");
  const btnRefresh = $("#refresh");
  const btnExport = $("#export-expenses");

  const modal = $("#exp-modal-backdrop");
  const btnOpen = $("#add-expense");
  const btnClose = $("#close-exp-modal");
  const btnCancel = $("#cancel-exp-modal");
  const btnSave = $("#save-expense");
  const inpName = $("#ex-name");
  const inpAmount = $("#ex-amount");
  const inpDate = $("#ex-date");
  const inpCategory = $("#ex-category");
  const inpNote = $("#ex-note");

  const inpFrom = $("#expenses-from");
  const inpTo = $("#expenses-to");
  const inpSearch = $("#expenses-search");
  const statsEl = $("#expense-stats");
  const btnClearFilters = $("#clear-expenses-filters");

  const PENCIL_SVG = `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zm2.92 2.33H5v-.92L14.06 7.52l.92.92L5.92 19.58zM20.71 7.04a1 1 0 0 0 0-1.41l-2.34-2.34a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>`;
  const TRASH_SVG  = `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 7h12v13a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V7zm3-4h6l1 1h4v2H4V4h4l1-1zm1 6h2v9h-2V9zm4 0h2v9h-2V9z"/></svg>`;

  function showExpenseError(message) {
    if (!errorEl) return;
    errorEl.textContent = message;
    errorEl.classList.remove("hidden");
  }

  function clearExpenseError() {
    if (!errorEl) return;
    errorEl.textContent = "";
    errorEl.classList.add("hidden");
  }

  // categories
  const CANONICAL = [
    "Bills & Utilities","Education","Entertainment","Food & Dining","Gifts","Groceries","Health & Medical",
    "Insurance","Other","Personal Care","Savings","Shopping","Subscriptions","Transport","Travel",
  ];

  function catEmoji(name = "") {
    const k = name.toLowerCase();
    if (k.includes("food")) return "🍽️";
    if (k.includes("groc")) return "🛒";
    if (k.includes("trans")) return "🚌";
    if (k.includes("shop")) return "🛍️";
    if (k.includes("bill")) return "🧾";
    if (k.includes("enter")) return "🎬";
    if (k.includes("health") || k.includes("med")) return "💊";
    if (k.includes("educ")) return "🎓";
    if (k.includes("travel")) return "✈️";
    if (k.includes("gift")) return "🎁";
    if (k.includes("personal")) return "🧴";
    if (k.includes("subscr")) return "🔔";
    if (k.includes("insur")) return "🛡️";
    if (k.includes("saving")) return "💾";
    return "🧾";
  }

  async function ensureCanonical() {
    // Seed any missing canonical categories on the backend.
    const have = new Set((await getJSON("/api/categories", [])).map(c => c.name));
    for (const n of CANONICAL) {
      if (!have.has(n)) {
        await fetch("/api/categories", {
          method: "POST",
          headers: { "Content-Type": "application/json", accept: "application/json" },
          body: JSON.stringify({ name: n })
        }).catch(() => {});
      }
    }
  }

  let categories = [];
  let chart;
  let editingId = null;
  let allRows = [];
  let summary = { income_total: null, expense_total: null, balance: null };
  let tippingExpenseId = null;   // the single expense that pushed you over income

  async function fillSelect() {
    // Load all categories and populate the dropdown (sorted alphabetically).
    await ensureCanonical();
    const final = (await getJSON("/api/categories", [])).slice()
      .sort((a, b) => (a.name || "").localeCompare(b.name || ""));
    categories = final;
    inpCategory.innerHTML = [
      `<option value="">Select a category…</option>`,
      ...final.map(c => `<option value="${c.id}">${c.name}</option>`)
    ].join("");
  }

  function openModal(row = null) {
    // Show modal; if row provided, preload values for edit.
    modal.style.display = "flex";
    modal.setAttribute("aria-hidden", "false");

    const max = todayISO();
    if (inpDate) inpDate.max = max;

    if (row) {
      editingId = row.id;
      inpName.value = row.name || "";
      inpAmount.value = toNum(row.amount) || "";
      inpDate.value = row.date || max;
      inpNote.value = row.note || "";
      inpCategory.value = row.category_id || "";
    } else {
      editingId = null;
      inpName.value = "";
      inpAmount.value = "";
      inpNote.value = "";
      inpDate.value = max;
      inpCategory.value = "";
    }
    inpName.focus();
  }

  function closeModal() {
    // Hide modal and reset aria state.
    modal.style.display = "none";
    modal.setAttribute("aria-hidden", "true");
  }

  function renderList(rowsRaw) {
    // Render expense list (newest first) with optional warnings.
    const rows = (rowsRaw || []).sort((a, b) => parseISO(b.date) - parseISO(a.date));
    listEl.innerHTML = rows.length ? rows.map(r => {
      const cat = categories.find(c => c.id === r.category_id);
      const icon = catEmoji(cat?.name || "");
      const amountNum = toNum(r.amount);
      const flags = [];

      // 1) Only the *tipping* expense shows the "Exceeds balance" warning
      if (tippingExpenseId && r.id === tippingExpenseId && summary.income_total != null) {
        const totalExpenses = (allRows || []).reduce((a, x) => a + toNum(x.amount || 0), 0);
        const overshoot = totalExpenses - summary.income_total;
        if (overshoot > 0) {
          flags.push(`⚠️ Exceeds balance by ${money(overshoot)}`);
        }
      }

      // 2) "Large expense" stays per-row, exactly like before
      if (amountNum > LARGE_EXPENSE_THRESHOLD) {
        flags.push("⚠️ Large expense");
      }

      const flagsHTML = flags.length
        ? `<div class="expense-flags">${flags.map(f => `<span class="expense-flag">${f}</span>`).join("")}</div>`
        : "";
      return `
        <div class="row">
          <div class="row-left">
            <div class="bubble">${icon}</div>
            <div>
              <div class="title">${r.name || "Expense"}</div>
              <div style="color:var(--muted);font-size:.9rem;">
                ${r.date}${cat ? " · " + cat.name : ""}
              </div>
              ${flagsHTML}
            </div>
          </div>
          <div class="row-right">
            <span class="amount neg">-${money(amountNum)}</span>
            <div class="row-actions">
              <button class="icon-btn" data-act="edit" data-id="${r.id}" title="Edit">${PENCIL_SVG}</button>
              <button class="icon-btn" data-act="del"  data-id="${r.id}" title="Delete">${TRASH_SVG}</button>
            </div>
          </div>
        </div>`;
    }).join("") : `<div class="row"><div class="title">No expenses yet.</div></div>`;

    listEl.querySelectorAll(".icon-btn").forEach(btn => {
      const id = Number(btn.dataset.id);
      const act = btn.dataset.act;
      const row = rows.find(x => x.id === id);
      btn.onclick = async () => {
        if (act === "edit") return openModal(row);
        if (act === "del") {
          if (!confirm("Delete this expense permanently?\n\nThis action cannot be undone.")) return;
          const res = await fetch(`/api/expenses/${id}`, { method: "DELETE" });
          if (!res.ok) {
            const msg = await httpText(res);
            return showExpenseError("Delete failed: " + msg);
          }
          loadAll();
        }
      };
    });
  }

  function renderBar(items) {
    // Draw bar chart for last 10 expenses by date.
    const cv = document.getElementById("expense-line");
    if (!cv) return;
    const last10 = (items || [])
      .filter(r => r.date)
      .sort((a, b) => parseISO(a.date) - parseISO(b.date))
      .slice(-10);
    const labels = last10.map(r => fmtDay(r.date));
    const values = last10.map(r => toNum(r.amount));
    if (chart) chart.destroy();
    chart = new Chart(cv.getContext("2d"), {
      type: "bar",
      data: { labels, datasets: [{ data: values, borderWidth: 0 }] },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { x: { grid: { display: false } }, y: { beginAtZero: true } }
      }
    });
  }

  function getFilteredExpenseRows() {
    const fromVal = inpFrom?.value || "";
    const toVal = inpTo?.value || "";
    const q = (inpSearch?.value || "").trim().toLowerCase();

    const fromDate = parseFilterDate(fromVal);
    const toDate = parseFilterDate(toVal);

    return (allRows || []).filter(r => {
      if (!r.date) return false;
      const dIso = r.date;
      const dObj = parseISO(dIso);
      if (isNaN(dObj)) return false;

      if (fromDate && dObj < fromDate) return false;
      if (toDate && dObj > toDate) return false;

      if (q) {
        const name = (r.name || "").toLowerCase();
        const note = (r.note || "").toLowerCase();
        if (!name.includes(q) && !note.includes(q)) return false;
      }
      return true;
    });
  }

  function applyExpenseFiltersAndRender() {
    const fromVal = inpFrom?.value || "";
    const toVal = inpTo?.value || "";
    if (!isValidDateRange(fromVal, toVal)) {
      alert("From date must be earlier than or equal to To date.");
      renderBar([]);
      renderList([]);
      return;
    }

    const rows = getFilteredExpenseRows();
    renderBar(rows);
    renderList(rows);
  }

  function exportExpensesCSV() {
    if (!allRows.length) {
      showExpenseError("No expense data to export yet.");
      return;
    }
    const rows = getFilteredExpenseRows();
    if (!rows.length) {
      showExpenseError("No expenses match the current filters.");
      return;
    }

    const header = ["id","name","amount","date","category","note"];
    const lines = [header.join(",")];

    rows.forEach(r => {
      const cat = categories.find(c => c.id === r.category_id)?.name || "";
      const vals = [
        r.id,
        (r.name || "").replace(/"/g,'""'),
        toNum(r.amount),
        r.date || "",
        cat.replace(/"/g,'""'),
        (r.note || "").replace(/"/g,'""')
      ];
      const line = vals.map(v => `"${String(v)}"`).join(",");
      lines.push(line);
    });

    const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "expenses.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  function renderExpenseStats(rowsRaw) {
    if (!statsEl) return;
    const rows = rowsRaw || [];
    const now = new Date();
    const ymNow = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,"0")}`;

    let totalThisMonth = 0;
    const sumsByMonth = new Map();
    const sumsByName = new Map();

    rows.forEach(r => {
      if (!r.date) return;
      const d = parseISO(r.date);
      if (isNaN(d)) return;

      const ym = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}`;
      const amt = toNum(r.amount);

      sumsByMonth.set(ym, (sumsByMonth.get(ym) || 0) + amt);
      if (ym === ymNow) totalThisMonth += amt;

      const key = (r.name || "Expense").trim() || "Expense";
      sumsByName.set(key, (sumsByName.get(key) || 0) + amt);
    });

    const totalAll = [...sumsByMonth.values()].reduce((a,b)=>a+b,0);
    const monthCount = sumsByMonth.size || 1;
    const avgPerMonth = totalAll / monthCount;

    let biggest = "—";
    if (sumsByName.size) {
      const [name, value] =
        [...sumsByName.entries()].sort((a,b)=>b[1]-a[1])[0];
      biggest = `${name} (${money(value)})`;
    }

    const spans = statsEl.querySelectorAll(".value-strong");
    if (spans[0]) spans[0].textContent = money(totalThisMonth);
    if (spans[1]) spans[1].textContent = money(avgPerMonth);
    if (spans[2]) spans[2].textContent = biggest;
  }

  async function loadSummary() {
    const s = await getJSON("/api/stats/summary", null);
    if (s && typeof s === "object") {
      const income = Number(s.income_total);
      const expense = Number(s.expense_total);
      const balance = Number(s.balance);
      summary = {
        income_total: Number.isFinite(income) ? income : null,
        expense_total: Number.isFinite(expense) ? expense : null,
        balance: Number.isFinite(balance) ? balance : null,
      };
    } else {
      summary = { income_total: null, expense_total: null, balance: null };
    }
  }

  function computeTippingExpenseId() {
    tippingExpenseId = null;

    const incomeTotal = Number.isFinite(summary.income_total)
      ? summary.income_total
      : null;

    // If we don't know total income, we can't decide anything
    if (incomeTotal === null) return;

    // Sort all expenses by date (oldest → newest)
    const sorted = (allRows || [])
      .filter(r => r.date)
      .slice()
      .sort((a, b) => parseISO(a.date) - parseISO(b.date));

    let running = 0;
    for (const r of sorted) {
      running += toNum(r.amount || 0);
      if (running > incomeTotal) {
        // This is the first expense that makes total expenses > total income
        tippingExpenseId = r.id;
        break;
      }
    }
  }

  async function saveExpense() {
    // Validate, then create or update an expense record.
    const name   = (inpName.value || "").trim();
    const amount = parseFloat(inpAmount.value);
    const date   = toISODate(inpDate.value);
    const catId  = parseInt(inpCategory.value, 10);
    const note   = (inpNote.value || "").trim() || null;

    if (!name) return alert("Please enter a name.");
    if (!amount || amount <= 0) return alert("Please enter a positive amount.");
    if (!date) return alert("Please pick a date (YYYY-MM-DD).");
    if (date > todayISO()) return alert("Date cannot be in the future.");
    if (!catId) return alert("Please select a category.");

    const payload = { name, amount, date, note, category_id: catId };
    const url = editingId == null ? "/api/expenses" : `/api/expenses/${editingId}`;
    const method = editingId == null ? "POST" : "PATCH";

    const res = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json", accept: "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const msg = await httpText(res);
      return alert("Save failed: " + msg);
    }

    closeModal();
    editingId = null;
    loadAll();
  }

  async function loadAll() {
    await fillSelect();
    await loadSummary();
    allRows = await getJSON("/api/expenses", []);
    computeTippingExpenseId();      // 🔹 decide which expense gets the warning
    renderExpenseStats(allRows);
    applyExpenseFiltersAndRender();
  }

  // events
  btnRefresh?.addEventListener("click", loadAll);
  btnExport?.addEventListener("click", exportExpensesCSV);

  inpFrom?.addEventListener("change", applyExpenseFiltersAndRender);
  inpTo?.addEventListener("change", applyExpenseFiltersAndRender);
  inpSearch?.addEventListener("input", applyExpenseFiltersAndRender);
  btnClearFilters?.addEventListener("click", () => {
    if (inpFrom) inpFrom.value = "";
    if (inpTo) inpTo.value = "";
    if (inpSearch) inpSearch.value = "";
    applyExpenseFiltersAndRender();
  });

  btnOpen?.addEventListener("click", () => openModal(null));
  btnClose?.addEventListener("click", closeModal);
  btnCancel?.addEventListener("click", closeModal);
  btnSave?.addEventListener("click", saveExpense);
  modal?.addEventListener("click", (e) => { if (e.target.id === "exp-modal-backdrop") closeModal(); });

  loadAll();
})();
}
