const chartTextColor = "#cbd5e1";
const chartGridColor = "rgba(148, 163, 184, 0.16)";

const chartColors = {
  blue: "rgba(56, 189, 248, 0.82)",
  rose: "rgba(251, 113, 133, 0.82)",
  amber: "rgba(251, 191, 36, 0.82)",
  green: "rgba(52, 211, 153, 0.82)",
  violet: "rgba(167, 139, 250, 0.82)",
};

Chart.defaults.color = chartTextColor;
Chart.defaults.borderColor = chartGridColor;
Chart.defaults.font.family =
  'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';

function formatNumber(value) {
  return new Intl.NumberFormat("en-US").format(value);
}

function formatPercent(value) {
  return `${Number(value).toFixed(2)}%`;
}

function setText(id, value) {
  document.getElementById(id).textContent = value;
}

function createBarChart(canvasId, labels, values, label, color) {
  const ctx = document.getElementById(canvasId);

  return new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label,
          data: values,
          backgroundColor: color,
          borderRadius: 10,
          borderSkipped: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false,
        },
        tooltip: {
          callbacks: {
            label: (context) => `${context.dataset.label}: ${context.raw}%`,
          },
        },
      },
      scales: {
        x: {
          grid: {
            display: false,
          },
        },
        y: {
          beginAtZero: true,
          ticks: {
            callback: (value) => `${value}%`,
          },
        },
      },
    },
  });
}

function createHorizontalBarChart(canvasId, labels, values, label) {
  const ctx = document.getElementById(canvasId);

  return new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label,
          data: values,
          backgroundColor: chartColors.violet,
          borderRadius: 10,
          borderSkipped: false,
        },
      ],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false,
        },
      },
      scales: {
        x: {
          beginAtZero: true,
        },
        y: {
          grid: {
            display: false,
          },
        },
      },
    },
  });
}

function renderKpis(kpis) {
  setText("totalParts", formatNumber(kpis.total_parts));
  setText("overallScrapRate", formatPercent(kpis.overall_scrap_rate));
  setText("highestRiskMachine", kpis.highest_risk_machine);
  setText("modelF1Score", Number(kpis.model_f1_score).toFixed(3));

  setText("accuracy", Number(kpis.model_accuracy).toFixed(3));
  setText("precision", Number(kpis.model_precision).toFixed(3));
  setText("recall", Number(kpis.model_recall).toFixed(3));
  setText("f1", Number(kpis.model_f1_score).toFixed(3));
}

function renderRecommendations(recommendations) {
  const list = document.getElementById("recommendationList");
  list.innerHTML = "";

  recommendations.forEach((recommendation) => {
    const li = document.createElement("li");
    li.textContent = recommendation;
    list.appendChild(li);
  });
}

function formatConditionLabel(key) {
  return key
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function renderSamplePrediction(samplePrediction) {
  setText(
    "sampleScrapProbability",
    `${Number(samplePrediction.scrap_probability).toFixed(2)}%`
  );

  setText("sampleRiskLevel", `${samplePrediction.risk_level} Risk`);

  const conditionGrid = document.getElementById("sampleInputConditions");
  conditionGrid.innerHTML = "";

  Object.entries(samplePrediction.input_conditions).forEach(([key, value]) => {
    const item = document.createElement("div");
    item.className = "condition-item";

    const label = document.createElement("span");
    label.textContent = formatConditionLabel(key);

    const strong = document.createElement("strong");
    strong.textContent = value;

    item.appendChild(label);
    item.appendChild(strong);
    conditionGrid.appendChild(item);
  });

  const recommendationList = document.getElementById("samplePredictionRecommendations");
  recommendationList.innerHTML = "";

  samplePrediction.recommendations.forEach((recommendation) => {
    const li = document.createElement("li");
    li.textContent = recommendation;
    recommendationList.appendChild(li);
  });
}

function renderCharts(charts) {
  createBarChart(
    "scrapByMachineChart",
    charts.scrap_rate_by_machine.map((item) => item.label),
    charts.scrap_rate_by_machine.map((item) => item.scrap_rate),
    "Scrap Rate",
    chartColors.rose
  );

  createBarChart(
    "scrapByShiftChart",
    charts.scrap_rate_by_shift.map((item) => item.label),
    charts.scrap_rate_by_shift.map((item) => item.scrap_rate),
    "Scrap Rate",
    chartColors.amber
  );

  createBarChart(
    "temperatureRiskChart",
    charts.scrap_rate_by_temperature_range.map((item) => item.label),
    charts.scrap_rate_by_temperature_range.map((item) => item.scrap_rate),
    "Scrap Rate",
    chartColors.blue
  );

  createHorizontalBarChart(
    "featureImportanceChart",
    charts.top_feature_importances.map((item) => item.feature),
    charts.top_feature_importances.map((item) => item.importance),
    "Importance"
  );
}

async function loadDashboard() {
  try {
    const response = await fetch("dashboard_data.json");

    if (!response.ok) {
      throw new Error(`Failed to load dashboard_data.json: ${response.status}`);
    }

    const data = await response.json();

        renderKpis(data.kpis);
    renderCharts(data.charts);
    renderRecommendations(data.recommendations);
    renderSamplePrediction(data.sample_prediction);
  } catch (error) {
    console.error(error);
    document.body.innerHTML = `
      <div class="page-shell">
        <div class="insight-card">
          <h1>Dashboard data could not be loaded</h1>
          <p>Please make sure dashboard_data.json exists and open this dashboard through a local server.</p>
          <p>Error: ${error.message}</p>
        </div>
      </div>
    `;
  }
}

loadDashboard();