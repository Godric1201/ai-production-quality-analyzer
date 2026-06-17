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
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return "Not generated yet";
  }

  return `${numericValue.toFixed(2)}%`;
}

function setText(id, value) {
  document.getElementById(id).textContent = value;
}

function formatCount(value) {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return "Not generated yet";
  }

  return formatNumber(numericValue);
}

function safeGet(obj, path, fallback = "Not generated yet") {
  return path.reduce((current, key) => {
    if (current && Object.prototype.hasOwnProperty.call(current, key)) {
      return current[key];
    }

  return undefined;
  }, obj) ?? fallback;
}

function formatValue(value, fallback = "Not generated yet") {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }

  return String(value);
}

function formatEnumLabel(value, fallback = "Not generated yet") {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }

  const labels = {
    ENGINEERING_REVIEW_REQUIRED: "Review Required",
    ADDITIONAL_MONITORING: "Additional Monitoring",
    STANDARD_MONITORING: "Standard Monitoring",
    TRUE_POSITIVE_REVIEW: "Confirmed Issue",
    FALSE_ALARM_REVIEW: "False Alarm",
    MISSED_ISSUE: "Missed Issue",
    TRUE_NEGATIVE_MONITORING: "Correct Monitoring",
    CRITICAL_VIOLATION: "Critical Violation",
    WARNING_VIOLATION: "Warning Violation",
    COMPLIANT: "Compliant",
    confirmed_issue: "Confirmed Issue",
    false_alarm: "False Alarm",
    no_issue: "No Issue",
    missed_issue: "Missed Issue",
    needs_follow_up: "Needs Follow-up",
  };
  const text = String(value);

  return (
    labels[text] ||
    text
      .replace(/[_-]+/g, " ")
      .toLowerCase()
      .replace(/\b\w/g, (char) => char.toUpperCase())
  );
}

