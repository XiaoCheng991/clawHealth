/* ============================================================
   ClawHealth – Frontend JavaScript
   ============================================================ */

"use strict";

// ---------------------------------------------------------------------------
// Tab navigation
// ---------------------------------------------------------------------------
const TABS = ["dashboard", "watch", "food", "goals"];
let activeTab = "dashboard";

function showTab(name) {
  TABS.forEach((t) => {
    document.getElementById(`tab-${t}`).classList.toggle("d-none", t !== name);
  });
  document.querySelectorAll(".nav-link[data-tab]").forEach((el) => {
    el.classList.toggle("active", el.dataset.tab === name);
  });
  activeTab = name;
  if (name === "dashboard") loadDashboard();
  if (name === "watch") loadWatchRecords();
  if (name === "food") loadFoodTab();
  if (name === "goals") loadGoals();
}

document.querySelectorAll(".nav-link[data-tab]").forEach((el) => {
  el.addEventListener("click", (e) => {
    e.preventDefault();
    showTab(el.dataset.tab);
  });
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function fmtDate(isoStr) {
  if (!isoStr) return "—";
  const d = new Date(isoStr);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")} ` +
    `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function showAlert(elId, msg, type = "success") {
  const el = document.getElementById(elId);
  el.className = `alert alert-${type} py-2 small`;
  el.textContent = msg;
  el.classList.remove("d-none");
  setTimeout(() => el.classList.add("d-none"), 3000);
}

const MEAL_LABELS = { breakfast: "早餐", lunch: "午餐", dinner: "晚餐", snack: "加餐" };

// ---------------------------------------------------------------------------
// Chart instances (reuse/destroy)
// ---------------------------------------------------------------------------
const charts = {};

function destroyChart(id) {
  if (charts[id]) {
    charts[id].destroy();
    delete charts[id];
  }
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------
async function loadDashboard() {
  const days = parseInt(document.getElementById("dashDays").value, 10);

  const [summary, trend] = await Promise.all([
    fetch(`/api/health/summary?days=${days}`).then((r) => r.json()),
    fetch(`/api/health/trend?days=${days}`).then((r) => r.json()),
  ]);

  document.getElementById("sum-steps").textContent = summary.avg_steps ?? "—";
  document.getElementById("sum-hr").textContent = summary.avg_heart_rate ?? "—";
  document.getElementById("sum-cal").textContent = summary.avg_calories_burned ?? "—";
  document.getElementById("sum-sleep").textContent = summary.avg_sleep_hours ?? "—";
  document.getElementById("sum-spo2").textContent = summary.avg_blood_oxygen ?? "—";
  document.getElementById("sum-active").textContent = summary.avg_active_minutes ?? "—";

  const labels = trend.map((d) => d.date.slice(5));

  buildLineChart("chartSteps", labels, trend.map((d) => d.steps), "步数", "#0d6efd");
  buildLineChart("chartHR", labels, trend.map((d) => d.heart_rate), "心率 (bpm)", "#dc3545");
  buildLineChart("chartCal", labels, trend.map((d) => d.calories_burned), "消耗卡路里", "#fd7e14");
  buildLineChart("chartSleep", labels, trend.map((d) => d.sleep_hours), "睡眠 (h)", "#0dcaf0");
}

function buildLineChart(canvasId, labels, data, label, color) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId).getContext("2d");
  charts[canvasId] = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [{
        label,
        data,
        borderColor: color,
        backgroundColor: color + "22",
        tension: 0.4,
        fill: true,
        pointRadius: 3,
        spanGaps: true,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: false, grid: { color: "#e9ecef" } },
        x: { grid: { display: false } },
      },
    },
  });
}

document.getElementById("dashDays").addEventListener("change", loadDashboard);

// ---------------------------------------------------------------------------
// Apple Watch – Sync Form
// ---------------------------------------------------------------------------
(function initWatchForm() {
  // Set default datetime to now
  const dtInput = document.getElementById("sw-datetime");
  dtInput.value = new Date().toISOString().slice(0, 16);

  document.getElementById("btnFillDemo").addEventListener("click", () => {
    dtInput.value = new Date().toISOString().slice(0, 16);
    document.getElementById("sw-steps").value = Math.floor(6000 + Math.random() * 6000);
    document.getElementById("sw-hr").value = Math.floor(60 + Math.random() * 30);
    document.getElementById("sw-cal").value = Math.floor(300 + Math.random() * 400);
    document.getElementById("sw-active").value = Math.floor(20 + Math.random() * 60);
    document.getElementById("sw-sleep").value = (6 + Math.random() * 3).toFixed(1);
    document.getElementById("sw-spo2").value = (96 + Math.random() * 3).toFixed(1);
    const workouts = ["跑步", "步行", "骑行", "游泳", "力量训练", "瑜伽"];
    document.getElementById("sw-workout").value = workouts[Math.floor(Math.random() * workouts.length)];
    document.getElementById("sw-workout-dur").value = Math.floor(20 + Math.random() * 60);
  });

  document.getElementById("syncForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      recorded_at: document.getElementById("sw-datetime").value,
      steps: parseInt(document.getElementById("sw-steps").value) || 0,
      heart_rate: parseFloat(document.getElementById("sw-hr").value) || null,
      calories_burned: parseInt(document.getElementById("sw-cal").value) || 0,
      active_minutes: parseInt(document.getElementById("sw-active").value) || 0,
      sleep_hours: parseFloat(document.getElementById("sw-sleep").value) || null,
      blood_oxygen: parseFloat(document.getElementById("sw-spo2").value) || null,
      workout_type: document.getElementById("sw-workout").value || null,
      workout_duration: parseInt(document.getElementById("sw-workout-dur").value) || 0,
    };

    const res = await fetch("/api/health/sync", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (res.ok) {
      showAlert("syncAlert", "✓ 数据同步成功！");
      loadWatchRecords();
    } else {
      const err = await res.json();
      showAlert("syncAlert", `同步失败：${err.error || res.statusText}`, "danger");
    }
  });

  document.getElementById("btnLoadRecords").addEventListener("click", loadWatchRecords);
})();

async function loadWatchRecords() {
  const data = await fetch("/api/health/data?limit=20").then((r) => r.json());
  const tbody = document.getElementById("watchTableBody");
  if (!data.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">暂无数据</td></tr>';
    return;
  }
  tbody.innerHTML = data.map((r) => `
    <tr>
      <td>${fmtDate(r.recorded_at)}</td>
      <td>${r.steps ?? "—"}</td>
      <td>${r.heart_rate ?? "—"}</td>
      <td>${r.calories_burned ?? "—"}</td>
      <td>${r.sleep_hours != null ? r.sleep_hours + " h" : "—"}</td>
      <td>${r.blood_oxygen != null ? r.blood_oxygen + "%" : "—"}</td>
      <td>${r.workout_type ? `${r.workout_type} ${r.workout_duration ? r.workout_duration + "min" : ""}` : "—"}</td>
    </tr>
  `).join("");
}

// ---------------------------------------------------------------------------
// Food Analysis
// ---------------------------------------------------------------------------
let macroChart = null;
let foodTrendChart = null;

function initFoodDatePicker() {
  const today = new Date().toISOString().slice(0, 10);
  const el = document.getElementById("food-date");
  if (!el.value) el.value = today;
}

async function loadFoodTab() {
  initFoodDatePicker();
  await refreshFoodData();
  await loadFoodTrend();
}

async function refreshFoodData() {
  const date = document.getElementById("food-date").value || new Date().toISOString().slice(0, 10);
  const analysis = await fetch(`/api/food/analysis?date=${date}`).then((r) => r.json());

  document.getElementById("food-total-cal").textContent = analysis.total_calories;
  document.getElementById("food-total-protein").textContent = analysis.total_protein_g + "g";
  document.getElementById("food-total-carbs").textContent = analysis.total_carbs_g + "g";
  document.getElementById("food-total-fat").textContent = analysis.total_fat_g + "g";

  const pct = Math.min(100, Math.round((analysis.total_calories / (analysis.calorie_goal || 2000)) * 100));
  document.getElementById("food-cal-bar").style.width = pct + "%";

  renderMacroChart(analysis);
  renderFoodTable(analysis);
}

async function loadFoodTrend() {
  const trend = await fetch("/api/food/trend?days=7").then((r) => r.json());
  const labels = trend.map((d) => d.date.slice(5));
  const data = trend.map((d) => d.calories);

  if (foodTrendChart) { foodTrendChart.destroy(); foodTrendChart = null; }
  const ctx = document.getElementById("chartFoodTrend").getContext("2d");
  foodTrendChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "热量摄入 (kcal)",
        data,
        backgroundColor: "#ffc10788",
        borderColor: "#ffc107",
        borderWidth: 1,
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false }, title: { display: true, text: "近 7 天热量摄入", font: { size: 12 } } },
      scales: { y: { beginAtZero: true }, x: { grid: { display: false } } },
    },
  });
}

function renderMacroChart(analysis) {
  if (macroChart) { macroChart.destroy(); macroChart = null; }
  const ctx = document.getElementById("chartMacros").getContext("2d");
  macroChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["蛋白质", "碳水化合物", "脂肪"],
      datasets: [{
        data: [analysis.total_protein_g, analysis.total_carbs_g, analysis.total_fat_g],
        backgroundColor: ["#0d6efd", "#198754", "#dc3545"],
        hoverOffset: 4,
      }],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: "bottom", labels: { font: { size: 11 } } },
        title: { display: true, text: "三大营养素比例", font: { size: 12 } },
      },
    },
  });
}

function renderFoodTable(analysis) {
  const tbody = document.getElementById("foodTableBody");
  const allEntries = Object.values(analysis.entries_by_meal).flat();
  if (!allEntries.length) {
    tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-4">暂无记录</td></tr>';
    return;
  }
  const mealOrder = ["breakfast", "lunch", "dinner", "snack"];
  const sorted = allEntries.slice().sort((a, b) =>
    mealOrder.indexOf(a.meal_type) - mealOrder.indexOf(b.meal_type)
  );
  tbody.innerHTML = sorted.map((e) => `
    <tr>
      <td><span class="badge bg-secondary">${MEAL_LABELS[e.meal_type] || e.meal_type}</span></td>
      <td>${e.food_name}</td>
      <td>${e.amount_g}</td>
      <td>${e.calories}</td>
      <td>${e.protein_g}g</td>
      <td>${e.carbs_g}g</td>
      <td>${e.fat_g}g</td>
      <td>
        <button class="btn btn-sm btn-outline-danger py-0 px-1" onclick="deleteFoodEntry(${e.id})">
          <i class="bi bi-trash3"></i>
        </button>
      </td>
    </tr>
  `).join("");
}

document.getElementById("btnAddFood").addEventListener("click", async () => {
  const payload = {
    logged_at: document.getElementById("food-date").value + "T12:00:00",
    meal_type: document.getElementById("food-meal").value,
    food_name: document.getElementById("food-name").value.trim(),
    amount_g: parseFloat(document.getElementById("food-amount").value) || 100,
    calories: parseFloat(document.getElementById("food-cal").value) || 0,
    protein_g: parseFloat(document.getElementById("food-protein").value) || 0,
    carbs_g: parseFloat(document.getElementById("food-carbs").value) || 0,
    fat_g: parseFloat(document.getElementById("food-fat").value) || 0,
    fiber_g: parseFloat(document.getElementById("food-fiber").value) || 0,
  };

  if (!payload.food_name) {
    showAlert("foodAlert", "请输入食物名称", "warning");
    return;
  }

  const res = await fetch("/api/food/entries", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (res.ok) {
    showAlert("foodAlert", "✓ 饮食记录已添加");
    // Clear name and nutrition fields, keep date/meal
    ["food-name", "food-amount", "food-cal", "food-protein", "food-carbs", "food-fat", "food-fiber"]
      .forEach((id) => { document.getElementById(id).value = ""; });
    await refreshFoodData();
    await loadFoodTrend();
  } else {
    const err = await res.json();
    showAlert("foodAlert", `添加失败：${err.error || res.statusText}`, "danger");
  }
});

async function deleteFoodEntry(id) {
  const res = await fetch(`/api/food/entries/${id}`, { method: "DELETE" });
  if (res.ok) {
    await refreshFoodData();
    await loadFoodTrend();
  }
}

document.getElementById("btnRefreshFood").addEventListener("click", async () => {
  await refreshFoodData();
  await loadFoodTrend();
});

// ---------------------------------------------------------------------------
// Goals
// ---------------------------------------------------------------------------
async function loadGoals() {
  const goals = await fetch("/api/goals").then((r) => r.json());
  document.getElementById("goal-steps").value = goals.daily_steps;
  document.getElementById("goal-cal-in").value = goals.daily_calories_intake;
  document.getElementById("goal-cal-burn").value = goals.daily_calories_burn;
  document.getElementById("goal-sleep").value = goals.sleep_hours;
  document.getElementById("goal-active").value = goals.active_minutes;
}

document.getElementById("btnSaveGoals").addEventListener("click", async () => {
  const payload = {
    daily_steps: parseInt(document.getElementById("goal-steps").value),
    daily_calories_intake: parseInt(document.getElementById("goal-cal-in").value),
    daily_calories_burn: parseInt(document.getElementById("goal-cal-burn").value),
    sleep_hours: parseFloat(document.getElementById("goal-sleep").value),
    active_minutes: parseInt(document.getElementById("goal-active").value),
  };

  const res = await fetch("/api/goals", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (res.ok) {
    showAlert("goalsAlert", "✓ 目标已保存");
  } else {
    showAlert("goalsAlert", "保存失败", "danger");
  }
});

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------
loadDashboard();
