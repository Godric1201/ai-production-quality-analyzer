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

function formatPredictionProbability(value) {
  const probability = Number(value);
  if (!Number.isFinite(probability)) {
    return "N/A";
  }

  return probability <= 1 ? formatPercent(probability * 100) : formatPercent(probability);
}

function splitRecommendationText(value) {
  if (!value) {
    return [];
  }

  return String(value)
    .split(";")
    .map((item) => item.trim())
    .filter(Boolean);
}

function renderRootCauseResults(predictionResults = []) {
  const tableBody = document.getElementById("rootCauseRows");
  tableBody.innerHTML = "";

  if (!Array.isArray(predictionResults) || predictionResults.length === 0) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.className = "empty-state";
    cell.colSpan = 5;
    cell.textContent = "No root cause analysis rows are available.";
    row.appendChild(cell);
    tableBody.appendChild(row);
    return;
  }

  predictionResults.slice(0, 8).forEach((result) => {
    const row = document.createElement("tr");
    const recommendations = splitRecommendationText(result.engineering_recommendations);

    const partCell = document.createElement("td");
    partCell.textContent = result.part_id || "N/A";

    const probabilityCell = document.createElement("td");
    probabilityCell.textContent = formatPredictionProbability(result.scrap_probability);

    const riskCell = document.createElement("td");
    const riskBadge = document.createElement("span");
    riskBadge.className = "rca-risk";
    riskBadge.textContent = result.predicted_scrap_risk || "N/A";
    riskCell.appendChild(riskBadge);

    const summaryCell = document.createElement("td");
    summaryCell.textContent =
      result.root_cause_summary || "No root cause summary available.";

    const recommendationCell = document.createElement("td");
    if (recommendations.length > 0) {
      const list = document.createElement("ul");
      list.className = "rca-recommendations";
      recommendations.forEach((recommendation) => {
        const item = document.createElement("li");
        item.textContent = recommendation;
        list.appendChild(item);
      });
      recommendationCell.appendChild(list);
    } else {
      recommendationCell.textContent = "No engineering recommendations available.";
    }

    row.appendChild(partCell);
    row.appendChild(probabilityCell);
    row.appendChild(riskCell);
    row.appendChild(summaryCell);
    row.appendChild(recommendationCell);
    tableBody.appendChild(row);
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

function renderThresholdTuning(thresholdTuning) {
  setText("defaultThreshold", Number(thresholdTuning.default_threshold).toFixed(2));
  setText("selectedThreshold", Number(thresholdTuning.selected_threshold).toFixed(2));

  setText(
    "recallImprovement",
    `+${Number(thresholdTuning.recall_improvement_percentage_points).toFixed(2)} pp`
  );

  setText(
    "thresholdRecall",
    `${(Number(thresholdTuning.default_recall) * 100).toFixed(2)}% → ${(Number(
      thresholdTuning.selected_recall
    ) * 100).toFixed(2)}%`
  );

  setText("missedScrapReduction", thresholdTuning.missed_scrap_reduction);
  setText("additionalFalseAlarms", `+${thresholdTuning.additional_false_alarms}`);

  setText(
    "thresholdNote",
    `Lowering the decision threshold reduced missed scrap from ${thresholdTuning.default_false_negative} to ${thresholdTuning.selected_false_negative}, at the cost of increasing false alarms from ${thresholdTuning.default_false_positive} to ${thresholdTuning.selected_false_positive}.`
  );
}

function formatCurrency(value, currency) {
  return `${new Intl.NumberFormat("en-US").format(Number(value).toFixed(0))} ${currency}`;
}

function renderCostOptimization(costOptimization) {
  setText(
    "costOptimizedThreshold",
    `Threshold ${Number(costOptimization.cost_optimized_threshold).toFixed(2)}`
  );

  setText(
    "optimizedTotalCost",
    formatCurrency(costOptimization.optimized_total_cost, costOptimization.currency)
  );

  setText(
    "defaultTotalCost",
    formatCurrency(costOptimization.default_total_cost, costOptimization.currency)
  );

  setText(
    "costSavings",
    formatCurrency(costOptimization.cost_savings_vs_default, costOptimization.currency)
  );

  setText(
    "costAssumptions",
    `${Number(costOptimization.missed_scrap_cost).toFixed(0)} / ${Number(
      costOptimization.false_alarm_cost
    ).toFixed(0)} ${costOptimization.currency}`
  );

  setText(
    "costOptimizationNote",
    `The cost-optimized threshold reduces estimated cost from ${formatCurrency(
      costOptimization.default_total_cost,
      costOptimization.currency
    )} to ${formatCurrency(
      costOptimization.optimized_total_cost,
      costOptimization.currency
    )}, under the assumption that missed scrap is more costly than additional inspection.`
  );
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
    renderRootCauseResults(data.prediction_results);
    renderThresholdTuning(data.model.threshold_tuning);
    renderCostOptimization(data.model.cost_optimization);
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