function splitListText(value) {
  if (!value) {
    return [];
  }

  if (Array.isArray(value)) {
    return value.map((item) => String(item).trim()).filter(Boolean);
  }

  return String(value)
    .split(/[;,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function formatLimitedList(value, limit = 3, moreLabel = "more") {
  const items = splitListText(value);
  if (items.length === 0) {
    return "None";
  }

  const visibleItems = items.slice(0, limit);
  const remainingCount = items.length - visibleItems.length;

  if (remainingCount > 0) {
    visibleItems.push(`+${remainingCount} ${moreLabel}`);
  }

  return visibleItems.join("\n");
}

function formatRequirementLabel(value) {
  const mapping = {
    TEMP_MAX_WARNING: "Temperature warning",
    TEMP_MAX_CRITICAL: "Temperature critical",
    VIBRATION_MAX_WARNING: "Vibration warning",
    VIBRATION_MAX_CRITICAL: "Vibration critical",
    CYCLE_TIME_MAX_WARNING: "Cycle-time warning",
    CYCLE_TIME_MAX_CRITICAL: "Cycle-time critical",
    PRESSURE_MIN_WARNING: "Low pressure warning",
    PRESSURE_MAX_WARNING: "High pressure warning",
    HUMIDITY_MAX_WARNING: "Humidity warning",
    LOW_OPERATOR_EXPERIENCE_WARNING: "Operator support warning",
  };

  if (!value) {
    return "Not available";
  }

  return mapping[value] || formatEnumLabel(value);
}

function formatRequirementList(value, limit = 4) {
  const items = splitListText(value);
  if (items.length === 0) {
    return [];
  }

  const visibleItems = items.slice(0, limit).map(formatRequirementLabel);
  const remainingCount = items.length - visibleItems.length;
  return remainingCount > 0 ? [...visibleItems, `+${remainingCount} more`] : visibleItems;
}

function formatRequirementChips(value, limit = 4) {
  return formatRequirementList(value, limit);
}

function formatDriverChipText(value) {
  const text = formatValue(value, "").trim();
  if (!text) {
    return "";
  }

  return truncateTraceText(text.replace(/\s+/g, " "), 28);
}

function formatDriverChips(value, limit = 3) {
  return splitListText(value)
    .slice(0, limit)
    .map(formatDriverChipText)
    .filter(Boolean);
}

function formatActionList(value, limit = 2) {
  const items = splitListText(value);
  if (items.length === 0) {
    return "None";
  }

  const visibleItems = items.slice(0, limit).map((item) => `- ${truncateTraceText(item, 86)}`);
  const remainingCount = items.length - visibleItems.length;

  if (remainingCount > 0) {
    visibleItems.push(`+${remainingCount} more actions`);
  }

  return visibleItems.join("\n");
}

function formatTraceActions(value, limit = 2) {
  return formatActionList(value, limit);
}

function joinDisplayList(items) {
  if (items.length <= 2) {
    return items.join(" and ");
  }

  return `${items.slice(0, -1).join(", ")}, and ${items[items.length - 1]}`;
}

function summarizeRequirementLabels(labels) {
  const readableLabels = splitListText(labels)
    .filter((label) => !label.startsWith("+"))
    .map((label) =>
      label
        .replace(/\s+(warning|critical)$/i, "")
        .replace(/^low pressure$/i, "pressure")
        .replace(/^high pressure$/i, "pressure")
        .replace(/-/g, " ")
        .toLowerCase()
    )
    .filter(Boolean);
  const uniqueChecks = [...new Set(readableLabels)];

  if (uniqueChecks.length === 0) {
    return "None";
  }

  const summaryText = joinDisplayList(uniqueChecks);
  return `${summaryText.charAt(0).toUpperCase()}${summaryText.slice(
    1
  )} checks fell outside configured process limits.`;
}

function formatViolationSummary(value, requirementIds = "") {
  const requirementLabels = formatRequirementList(requirementIds, 99);
  const labelSummary = summarizeRequirementLabels(requirementLabels);
  if (labelSummary !== "None") {
    return labelSummary;
  }

  const text = formatValue(value, "").trim();
  if (!text) {
    return "None";
  }
  return truncateTraceText(text, 150);
}

function truncateTraceText(value, maxLength) {
  const text = formatValue(value, "").trim();
  if (text.length <= maxLength) {
    return text;
  }

  return `${text.slice(0, Math.max(0, maxLength - 3)).trim()}...`;
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

function renderWorkflowMetrics(containerId, metrics) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";

  metrics.forEach((metric) => {
    const item = document.createElement("div");
    const label = document.createElement("span");
    const value = document.createElement("strong");

    label.textContent = metric.label;
    value.textContent = metric.value;
    item.appendChild(label);
    item.appendChild(value);
    container.appendChild(item);
  });
}

function renderMissingWorkflowCard(metricsId, interpretationId) {
  renderWorkflowMetrics(metricsId, [
    {
      label: "Status",
      value: "Not generated yet",
    },
  ]);
  setText(interpretationId, "Output not generated yet.");
}

function renderWorkflowOverview(workflowOverview = {}) {
  const dataQuality = safeGet(workflowOverview, ["data_quality"], {});
  if (dataQuality.status === "missing") {
    renderMissingWorkflowCard("dataQualityMetrics", "dataQualityInterpretation");
  } else {
    renderWorkflowMetrics("dataQualityMetrics", [
      { label: "Status", value: safeGet(dataQuality, ["status"]) },
      { label: "Rows", value: formatCount(safeGet(dataQuality, ["row_count"], null)) },
      { label: "Warnings", value: formatCount(safeGet(dataQuality, ["warning_count"], null)) },
    ]);
    setText("dataQualityInterpretation", "Input data is checked before model training.");
  }

  const batchReview = safeGet(workflowOverview, ["batch_review"], {});
  if (batchReview.status === "missing") {
    renderMissingWorkflowCard("batchReviewMetrics", "batchReviewInterpretation");
  } else {
    renderWorkflowMetrics("batchReviewMetrics", [
      { label: "Rows reviewed", value: formatCount(safeGet(batchReview, ["row_count"], null)) },
      {
        label: "Engineering review",
        value: formatCount(
          safeGet(batchReview, ["decision_counts", "ENGINEERING_REVIEW_REQUIRED"], null)
        ),
      },
      {
        label: "Threshold",
        value:
          safeGet(batchReview, ["review_threshold"], null) === null
            ? "Not generated yet"
            : Number(batchReview.review_threshold).toFixed(2),
      },
    ]);
    setText(
      "batchReviewInterpretation",
      "New records are scored and routed for engineering review or monitoring."
    );
  }

  const specCompliance = safeGet(workflowOverview, ["spec_compliance"], {});
  if (specCompliance.status === "missing") {
    renderMissingWorkflowCard("specComplianceMetrics", "specComplianceInterpretation");
  } else {
    renderWorkflowMetrics("specComplianceMetrics", [
      {
        label: "Critical",
        value: formatCount(
          safeGet(specCompliance, ["status_counts", "CRITICAL_VIOLATION"], null)
        ),
      },
      {
        label: "Warning",
        value: formatCount(
          safeGet(specCompliance, ["status_counts", "WARNING_VIOLATION"], null)
        ),
      },
      {
        label: "Compliant",
        value: formatCount(safeGet(specCompliance, ["status_counts", "COMPLIANT"], null)),
      },
    ]);
    setText(
      "specComplianceInterpretation",
      "Configured process requirements are checked against new records."
    );
  }

  const feedbackLoop = safeGet(workflowOverview, ["feedback_loop"], {});
  if (feedbackLoop.status === "missing") {
    renderMissingWorkflowCard("feedbackLoopMetrics", "feedbackLoopInterpretation");
  } else {
    renderWorkflowMetrics("feedbackLoopMetrics", [
      {
        label: "Issue capture",
        value: formatPercent(Number(safeGet(feedbackLoop, ["issue_capture_rate"], 0)) * 100),
      },
      {
        label: "False alarm rate",
        value: formatPercent(
          Number(safeGet(feedbackLoop, ["false_alarm_rate_among_reviews"], 0)) * 100
        ),
      },
      {
        label: "Missed issues",
        value: formatCount(safeGet(feedbackLoop, ["missed_issue_count"], null)),
      },
    ]);
    setText(
      "feedbackLoopInterpretation",
      "Later feedback is used to evaluate review decisions and threshold trade-offs."
    );
  }
}

function formatSeverityLabel(value) {
  const label = formatValue(value, "Informational");
  return formatEnumLabel(label);
}

function severityClass(value) {
  const normalized = String(value || "").toLowerCase();
  if (normalized === "critical") {
    return "severity-critical";
  }
  if (normalized === "warning") {
    return "severity-warning";
  }
  if (normalized === "monitoring") {
    return "severity-monitoring";
  }
  return "severity-info";
}

function createSeverityBadge(value) {
  const badge = document.createElement("span");
  badge.className = `severity-badge ${severityClass(value)}`;
  badge.textContent = formatSeverityLabel(value);
  return badge;
}

function labelCell(cell, label) {
  if (label) {
    cell.dataset.label = label;
  }
}

function appendTextCell(row, value, label) {
  const cell = document.createElement("td");
  labelCell(cell, label);
  cell.textContent = formatValue(value, "Not specified");
  row.appendChild(cell);
}

function appendSeverityCell(row, value, label) {
  const cell = document.createElement("td");
  labelCell(cell, label);
  cell.appendChild(createSeverityBadge(value));
  row.appendChild(cell);
}

function renderRulebookTable(containerId, rows, columns) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";

  if (!rows || rows.length === 0) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = columns.length;
    cell.textContent = "Rulebook data not generated yet.";
    row.appendChild(cell);
    container.appendChild(row);
    return;
  }

  rows.forEach((item) => {
    const row = document.createElement("tr");
    columns.forEach((column) => {
      if (column.type === "severity") {
        appendSeverityCell(row, item[column.key], column.label);
      } else {
        appendTextCell(row, item[column.key], column.label);
      }
    });
    container.appendChild(row);
  });
}

function renderEngineeringRulebook(rulebook = {}) {
  const summary = safeGet(rulebook, ["summary"], {});
  const sourceFiles = safeGet(summary, ["source_files"], []);

  setText("rulebookSpecCount", formatCount(safeGet(summary, ["spec_requirement_count"], null)));
  setText("rulebookRcaCount", formatCount(safeGet(summary, ["rca_rule_count"], null)));
  setText("rulebookSourceType", formatValue(safeGet(summary, ["source_type"], "YAML configuration")));
  setText(
    "rulebookSourceFiles",
    Array.isArray(sourceFiles) && sourceFiles.length > 0
      ? sourceFiles.join(", ")
      : "config/spec_requirements.yaml, config/rca_rules.yaml"
  );

  renderRulebookTable("specRulebookTable", safeGet(rulebook, ["spec_requirements"], []), [
    { key: "label", label: "Check" },
    { key: "signal_label", label: "Signal" },
    { key: "condition", label: "Condition" },
    { key: "severity", label: "Severity", type: "severity" },
    { key: "recommended_action", label: "Recommended action" },
  ]);

  renderRulebookTable("rcaRulebookTable", safeGet(rulebook, ["rca_rules"], []), [
    { key: "label", label: "Rule" },
    { key: "condition", label: "Trigger / condition" },
    { key: "severity", label: "Severity", type: "severity" },
    { key: "possible_cause", label: "Possible cause" },
    { key: "recommended_action", label: "Recommended action" },
  ]);
}

function formatMetric(value, digits = 3) {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return "Not generated yet";
  }

  return numericValue.toFixed(digits);
}

