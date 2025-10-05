// Dashboard logic 
//  fetch totals from  API
// render 3 KPI numbers
// build a "Spending by Category" list
//  draw a donut chart with Chart.js
(async function () {
  // ---- helpers ----
  const $ = (sel) => document.querySelector(sel);                // quick DOM picker
  const money = (n) => (+n || 0).toLocaleString(undefined, {     // € formatting
    style: "currency", currency: "EUR"
  });
  const toNum = (x) => (typeof x === "string" ? parseFloat(x) : +x || 0);

  // fetch JSON with a safe fallback (never crash UI)
  async function getJSON(url, fallback = []) {
    try {
      const res = await fetch(url, { headers: { accept: "application/json" } });
      if (!res.ok) return fallback;
      return await res.json();
    } catch {
      return fallback;
    }
  }

  //  will update these spots in the HTML 
  const elIncome   = $("#kpi-income");
  const elExpense  = $("#kpi-expense");
  const elBalance  = $("#kpi-balance");
  const elCatList  = $("#category-list");
  const btnRefresh = $("#refresh");

  //  draw the donut chart (Chart.js) 
  let donut; // keep a reference so we can re-draw on refresh
  function renderDonut(totalIncome, totalExpense, balance) {
    const canvas = document.getElementById("donut");
    if (!canvas) return;

    // remove old chart if it exists
    if (donut) donut.destroy();

    donut = new Chart(canvas.getContext("2d"), {
      type: "doughnut",
      data: {
        labels: ["Total Balance", "Total Expenses", "Total Income"],
        datasets: [{
          data: [Math.max(balance, 0), totalExpense, totalIncome],
          backgroundColor: ["#7c3aed", "#ef4444", "#f59e0b"],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "68%",
        plugins: { legend: { position: "bottom" } }
      }
    });
  }

  //  build the "Spending by Category" list 
  function renderCategoryList(expenses, categories) {
    if (!elCatList) return;

    // make a quick map: id -> name
    const nameById = new Map((categories || []).map(c => [c.id, c.name]));
    // add up totals per category name
    const totals = new Map(); // name -> sum

    for (const e of expenses || []) {
      const catName = nameById.get(e.category_id ?? null) || "Uncategorized";
      totals.set(catName, (totals.get(catName) || 0) + toNum(e.amount));
    }

    // convert map to array and sort by biggest spend
    const rows = [...totals.entries()]
      .map(([name, sum]) => ({ name, sum }))
      .sort((a,b) => b.sum - a.sum);

    // write rows to HTML
    elCatList.innerHTML = rows.length
      ? rows.map(r => `
          <div class="row">
            <div class="row-left">
              <div class="bubble">🧾</div>
              <div class="title">${r.name}</div>
            </div>
            <div class="row-right">
              <span class="amount neg">-${money(r.sum)}</span>
            </div>
          </div>
        `).join("")
      : `<div class="row"><div class="title">No expenses yet.</div></div>`;
  }

  // load everything from the API and update the page 
  async function loadAll() {
    // get income, expenses, categories at the same time
    const [income, expenses, cats] = await Promise.all([
      getJSON("/api/income", []),
      getJSON("/api/expenses", []),
      getJSON("/api/categories", []),
    ]);

    // compute totals
    const totalIncome  = (income   || []).reduce((a,x)=> a + toNum(x.amount), 0);
    const totalExpense = (expenses || []).reduce((a,x)=> a + toNum(x.amount), 0);
    const balance      = totalIncome - totalExpense;

    // put numbers on the page
    if (elIncome)  elIncome.textContent  = money(totalIncome);
    if (elExpense) elExpense.textContent = money(totalExpense);
    if (elBalance) elBalance.textContent = money(balance);

    // build list + chart
    renderCategoryList(expenses, cats);
    renderDonut(totalIncome, totalExpense, balance);
  }

  // refresh button + initial load
  btnRefresh?.addEventListener("click", loadAll);
  loadAll();
})();


