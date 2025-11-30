/**
 * income.js
 * Handles income CRUD, filtering, stats, and chart rendering with inline validation.
 * Accepts dd/mm/yyyy or yyyy-mm-dd, blocks future dates, and keeps list/chart in sync.
 */

if (window.__INCOME_APP_INITIALIZED__) {
  console.warn("income.js already initialized; skipping duplicate load");
} else {
  window.__INCOME_APP_INITIALIZED__ = true;

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
    let raw = "";
    try { raw = await res.text(); } catch {}
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

  // Convert dd/mm/yyyy or ISO to Date; returns null on bad input.
  function parseFilterDate(str) {
    if (!str) return null;
    if (/^\d{4}-\d{2}-\d{2}$/.test(str)) {
      const d = new Date(str);
      return isNaN(d) ? null : d;
    }
    const m = str.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
    if (m) {
      const [_, dd, mm, yy] = m;
      const d = new Date(parseInt(yy, 10), parseInt(mm, 10) - 1, parseInt(dd, 10));
      return isNaN(d) ? null : d;
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

  function toISODate(s) {
    if (!s) return "";
    if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
    const m = s.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
    return m ? `${m[3]}-${m[2]}-${m[1]}` : s;
  }

  // elements 
  const listEl = $("#income-list");
  const btnRefresh = $("#refresh");
  const btnExport = $("#export-income");

  const inpFrom = $("#income-from");
  const inpTo = $("#income-to");
  const inpSearch = $("#income-search");
  const statsEl = $("#income-stats");
  const btnClearFilters = $("#clear-income-filters");

  const modal = $("#inc-modal-backdrop");
  const btnOpen = $("#add-income");
  const btnClose = $("#close-inc-modal");
  const btnCancel = $("#cancel-inc-modal");
  const btnSave = $("#save-income");
  const inpName = $("#in-name");
  const inpAmount = $("#in-amount");
  const inpDate = $("#in-date");
  const inpNote = $("#in-note");
  const errorEl = document.getElementById("income-form-error");

  const PENCIL_SVG = `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zm2.92 2.33H5v-.92L14.06 7.52l.92.92L5.92 19.58zM20.71 7.04a1 1 0 0 0 0-1.41l-2.34-2.34a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>`;
  const TRASH_SVG  = `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 7h12v13a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V7zm3-4h6l1 1h4v2H4V4h4l1-1zm1 6h2v9h-2V9zm4 0h2v9h-2V9z"/></svg>`;

  let editingId = null;  // null = create, number = edit existing
  let chart;
  let allRows = [];      // full dataset from API

  function openModal(row = null) {
    // keep inline error cleared when opening
    clearIncomeError();
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
    } else {
      editingId = null;
      inpName.value = "";
      inpAmount.value = "";
      inpNote.value = "";
      inpDate.value = max;
    }
    inpName.focus();
  }

  function closeModal() {
    modal.style.display = "none";
    modal.setAttribute("aria-hidden", "true");
    clearIncomeError();
  }


  function showIncomeError(message) {
    if (!errorEl) return;
    errorEl.textContent = message;
    errorEl.classList.remove("hidden");
  }

  function clearIncomeError() {
    if (!errorEl) return;
    errorEl.textContent = "";
    errorEl.classList.add("hidden");
  }

  function renderList(rowsRaw) {
    const rows = (rowsRaw || []).sort((a, b) => parseISO(b.date) - parseISO(a.date));
    listEl.innerHTML = rows.length ? rows.map(r => `
      <div class="row">
        <div class="row-left">
          <div class="bubble">💼</div>
          <div>
            <div class="title">${r.name || "Income"}</div>
            <div style="color:var(--muted);font-size:.9rem;">${r.date}</div>
          </div>
        </div>
        <div class="row-right">
          <span class="amount text-income">+${money(toNum(r.amount))}</span>
          <div class="row-actions">
            <button class="icon-btn" data-act="edit" data-id="${r.id}" title="Edit">${PENCIL_SVG}</button>
            <button class="icon-btn" data-act="del"  data-id="${r.id}" title="Delete">${TRASH_SVG}</button>
          </div>
        </div>
      </div>
    `).join("") : `<div class="row"><div class="title">No income yet.</div></div>`;

    listEl.querySelectorAll(".icon-btn").forEach(btn => {
      const id = Number(btn.dataset.id);
      const act = btn.dataset.act;
      const row = rows.find(x => x.id === id);
      btn.onclick = async () => {
        if (act === "edit") return openModal(row);
        if (act === "del") {
          if (!confirm("Delete this income permanently?\n\nThis action cannot be undone.")) return;
          const res = await fetch(`/api/income/${id}`, { method: "DELETE" });
          if (!res.ok) {
            const msg = await httpText(res);
            return showIncomeError("Delete failed: " + msg);
          }
          loadAll();
        }
      };
    });
  }

  function renderBar(items) {
    const cv = document.getElementById("income-bar");
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

  function getFilteredIncomeRows() {
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

  function applyIncomeFiltersAndRender() {
    const fromVal = inpFrom?.value || "";
    const toVal = inpTo?.value || "";
    if (!isValidDateRange(fromVal, toVal)) {
      alert("From date must be earlier than or equal to To date.");
      renderBar([]);
      renderList([]);
      return;
    }

    const rows = getFilteredIncomeRows();
    renderBar(rows);
    renderList(rows);
  }

  function exportIncomeCSV() {
    if (!allRows.length) {
      showIncomeError("No income data to export yet.");
      return;
    }
    const rows = getFilteredIncomeRows();
    if (!rows.length) {
      showIncomeError("No income matches the current filters.");
      return;
    }

    const header = ["id", "name", "amount", "date", "note"];
    const lines = [header.join(",")];

    rows.forEach(r => {
      const vals = [
        r.id,
        (r.name || "").replace(/"/g, '""'),
        toNum(r.amount),
        r.date || "",
        (r.note || "").replace(/"/g, '""')
      ];
      const line = vals.map(v => `"${String(v)}"`).join(",");
      lines.push(line);
    });

    const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "income.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  function renderIncomeStats(rowsRaw) {
    if (!statsEl) return;
    const rows = rowsRaw || [];
    const now = new Date();
    const ymNow = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;

    let totalThisMonth = 0;
    const sumsByMonth = new Map();
    const sumsBySource = new Map();

    rows.forEach(r => {
      if (!r.date) return;
      const d = parseISO(r.date);
      if (isNaN(d)) return;

      const ym = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
      const amt = toNum(r.amount);

      sumsByMonth.set(ym, (sumsByMonth.get(ym) || 0) + amt);
      if (ym === ymNow) totalThisMonth += amt;

      const key = (r.name || "Income").trim() || "Income";
      sumsBySource.set(key, (sumsBySource.get(key) || 0) + amt);
    });

    const totalAll = [...sumsByMonth.values()].reduce((a, b) => a + b, 0);
    const monthCount = sumsByMonth.size || 1;
    const avgPerMonth = totalAll / monthCount;

    let bestSource = "—";
    if (sumsBySource.size) {
      const [name, value] =
        [...sumsBySource.entries()].sort((a, b) => b[1] - a[1])[0];
      bestSource = `${name} (${money(value)})`;
    }

    const spans = statsEl.querySelectorAll(".value-strong");
    if (spans[0]) spans[0].textContent = money(totalThisMonth);
    if (spans[1]) spans[1].textContent = money(avgPerMonth);
    if (spans[2]) spans[2].textContent = bestSource;
  }

  async function saveIncome() {
    const name   = (inpName.value || "").trim();
    const amount = parseFloat(inpAmount.value);
    const date   = toISODate(inpDate.value);
    const note   = (inpNote.value || "").trim() || null;

    clearIncomeError();

    if (!name) return showIncomeError("Please enter a name.");
    if (!amount || amount <= 0) return showIncomeError("Amount must be positive.");
    if (!date) return showIncomeError("Please pick a date (YYYY-MM-DD).");
    if (date > todayISO()) return showIncomeError("Date cannot be in the future.");

    const payload = { name, amount, date, note };
    const url = editingId == null ? "/api/income" : `/api/income/${editingId}`;
    const method = editingId == null ? "POST" : "PATCH";

    const res = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json", accept: "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const msg = await httpText(res);
      return showIncomeError("Save failed: " + msg);
    }

    closeModal();
    editingId = null;
    loadAll();
  }

  async function loadAll() {
    allRows = await getJSON("/api/income", []);
    renderIncomeStats(allRows);
    applyIncomeFiltersAndRender();
  }

  // events
  btnRefresh?.addEventListener("click", loadAll);
  btnOpen?.addEventListener("click", () => openModal(null));
  btnClose?.addEventListener("click", closeModal);
  btnCancel?.addEventListener("click", closeModal);
  btnSave?.addEventListener("click", saveIncome);
  modal?.addEventListener("click", (e) => {
    if (e.target.id === "inc-modal-backdrop") closeModal();
  });

  btnExport?.addEventListener("click", exportIncomeCSV);

  // filters trigger re-render
  inpFrom?.addEventListener("change", applyIncomeFiltersAndRender);
  inpTo?.addEventListener("change", applyIncomeFiltersAndRender);
  inpSearch?.addEventListener("input", applyIncomeFiltersAndRender);

  // reset filters
  btnClearFilters?.addEventListener("click", () => {
    if (inpFrom) inpFrom.value = "";
    if (inpTo) inpTo.value = "";
    if (inpSearch) inpSearch.value = "";
    applyIncomeFiltersAndRender();
  });

  loadAll();
})();
}
