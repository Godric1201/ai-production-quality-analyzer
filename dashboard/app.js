const chartTextColor = "#cbd5e1";
const chartGridColor = "rgba(148, 163, 184, 0.16)";

const chartColors = {
  blue: "rgba(56, 189, 248, 0.82)",
  rose: "rgba(251, 113, 133, 0.82)",
  amber: "rgba(251, 191, 36, 0.82)",
  green: "rgba(52, 211, 153, 0.82)",
  violet: "rgba(167, 139, 250, 0.82)",
};

let selectedRootCauseRow = null;
let selectedRootCausePartId = null;
let rootCauseResults = [];

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

function truncateText(value, maxLength = 96) {
  const text = String(value || "").trim();
  if (text.length <= maxLength) {
    return text;
  }

  return `${text.slice(0, maxLength - 1).trim()}…`;
}

function formatTitleCase(value) {
  return String(value)
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function extractRootCauseDrivers(summary) {
  if (!summary) {
    return [];
  }

  const text = String(summary).trim();
  const marker = "mainly due to ";
  const markerIndex = text.toLowerCase().indexOf(marker);
  if (markerIndex === -1) {
    return text ? [text] : [];
  }

  return text
    .slice(markerIndex + marker.length)
    .replace(/\.$/, "")
    .replace(", and ", ", ")
    .replace(" and ", ", ")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function getDominantRootCause(predictionResults) {
  const counts = new Map();

  predictionResults.forEach((result) => {
    extractRootCauseDrivers(result.root_cause_summary).forEach((driver) => {
      counts.set(driver, (counts.get(driver) || 0) + 1);
    });
  });

  if (counts.size === 0) {
    return "N/A";
  }

  const [driver] = [...counts.entries()].sort((a, b) => b[1] - a[1])[0];
  return formatTitleCase(driver);
}

function renderRootCauseSummaryCards(predictionResults = []) {
  const rows = Array.isArray(predictionResults) ? predictionResults : [];
  const highRiskCount = rows.filter(
    (result) => String(result.predicted_scrap_risk || "").toLowerCase() === "high"
  ).length;
  const probabilities = rows
    .map((result) => Number(result.scrap_probability))
    .filter(Number.isFinite);
  const averageRisk =
    probabilities.length > 0
      ? probabilities.reduce((sum, value) => sum + value, 0) / probabilities.length
      : null;

  setText("totalPredictions", formatNumber(rows.length));
  setText("highRiskBatches", formatNumber(highRiskCount));
  setText("dominantRootCause", getDominantRootCause(rows));
  setText(
    "averagePredictedRisk",
    averageRisk === null ? "N/A" : formatPredictionProbability(averageRisk)
  );
}

function getConfidenceLevel(result) {
  const probability = Number(result.scrap_probability);
  if (!Number.isFinite(probability)) {
    return "Unknown";
  }
  if (probability >= 0.7) {
    return "High";
  }
  if (probability >= 0.5) {
    return "Medium";
  }
  return "Watch";
}

function getRcaControls() {
  return {
    highRiskOnly: document.getElementById("highRiskOnlyToggle").checked,
    sortMode: document.getElementById("rcaSortControl").value,
  };
}

function getFilteredRootCauseResults() {
  const { highRiskOnly, sortMode } = getRcaControls();
  const filteredRows = rootCauseResults.filter((result) => {
    if (!highRiskOnly) {
      return true;
    }

    return String(result.predicted_scrap_risk || "").toLowerCase() === "high";
  });

  return [...filteredRows].sort((a, b) => {
    if (sortMode === "risk-asc") {
      return Number(a.scrap_probability || 0) - Number(b.scrap_probability || 0);
    }
    if (sortMode === "batch-id") {
      return String(a.part_id || "").localeCompare(String(b.part_id || ""));
    }

    return Number(b.scrap_probability || 0) - Number(a.scrap_probability || 0);
  });
}

function refreshRootCauseResults() {
  const rows = getFilteredRootCauseResults().slice(0, 8);
  if (
    selectedRootCausePartId &&
    !rows.some((result) => result.part_id === selectedRootCausePartId)
  ) {
    closeRootCausePanel();
  }

  renderRootCauseTable(rows);
}

function buildSensorEvidence(result) {
  const evidence = [];
  const temperature = Number(result.temperature_c);
  const pressure = Number(result.pressure_bar);
  const cycleTime = Number(result.cycle_time_s);
  const vibration = Number(result.vibration_mm_s);
  const humidity = Number(result.humidity_percent);
  const operatorExperience = Number(result.operator_experience_years);

  if (Number.isFinite(temperature) && temperature > 190) {
    evidence.push(`Temperature ${temperature.toFixed(1)} C exceeds the 190 C monitoring band.`);
  }
  if (Number.isFinite(pressure) && pressure >= 6.4) {
    evidence.push(`Pressure ${pressure.toFixed(2)} bar is above the expected range.`);
  } else if (Number.isFinite(pressure) && pressure <= 5.1) {
    evidence.push(`Pressure ${pressure.toFixed(2)} bar is below the expected range.`);
  }
  if (Number.isFinite(cycleTime) && cycleTime > 50) {
    evidence.push(`Cycle time ${cycleTime.toFixed(1)} s is above the 50 s warning threshold.`);
  }
  if (Number.isFinite(vibration) && vibration > 2.7) {
    evidence.push(`Vibration ${vibration.toFixed(2)} mm/s is above the normal monitoring band.`);
  }
  if (Number.isFinite(humidity) && humidity > 60) {
    evidence.push(`Humidity ${humidity.toFixed(1)}% is above the configured monitoring band.`);
  }
  if (Number.isFinite(operatorExperience) && operatorExperience < 2) {
    evidence.push(`Operator experience ${operatorExperience.toFixed(1)} years is below the guidance threshold.`);
  }
  if (result.machine_id === "M2") {
    evidence.push("Machine M2 is configured as a higher-risk asset.");
  }
  if (result.material_batch === "B4") {
    evidence.push("Material batch B4 is configured as a higher-risk material batch.");
  }
  if (result.shift === "night" || result.shift === "late") {
    evidence.push(`Production occurred on the ${result.shift} shift.`);
  }

  return evidence.length > 0
    ? evidence
    : ["No configured sensor anomaly indicators are available for this row."];
}

function renderPanelList(listId, items) {
  const list = document.getElementById(listId);
  list.innerHTML = "";

  items.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    list.appendChild(li);
  });
}