function formatFractionPercent(value) {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return "Not generated yet";
  }

  return formatPercent(numericValue * 100);
}

function formatModelRole(value) {
  if (value === "early_warning_decision_support") {
    return "Early-warning decision support";
  }

  return formatEnumLabel(value);
}

function appendEvaluationCell(row, value, label) {
  const cell = document.createElement("td");
  labelCell(cell, label);
  cell.textContent = value;
  row.appendChild(cell);
}

function renderEvaluationTable(containerId, rows, columns, emptyText) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";

  if (!Array.isArray(rows) || rows.length === 0) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = columns.length;
    cell.textContent = emptyText;
    row.appendChild(cell);
    container.appendChild(row);
    return;
  }

  rows.forEach((item) => {
    const row = document.createElement("tr");
    columns.forEach((column) => {
      appendEvaluationCell(row, column.format(item[column.key], item), column.label);
    });
    container.appendChild(row);
  });
}

function renderModelEvaluation(modelEvaluation = {}) {
  const summary = safeGet(modelEvaluation, ["summary"], {});

  setText("modelEvalRocAuc", formatMetric(safeGet(summary, ["roc_auc"], null)));
  setText("modelEvalPrAuc", formatMetric(safeGet(summary, ["pr_auc"], null)));
  setText(
    "modelEvalBaselineRate",
    formatFractionPercent(safeGet(summary, ["baseline_scrap_rate"], null))
  );
  setText("modelEvalRole", formatModelRole(safeGet(summary, ["model_role"], null)));

  renderEvaluationTable(
    "riskBandTable",
    safeGet(modelEvaluation, ["risk_bands"], []),
    [
      { key: "risk_band", label: "Risk band", format: (value) => formatValue(value) },
      { key: "row_count", label: "Rows", format: (value) => formatCount(value) },
      {
        key: "actual_scrap_rate",
        label: "Actual scrap rate",
        format: (value) => formatFractionPercent(value),
      },
      {
        key: "average_predicted_risk",
        label: "Average predicted risk",
        format: (value) => formatFractionPercent(value),
      },
      { key: "review_priority", label: "Review priority", format: (value) => formatValue(value) },
    ],
    "Risk band evaluation not generated yet."
  );

  renderEvaluationTable(
    "thresholdTradeoffTable",
    safeGet(modelEvaluation, ["threshold_tradeoff"], []),
    [
      { key: "threshold", label: "Threshold", format: (value) => formatMetric(value, 2) },
      { key: "recall", label: "Recall", format: (value) => formatFractionPercent(value) },
      { key: "false_positive", label: "False positives", format: (value) => formatCount(value) },
      { key: "false_negative", label: "False negatives", format: (value) => formatCount(value) },
      { key: "total_cost", label: "Total cost", format: (value) => formatNumber(Number(value)) },
    ],
    "Threshold trade-off data not generated yet."
  );
}

