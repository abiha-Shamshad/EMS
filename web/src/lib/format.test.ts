import { strict as assert } from "node:assert";
import { test } from "node:test";

import { buildUrl, readCookie } from "./api.ts";
import { date, initials, label, minutes, money, percent, sumMoney } from "./format.ts";

test("money keeps decimal strings exact", () => {
  assert.equal(money("8620.00"), "$8,620.00");
  assert.equal(money("1234567.5"), "$1,234,567.50");
  assert.equal(money("0.1", "PKR"), "PKR 0.10");
  assert.equal(money("-25.00"), "-$25.00");
  assert.equal(money(null), "—");
});

test("sumMoney adds decimal strings exactly", () => {
  assert.equal(sumMoney(["0.10", "0.20"]), "0.30");
  assert.equal(sumMoney(["12000.00", "9500.5", null, "-0.5"]), "21500.00");
  assert.equal(sumMoney([]), "0.00");
});

test("calendar dates are not shifted by time zones", () => {
  assert.equal(date("2026-10-12"), "12 Oct 2026");
});

test("labels, minutes, initials and percent", () => {
  assert.equal(label("ceo"), "CEO");
  assert.equal(label("on_break"), "On break");
  assert.equal(minutes(412), "6 h 52 min");
  assert.equal(minutes(45), "45 min");
  assert.equal(initials("Imran Qureshi"), "IQ");
  assert.equal(percent("0.36"), "36%");
});

test("api helpers", () => {
  assert.equal(buildUrl("/members", { limit: 25, cursor: null, q: "" }), "/api/v1/members?limit=25");
  assert.equal(readCookie("ems_csrf", "a=1; ems_csrf=abc%3D; b=2"), "abc=");
  assert.equal(readCookie("missing", "a=1"), null);
});
