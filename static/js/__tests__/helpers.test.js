const {
  money,
  toNum,
  daysAgo,
  pickExp30Records,
  pickInc60Records,
} = require("../helpers");

// ---------------------------
// 🧪 money()
// ---------------------------

describe("money()", () => {
  test("formats a number into EUR currency", () => {
    // Arrange
    const input = 1234.5;

    // Act
    const result = money(input);

    // Assert
    expect(result).toMatch("€1,234.50");
  });

  test("formats zero correctly", () => {
    // Arrange
    const input = 0;

    // Act
    const result = money(input);

    // Assert
    expect(result).toBe("€0.00");
  });
});

// ---------------------------
// 🧪 toNum()
// ---------------------------

describe("toNum()", () => {
  test("converts valid numeric string", () => {
    expect(toNum("12.50")).toBe(12.5);
  });

  test("converts number to number", () => {
    expect(toNum(42)).toBe(42);
  });

  test("returns NaN for invalid input", () => {
    expect(toNum("invalid")).toBeNaN();
    });

});

// ---------------------------
// 🧪 daysAgo()
// ---------------------------

describe("daysAgo()", () => {
  test("returns correct difference in days", () => {
    // Arrange
    const today = new Date();
    const yesterday = new Date(today.getTime() - 1 * 24 * 60 * 60 * 1000)
      .toISOString()
      .split("T")[0];

    // Act
    const result = daysAgo(yesterday);

    // Assert
    expect(result).toBe(1);
  });

  test("returns Infinity for invalid date", () => {
    expect(daysAgo("not-a-date")).toBe(Infinity);
  });
});

// ---------------------------
// 🧪 pickExp30Records()
// ---------------------------

describe("pickExp30Records()", () => {
  test("returns only expenses from last 30 days, max 4, sorted newest-first", () => {
    // Arrange
    const today = new Date();
    const makeDate = (days) =>
      new Date(today.getTime() - days * 24 * 60 * 60 * 1000)
        .toISOString()
        .split("T")[0];

    const expenses = [
      { name: "Old", amount: 50, date: makeDate(40) },
      { name: "R1", amount: 20, date: makeDate(1) },
      { name: "R2", amount: 30, date: makeDate(5) },
      { name: "R3", amount: 40, date: makeDate(10) },
      { name: "R4", amount: 50, date: makeDate(20) },
      { name: "R5", amount: 60, date: makeDate(3) },
    ];

    // Act
    const result = pickExp30Records(expenses);

    // Assert
    expect(result.length).toBe(4);
    expect(result.find((e) => e.name === "Old")).toBeUndefined();

    // ensure newest-first
    const timestamps = result.map((r) => new Date(r.date).getTime());
    for (let i = 0; i < timestamps.length - 1; i++) {
      expect(timestamps[i]).toBeGreaterThanOrEqual(timestamps[i + 1]);
    }
  });
});

// ---------------------------
// 🧪 pickInc60Records()
// ---------------------------

describe("pickInc60Records()", () => {
  test("selects top 4 income rows by amount within 60 days", () => {
    // Arrange
    const today = new Date();
    const makeDate = (days) =>
      new Date(today.getTime() - days * 24 * 60 * 60 * 1000)
        .toISOString()
        .split("T")[0];

    const items = [
      { name: "Old", amount: 5000, date: makeDate(100) }, // too old
      { name: "I1", amount: 100, date: makeDate(1) },
      { name: "I2", amount: 500, date: makeDate(2) },
      { name: "I3", amount: 200, date: makeDate(3) },
      { name: "I4", amount: 300, date: makeDate(4) },
      { name: "I5", amount: 800, date: makeDate(5) },
    ];

    // Act
    const result = pickInc60Records(items);

    // Assert
    expect(result.length).toBe(4);
    expect(result.find((e) => e.name === "Old")).toBeUndefined();

    // check sorted by amount (desc)
    const amounts = result.map((r) => r.amount);
    for (let i = 0; i < amounts.length - 1; i++) {
      expect(amounts[i]).toBeGreaterThanOrEqual(amounts[i + 1]);
    }
  });
});

