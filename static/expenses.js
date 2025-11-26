/**
 * expenses.js
 * - Ensures canonical categories
 * - No duplicate rows on edit (PATCH when editingId != null)
 * - Accepts dd/mm/yyyy or yyyy-mm-dd; blocks future dates
 * - Newest -> Oldest; small bar chart stays in sync
 * - Adds: stats, filters, CSV export
 */

if (window.__EXPENSES_APP_INITIALIZED__) {
  console.warn("expenses.js already initialized; skipping duplicate load");
} else {
  window.__EXPENSES_APP_INITIALIZED__ = true;

(function () {
  // ---- helpers ----
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

  // ---- UI pieces ----
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

  // categories
  const CANONICAL = [
    "Bills & Utilities","Education","Entertainment","Food & Dining","Gifts","Groceries","Health & Medical",
    "Insurance","Other","Personal Care","Savings","Shopping","Subscriptions","Transport","Travel",
  ];
  const HIDE = new Set(["bills", "food", "shopping"]);

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

  async function fillSelect() {
    await ensureCanonical();
    const all = await getJSON("/api/categories", []);
    const byLower = new Map();
    all.forEach(c => {
      const k = (c.name || "").toLowerCase();
      if (!byLower.has(k)) byLower.set(k, []);
      byLower.get(k).push(c);
    });
    const final = [];
    for (const name of CANONICAL) {
      const low = name.toLowerCase();
      if (HIDE.has(low)) continue;
      const group = byLower.get(low);
      if (!group || !group.length) continue;
      const exact = group.find(g => g.name === name);
      final.push(exact || group[0]);
    }
    final.sort((a, b) => a.name.localeCompare(b.name));
    categories = final;
    inpCategory.innerHTML = [
      `<option value="">Select a category…</option>`,
      ...final.map(c => `<option value="${c.id}">${c.name}</option>`)
    ].join("");
  }

  function openModal(row = null) {
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
    modal.style.display = "none";
    modal.setAttribute("aria-hidden", "true");
  }

  function renderList(rowsRaw) {
    const rows = (rowsRaw || []).sort((a, b) => parseISO(b.date) - parseISO(a.date));
    listEl.innerHTML = rows.length ? rows.map(r => {
      const cat = categories.find(c => c.id === r.category_id);
      const icon = catEmoji(cat?.name || "");
      return `
        <div class="row">
          <div class="row-left">
            <div class="bubble">${icon}</div>
            <div>
              <div class="title">${r.name || "Expense"}</div>
              <div style="color:var(--muted);font-size:.9rem;">
                ${r.date}${cat ? " · " + cat.name : ""}
              </div>
            </div>
          </div>
          <div class="row-right">
            <span class="amount neg">-${money(toNum(r.amount))}</span>
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
          if (!res.ok) return alert("Delete failed: " + (await httpText(res)));
          loadAll();
        }
      };
    });
  }

  function renderBar(items) {
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

    return (allRows || []).filter(r => {
      if (!r.date) return false;
      const d = r.date;

      if (fromVal && d < fromVal) return false;
      if (toVal && d > toVal) return false;

      if (q) {
        const name = (r.name || "").toLowerCase();
        const note = (r.note || "").toLowerCase();
        if (!name.includes(q) && !note.includes(q)) return false;
      }
      return true;
    });
  }

  function applyExpenseFiltersAndRender() {
    const rows = getFilteredExpenseRows();
    renderBar(rows);
    renderList(rows);
  }

  function exportExpensesCSV() {
    if (!allRows.length) {
      alert("No expense data to export yet.");
      return;
    }
    const rows = getFilteredExpenseRows();
    if (!rows.length) {
      alert("No expenses match the current filters.");
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

  async function saveExpense() {
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
    if (!res.ok) return alert("Save failed: " + (await httpText(res)));

    closeModal();
    editingId = null;
    loadAll();
  }

  async function loadAll() {
    await fillSelect();
    allRows = await getJSON("/api/expenses", []);
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