function openRootCausePanel(result, rowElement) {
  const panel = document.getElementById("rcaDetailPanel");
  const backdrop = document.getElementById("rcaPanelBackdrop");
  const recommendations = splitRecommendationText(result.engineering_recommendations);

  if (selectedRootCauseRow) {
    selectedRootCauseRow.classList.remove("is-selected");
  }
  selectedRootCauseRow = rowElement;
  selectedRootCausePartId = result.part_id || null;
  selectedRootCauseRow.classList.add("is-selected");

  setText("panelBatchId", result.part_id || "Batch ID unavailable");
  setText(
    "panelFailureRisk",
    `${formatPredictionProbability(result.scrap_probability)} (${result.predicted_scrap_risk || "N/A"})`
  );
  setText("panelConfidenceLevel", `Confidence: ${getConfidenceLevel(result)}`);
  setText(
    "panelRootCauseSummary",
    result.root_cause_summary || "No root cause summary available."
  );
  renderPanelList("panelSensorEvidence", buildSensorEvidence(result));
  renderPanelList(
    "panelEngineeringRecommendations",
    recommendations.length > 0
      ? recommendations
      : ["No engineering recommendations available."]
  );

  panel.classList.add("is-open");
  backdrop.classList.add("is-open");
  panel.setAttribute("aria-hidden", "false");
}

function closeRootCausePanel() {
  const panel = document.getElementById("rcaDetailPanel");
  const backdrop = document.getElementById("rcaPanelBackdrop");

  panel.classList.remove("is-open");
  backdrop.classList.remove("is-open");
  panel.setAttribute("aria-hidden", "true");

  if (selectedRootCauseRow) {
    selectedRootCauseRow.classList.remove("is-selected");
    selectedRootCauseRow = null;
  }
  selectedRootCausePartId = null;
}

function setupRootCausePanel() {
  document.getElementById("closeRcaPanel").addEventListener("click", closeRootCausePanel);
  document.getElementById("rcaPanelBackdrop").addEventListener("click", closeRootCausePanel);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeRootCausePanel();
    }
  });
}

function setupRootCauseControls() {
  document
    .getElementById("highRiskOnlyToggle")
    .addEventListener("change", refreshRootCauseResults);
  document
    .getElementById("rcaSortControl")
    .addEventListener("change", refreshRootCauseResults);
}

function renderRootCauseTable(predictionResults = []) {
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

  predictionResults.forEach((result) => {
    const row = document.createElement("tr");
    const recommendations = splitRecommendationText(result.engineering_recommendations);
    row.tabIndex = 0;
    row.setAttribute("role", "button");
    row.setAttribute("aria-label", `Open root cause details for ${result.part_id || "batch"}`);
    if (selectedRootCausePartId && result.part_id === selectedRootCausePartId) {
      selectedRootCauseRow = row;
      row.classList.add("is-selected");
    }

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
    summaryCell.className = "rca-summary-cell";
    summaryCell.textContent = truncateText(
      result.root_cause_summary || "No root cause summary available.",
      118
    );

    const recommendationCell = document.createElement("td");
    recommendationCell.className = "rca-action-cell";
    if (recommendations.length > 0) {
      const preview = document.createElement("span");
      preview.className = "action-preview";
      preview.textContent = truncateText(recommendations[0], 86);
      recommendationCell.appendChild(preview);
    } else {
      const preview = document.createElement("span");
      preview.className = "action-preview muted";
      preview.textContent = "No action preview available.";
      recommendationCell.appendChild(preview);
    }
    const detailHint = document.createElement("span");
    detailHint.className = "details-hint";
    detailHint.textContent = "Open details";
    recommendationCell.appendChild(detailHint);

    row.appendChild(partCell);
    row.appendChild(probabilityCell);
    row.appendChild(riskCell);
    row.appendChild(summaryCell);
    row.appendChild(recommendationCell);
    row.addEventListener("click", () => openRootCausePanel(result, row));
    row.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openRootCausePanel(result, row);
      }
    });
    tableBody.appendChild(row);
  });
}

function renderRootCauseResults(predictionResults = []) {
  rootCauseResults = Array.isArray(predictionResults) ? predictionResults : [];
  refreshRootCauseResults();
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
    renderRootCauseSummaryCards(data.prediction_results);
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

setupRootCausePanel();
setupRootCauseControls();
loadDashboard();
