// helpers.js- pure testable functions extracted from script.js

function money(n) {
  return (+n || 0).toLocaleString(undefined, {
    style: "currency",
    currency: "EUR",
  });
}

function toNum(x) {
  return typeof x === "string" ? parseFloat(x) : +x || 0;
}

function daysAgo(iso) {
  const d = new Date(iso);
  if (isNaN(d)) return Infinity;
  const ONE = 24 * 60 * 60 * 1000;
  return Math.floor((Date.now() - d.getTime()) / ONE);
}

function pickExp30Records(expenses) {
  const parseISO = (d) => new Date(d);
  return (expenses || [])
    .filter((r) => r.date && daysAgo(r.date) <= 30)
    .sort((a, b) => parseISO(b.date) - parseISO(a.date))
    .slice(0, 4);
}

function pickInc60Records(income) {
  const parseISO = (d) => new Date(d);
  const toNumSafe = (x) => (typeof x === "string" ? parseFloat(x) : +x || 0);

  return (income || [])
    .filter((r) => r.date && daysAgo(r.date) <= 60)
    .sort((a, b) => toNumSafe(b.amount) - toNumSafe(a.amount)) // highest first
    .slice(0, 4);
}

module.exports = {
  money,
  toNum,
  daysAgo,
  pickExp30Records,
  pickInc60Records,
};