function renderTraceList(containerId, items) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";

  items.forEach((item) => {
    const row = document.createElement("div");
    const label = document.createElement("span");
    const value = document.createElement("strong");

    label.textContent = item.label;
    if (item.chips && item.chips.length > 0) {
      value.className = "trace-chip-list";
      item.chips.forEach((chipLabel) => {
        const chip = document.createElement("span");
        chip.className = "trace-chip";
        chip.textContent = chipLabel;
        value.appendChild(chip);
      });
    } else {
      value.textContent = item.value;
    }
    row.appendChild(label);
    row.appendChild(value);
    container.appendChild(row);
  });
}

function renderMissingCaseTrace() {
  setText("tracePartId", "Case trace not generated yet.");
  setText("traceRisk", "Not generated yet");
  setText("traceReviewDecision", "Not generated yet");
  setText("traceSpecStatus", "Not generated yet");
  setText("traceFeedbackClassification", "Not generated yet");

  ["traceInputConditions", "traceModelRca", "traceSpecCompliance", "traceFeedbackOutcome"].forEach(
    (containerId) => {
      renderTraceList(containerId, [
        {
          label: "Status",
          value: "Not generated yet",
        },
      ]);
    }
  );
  setText("traceSummary", "Case trace not generated yet.");
}

function renderCaseTrace(caseTrace = {}) {
  if (!caseTrace || caseTrace.status === "missing") {
    renderMissingCaseTrace();
    return;
  }

  const input = safeGet(caseTrace, ["input_conditions"], {});
  const modelReview = safeGet(caseTrace, ["model_review"], {});
  const rca = safeGet(caseTrace, ["rca"], {});
  const spec = safeGet(caseTrace, ["spec_compliance"], {});
  const feedback = safeGet(caseTrace, ["feedback"], {});
  const probability = safeGet(modelReview, ["scrap_probability"], null);
  const probabilityText = formatPredictionProbability(probability);

  setText("tracePartId", formatValue(caseTrace.part_id));
  setText(
    "traceRisk",
    `${formatValue(safeGet(modelReview, ["risk_level"], "Unknown"))} · ${probabilityText}`
  );
  setText(
    "traceRisk",
    `${formatEnumLabel(safeGet(modelReview, ["risk_level"], "Unknown"))} \u00b7 ${probabilityText}`
  );
  setText("traceReviewDecision", formatEnumLabel(safeGet(modelReview, ["review_decision"])));
  setText("traceSpecStatus", formatEnumLabel(safeGet(spec, ["spec_compliance_status"])));
  setText(
    "traceFeedbackClassification",
    formatEnumLabel(safeGet(feedback, ["feedback_classification"]))
  );

  renderTraceList("traceInputConditions", [
    { label: "Machine", value: formatValue(safeGet(input, ["machine_id"])) },
    { label: "Shift", value: formatValue(safeGet(input, ["shift"])) },
    { label: "Material batch", value: formatValue(safeGet(input, ["material_batch"])) },
    {
      label: "Temperature",
      value: `${formatValue(safeGet(input, ["temperature_c"]))} C`,
    },
    {
      label: "Vibration",
      value: `${formatValue(safeGet(input, ["vibration_mm_s"]))} mm/s`,
    },
    {
      label: "Cycle time",
      value: `${formatValue(safeGet(input, ["cycle_time_s"]))} s`,
    },
  ]);

  renderTraceList("traceModelRca", [
    { label: "Scrap probability", value: probabilityText },
    { label: "Risk level", value: formatEnumLabel(safeGet(modelReview, ["risk_level"])) },
    {
      label: "Root cause summary",
      value: formatValue(safeGet(rca, ["root_cause_summary"])),
    },
    {
      label: "Top drivers",
      chips: formatDriverChips(safeGet(rca, ["top_suspected_drivers"], ""), 3),
      value: "Not generated yet",
    },
  ]);

  renderTraceList("traceSpecCompliance", [
    {
      label: "Status",
      value: formatEnumLabel(safeGet(spec, ["spec_compliance_status"])),
    },
    {
      label: "Violated requirements",
      chips: formatRequirementList(safeGet(spec, ["violated_requirement_ids"], ""), 4),
      value: "None",
    },
    {
      label: "Violation summary",
      value: formatViolationSummary(
        safeGet(spec, ["violation_summary"], "None"),
        safeGet(spec, ["violated_requirement_ids"], "")
      ),
    },
    {
      label: "Recommended actions",
      value: formatActionList(safeGet(spec, ["recommended_actions"], ""), 2),
    },
  ]);

  renderTraceList("traceFeedbackOutcome", [
    {
      label: "Actual scrap",
      value: Number(safeGet(feedback, ["actual_scrap"], 0)) === 1 ? "Yes" : "No",
    },
    {
      label: "Engineer outcome",
      value: formatEnumLabel(safeGet(feedback, ["engineer_review_outcome"])),
    },
    {
      label: "Classification",
      value: formatEnumLabel(safeGet(feedback, ["feedback_classification"])),
    },
    {
      label: "Interpretation",
      value: formatValue(safeGet(feedback, ["feedback_interpretation"])),
    },
  ]);

  setText("traceSummary", truncateTraceText(caseTrace.trace_summary, 600));
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
    labelCell(partCell, "Part ID");
    partCell.textContent = result.part_id || "N/A";

    const probabilityCell = document.createElement("td");
    labelCell(probabilityCell, "Scrap probability");
    probabilityCell.textContent = formatPredictionProbability(result.scrap_probability);

    const riskCell = document.createElement("td");
    labelCell(riskCell, "Risk");
    const riskBadge = document.createElement("span");
    riskBadge.className = "rca-risk";
    riskBadge.textContent = result.predicted_scrap_risk || "N/A";
    riskCell.appendChild(riskBadge);

    const summaryCell = document.createElement("td");
    labelCell(summaryCell, "Root cause summary");
    summaryCell.className = "rca-summary-cell";
    summaryCell.textContent = truncateText(
      result.root_cause_summary || "No root cause summary available.",
      118
    );

    const recommendationCell = document.createElement("td");
    labelCell(recommendationCell, "Action preview");
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
    renderWorkflowOverview(data.workflow_overview);
    renderEngineeringRulebook(data.engineering_rulebook);
    renderModelEvaluation(data.model_evaluation);
    renderCaseTrace(data.case_trace);
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
