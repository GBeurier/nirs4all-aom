import {
  abiVersion,
  fitAom,
  fitAomRidge,
  fitModel,
  fitPls,
  loadModule,
  predictModel,
  predictPls,
  version,
} from "./n4m/index.js";

const COLORS = {
  train: "#0d9488",
  test: "#4f46e5",
  baseline: "#e76f51",
  hpo: "#4f46e5",
  adaptive: "#0d9488",
  grid: "#e2e8f0",
  muted: "#64748b",
  text: "#0f172a",
};

const OPERATORS = [
  { kind: 0, name: "Identity", short: "raw X", detail: "No spectral transformation; AOM can decide that the raw view is already best." },
  { kind: 7, name: "Polynomial detrending", short: "degree 1", detail: "Subtracts the least-squares linear baseline independently from every spectrum." },
  { kind: 8, name: "Savitzky–Golay smoothing", short: "window 5 · poly 2", detail: "Applies the default five-point, second-order Savitzky–Golay smoothing operator." },
  { kind: 9, name: "Savitzky–Golay derivative", short: "window 5 · poly 2 · d1", detail: "Applies the default first-derivative Savitzky–Golay operator." },
  { kind: 15, name: "Finite difference", short: "centered · order 1", detail: "Applies the default centered first finite difference." },
];

const byId = (id) => document.getElementById(id);
let manifest = null;
let currentData = null;
let activeDatasetId = null;
let runtimeReady = false;
let comparisonSerial = 0;
let loadingDatasetId = null;

const PHASES = ["data", "pls", "aom-pls", "ridge", "aom-ridge", "results"];
const RIDGE_ALPHAS = [1e-8, 1e-6, 1e-4, 1e-2, 1, 1e2, 1e4];

function setActivity({ state, progress, title, detail, phase = null }) {
  const container = byId("activity");
  const boundedProgress = Math.max(0, Math.min(100, Math.round(progress)));
  container.dataset.state = state;
  byId("activity-title").textContent = title;
  byId("activity-detail").textContent = detail;
  byId("activity-progress-bar").style.width = `${boundedProgress}%`;
  byId("activity-progress").setAttribute("aria-valuenow", String(boundedProgress));
  const action = byId("activity-action");
  if (state === "complete") {
    action.hidden = false;
    action.href = "#results";
    action.textContent = "View results ↓";
  } else if (state === "ready") {
    action.hidden = false;
    action.href = "#experiment";
    action.textContent = "Configure and run ↓";
  } else {
    action.hidden = true;
  }
  document.querySelectorAll(".activity-phases li").forEach((item) => {
    const itemPhase = item.dataset.phase;
    const itemIndex = PHASES.indexOf(itemPhase);
    const phaseIndex = PHASES.indexOf(phase);
    item.classList.toggle("active", state !== "complete" && itemPhase === phase);
    item.classList.toggle("complete", state === "complete" || (phaseIndex >= 0 && itemIndex < phaseIndex));
  });
}

function yieldToBrowser() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

async function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text);
      return;
    } catch (error) {
      // Fall through for browsers that expose Clipboard API but deny it.
    }
  }
  const fallback = document.createElement("textarea");
  fallback.value = text;
  fallback.setAttribute("readonly", "");
  fallback.style.position = "fixed";
  fallback.style.opacity = "0";
  document.body.append(fallback);
  fallback.select();
  const copied = document.execCommand("copy");
  fallback.remove();
  if (!copied) throw new Error("Copy is unavailable in this browser.");
}

function setupCodeWorkbench() {
  const tabs = [...document.querySelectorAll('.code-tabs [role="tab"]')];
  const activate = (selected, moveFocus = true) => {
    tabs.forEach((tab) => {
      const active = tab === selected;
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
      byId(tab.getAttribute("aria-controls")).hidden = !active;
    });
    if (moveFocus) selected.focus();
  };
  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => activate(tab, false));
    tab.addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      let nextIndex = index;
      if (event.key === "ArrowLeft") nextIndex = (index - 1 + tabs.length) % tabs.length;
      if (event.key === "ArrowRight") nextIndex = (index + 1) % tabs.length;
      if (event.key === "Home") nextIndex = 0;
      if (event.key === "End") nextIndex = tabs.length - 1;
      activate(tabs[nextIndex]);
    });
  });

  document.querySelectorAll("[data-copy-target]").forEach((button) => {
    button.addEventListener("click", async () => {
      const target = byId(button.dataset.copyTarget);
      const original = button.textContent;
      try {
        await copyText(target.textContent.trim());
        button.textContent = "Copied";
        button.classList.add("copied");
        byId("copy-status").textContent = `${target.id.includes("install") ? "Installation command" : "Code example"} copied to the clipboard.`;
      } catch (error) {
        byId("copy-status").textContent = error.message;
      }
      window.setTimeout(() => {
        button.textContent = original;
        button.classList.remove("copied");
      }, 1800);
    });
  });
}

function updateUploadReadiness() {
  const inputs = ["x-cal-file", "y-cal-file", "x-val-file", "y-val-file"].map((id) => byId(id));
  const selected = inputs.filter((input) => input.files?.[0]).length;
  const button = byId("load-upload");
  button.disabled = selected !== inputs.length;
  const status = byId("upload-status");
  status.className = "form-status";
  status.textContent = selected === inputs.length
    ? "Four files selected. Validate them to inspect the dataset; nothing will be uploaded."
    : `${selected}/4 files selected. Add calibration X/y and validation X/y.`;
}

function setControlsLocked(locked) {
  document.querySelectorAll(".dataset-option, #components, #folds, #operator-controls input, .upload-card input, .upload-card select")
    .forEach((control) => { control.disabled = locked; });
  if (locked) byId("load-upload").disabled = true;
  else {
    const uploadInputs = ["x-cal-file", "y-cal-file", "x-val-file", "y-val-file"].map((id) => byId(id));
    byId("load-upload").disabled = uploadInputs.some((input) => !input.files?.[0]);
  }
}

function svgElement(name, attributes = {}) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", name);
  Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, String(value)));
  return node;
}

function addText(svg, text, attributes = {}) {
  const node = svgElement("text", attributes);
  node.textContent = text;
  svg.append(node);
  return node;
}

function finiteNumber(raw, delimiter) {
  const normalized = delimiter === "," ? raw.trim() : raw.trim().replace(",", ".");
  if (normalized === "") return null;
  const value = Number(normalized);
  return Number.isFinite(value) ? value : null;
}

function countDelimiter(line, delimiter) {
  let count = 0;
  let quoted = false;
  for (let i = 0; i < line.length; i += 1) {
    if (line[i] === '"') quoted = !quoted;
    else if (!quoted && line[i] === delimiter) count += 1;
  }
  return count;
}

function detectDelimiter(line) {
  const candidates = [";", "\t", ",", "|"];
  return candidates.map((delimiter) => [delimiter, countDelimiter(line, delimiter)])
    .sort((left, right) => right[1] - left[1])[0][0];
}

function parseDelimitedLine(line, delimiter) {
  const cells = [];
  let value = "";
  let quoted = false;
  for (let i = 0; i < line.length; i += 1) {
    const char = line[i];
    if (char === '"') {
      if (quoted && line[i + 1] === '"') {
        value += '"';
        i += 1;
      } else {
        quoted = !quoted;
      }
    } else if (char === delimiter && !quoted) {
      cells.push(value.trim());
      value = "";
    } else {
      value += char;
    }
  }
  cells.push(value.trim());
  while (cells.length > 1 && cells.at(-1) === "") cells.pop();
  return cells;
}

function delimitedRows(text) {
  const lines = text.replace(/^\uFEFF/, "").replace(/\r/g, "").split("\n")
    .map((line) => line.trim()).filter(Boolean);
  if (lines.length === 0) throw new Error("The file is empty.");
  const delimiter = detectDelimiter(lines[0]);
  return { delimiter, rows: lines.map((line) => parseDelimitedLine(line, delimiter)) };
}

function parseXText(text, { hasHeader = true } = {}) {
  const parsed = delimitedRows(text);
  const header = hasHeader ? parsed.rows.shift() : null;
  if (parsed.rows.length === 0) throw new Error("X contains no sample rows.");
  const cols = parsed.rows[0].length;
  if (cols < 2) throw new Error("X must contain at least two spectral features.");
  const values = new Float64Array(parsed.rows.length * cols);
  parsed.rows.forEach((row, rowIndex) => {
    if (row.length !== cols) throw new Error(`X row ${rowIndex + 1} has ${row.length} columns; expected ${cols}.`);
    row.forEach((raw, colIndex) => {
      const value = finiteNumber(raw, parsed.delimiter);
      if (value === null) throw new Error(`X contains a non-numeric value at row ${rowIndex + 1}, column ${colIndex + 1}.`);
      values[rowIndex * cols + colIndex] = value;
    });
  });
  let axis = Float64Array.from({ length: cols }, (_, index) => index);
  let headerLabels = null;
  if (header) {
    if (header.length !== cols) throw new Error(`X header has ${header.length} columns; sample rows have ${cols}.`);
    headerLabels = header;
    const numericHeader = header.map((raw) => finiteNumber(raw, parsed.delimiter));
    if (numericHeader.every((value) => value !== null)) axis = Float64Array.from(numericHeader);
  }
  return { data: values, rows: parsed.rows.length, cols, axis, headerLabels, delimiter: parsed.delimiter };
}

function parseYText(text) {
  const parsed = delimitedRows(text);
  let targetName = "response";
  if (parsed.rows[0].some((raw) => finiteNumber(raw, parsed.delimiter) === null)) {
    targetName = parsed.rows.shift()[0] || targetName;
  }
  if (parsed.rows.length === 0) throw new Error("y contains no response rows.");
  if (parsed.rows.some((row) => row.length !== 1)) throw new Error("y must contain exactly one response column.");
  const values = new Float64Array(parsed.rows.length);
  parsed.rows.forEach((row, index) => {
    const value = finiteNumber(row[0], parsed.delimiter);
    if (value === null) throw new Error(`y contains a non-numeric value at row ${index + 1}.`);
    values[index] = value;
  });
  return { data: values, rows: parsed.rows.length, targetName };
}

function validatePartitions(trainX, trainY, testX, testY) {
  if (trainX.rows !== trainY.rows) throw new Error(`Calibration X/y row mismatch: ${trainX.rows} versus ${trainY.rows}.`);
  if (testX.rows !== testY.rows) throw new Error(`Validation X/y row mismatch: ${testX.rows} versus ${testY.rows}.`);
  if (trainX.cols !== testX.cols) throw new Error(`Calibration/validation feature mismatch: ${trainX.cols} versus ${testX.cols}.`);
  if (trainX.rows < 4) throw new Error("At least four calibration rows are required.");
  if (testX.rows < 1) throw new Error("At least one validation row is required.");
  if (trainX.axis.length !== testX.axis.length) throw new Error("Calibration and validation feature headers differ in length.");
  for (let index = 0; index < trainX.axis.length; index += 1) {
    if (Math.abs(trainX.axis[index] - testX.axis[index]) > 1e-9) {
      throw new Error(`Calibration and validation feature headers differ at column ${index + 1}.`);
    }
  }
}

function matrix(data, rows, cols) {
  return { data, rows, cols };
}

function meanRows(buffer, rows, cols) {
  const mean = new Float64Array(cols);
  for (let row = 0; row < rows; row += 1) {
    for (let col = 0; col < cols; col += 1) mean[col] += buffer[row * cols + col];
  }
  for (let col = 0; col < cols; col += 1) mean[col] /= rows;
  return mean;
}

function extent(values) {
  let min = Infinity;
  let max = -Infinity;
  for (const value of values) {
    if (Number.isFinite(value)) {
      min = Math.min(min, value);
      max = Math.max(max, value);
    }
  }
  if (!Number.isFinite(min)) return [0, 1];
  if (min === max) return [min - .5, max + .5];
  return [min, max];
}

function paddedExtent(values, fraction = .06) {
  const [min, max] = extent(values);
  const pad = Math.max((max - min) * fraction, Number.EPSILON);
  return [min - pad, max + pad];
}

function compactNumber(value) {
  const absolute = Math.abs(value);
  if (absolute !== 0 && (absolute >= 1e4 || absolute < 1e-3)) return value.toExponential(1);
  if (absolute >= 100) return value.toFixed(0);
  if (absolute >= 10) return value.toFixed(1);
  return value.toFixed(2);
}

function axisUnit(unit) {
  if (unit === "cm-1") return "cm⁻¹";
  if (unit === "nm") return "nm";
  return "feature index";
}

function signalLabel(signal) {
  if (signal === "reflectance%") return "Reflectance (%)";
  if (signal === "absorbance") return "Absorbance";
  return "Signal";
}

function pathFromValues(values, x, y) {
  let path = "";
  for (let index = 0; index < values.length; index += 1) {
    path += `${index === 0 ? "M" : "L"}${x(index).toFixed(2)},${y(values[index]).toFixed(2)}`;
  }
  return path;
}

function addAxes(svg, options) {
  const { width, height, margin, axis, yMin, yMax, xLabel, yLabel, xTicks = 5, yTicks = 5 } = options;
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const x = (index) => margin.left + (axis.length <= 1 ? .5 : index / (axis.length - 1)) * plotWidth;
  const y = (value) => margin.top + (yMax - value) / (yMax - yMin) * plotHeight;

  for (let tick = 0; tick <= yTicks; tick += 1) {
    const value = yMin + tick * (yMax - yMin) / yTicks;
    const position = y(value);
    svg.append(svgElement("line", { x1: margin.left, y1: position, x2: width - margin.right, y2: position, class: "n4viz-grid" }));
    addText(svg, compactNumber(value), { x: margin.left - 9, y: position + 3, class: "n4viz-tick", "text-anchor": "end" });
  }
  for (let tick = 0; tick <= xTicks; tick += 1) {
    const index = Math.round(tick * (axis.length - 1) / xTicks);
    const position = x(index);
    addText(svg, compactNumber(axis[index]), { x: position, y: height - margin.bottom + 20, class: "n4viz-tick", "text-anchor": "middle" });
  }
  svg.append(svgElement("line", { x1: margin.left, y1: height - margin.bottom, x2: width - margin.right, y2: height - margin.bottom, class: "n4viz-axis" }));
  svg.append(svgElement("line", { x1: margin.left, y1: margin.top, x2: margin.left, y2: height - margin.bottom, class: "n4viz-axis" }));
  addText(svg, xLabel, { x: margin.left + plotWidth / 2, y: height - 8, class: "n4viz-axis-label", "text-anchor": "middle" });
  addText(svg, yLabel, { x: 15, y: margin.top + plotHeight / 2, class: "n4viz-axis-label", transform: `rotate(-90 15 ${margin.top + plotHeight / 2})`, "text-anchor": "middle" });
  return { x, y };
}

function drawSpectra(data) {
  const svg = byId("spectra-chart");
  svg.replaceChildren();
  const width = 760;
  const height = 360;
  const margin = { left: 62, right: 18, top: 20, bottom: 48 };
  const combined = [...data.trainX.data, ...data.testX.data];
  const [yMin, yMax] = paddedExtent(combined, .04);
  const scales = addAxes(svg, {
    width, height, margin, axis: data.axis, yMin, yMax,
    xLabel: axisUnit(data.meta.unit), yLabel: signalLabel(data.meta.signalType),
  });
  const addPartition = (buffer, rows, color, limit) => {
    const step = Math.max(1, Math.ceil(rows / limit));
    for (let row = 0; row < rows; row += step) {
      const values = buffer.subarray(row * data.cols, (row + 1) * data.cols);
      svg.append(svgElement("path", { d: pathFromValues(values, scales.x, scales.y), class: "plot-line sample", stroke: color }));
    }
    const mean = meanRows(buffer, rows, data.cols);
    svg.append(svgElement("path", { d: pathFromValues(mean, scales.x, scales.y), class: "plot-line mean n4viz-line-mean", stroke: color }));
  };
  addPartition(data.trainX.data, data.trainRows, COLORS.train, 28);
  addPartition(data.testX.data, data.testRows, COLORS.test, 14);
}

function drawTargetHistogram(data) {
  const svg = byId("target-chart");
  svg.replaceChildren();
  const width = 520;
  const height = 360;
  const margin = { left: 48, right: 16, top: 24, bottom: 48 };
  const all = [...data.trainY, ...data.testY];
  let [min, max] = extent(all);
  if (min === max) { min -= .5; max += .5; }
  const bins = Math.min(10, Math.max(5, Math.round(Math.sqrt(all.length))));
  const counts = (values) => {
    const result = new Array(bins).fill(0);
    for (const value of values) {
      const raw = Math.floor((value - min) / (max - min) * bins);
      result[Math.max(0, Math.min(bins - 1, raw))] += 1;
    }
    return result;
  };
  const trainCounts = counts(data.trainY);
  const testCounts = counts(data.testY);
  const yMax = Math.max(1, ...trainCounts, ...testCounts);
  const x = (value) => margin.left + (value - min) / (max - min) * (width - margin.left - margin.right);
  const y = (value) => height - margin.bottom - value / yMax * (height - margin.top - margin.bottom);
  for (let tick = 0; tick <= 4; tick += 1) {
    const value = tick * yMax / 4;
    const position = y(value);
    svg.append(svgElement("line", { x1: margin.left, y1: position, x2: width - margin.right, y2: position, class: "n4viz-grid" }));
    addText(svg, Math.round(value), { x: margin.left - 8, y: position + 3, class: "n4viz-tick", "text-anchor": "end" });
  }
  const groupWidth = (width - margin.left - margin.right) / bins;
  trainCounts.forEach((value, index) => {
    const baseX = margin.left + index * groupWidth;
    svg.append(svgElement("rect", { x: baseX + 2, y: y(value), width: Math.max(1, groupWidth * .47 - 3), height: height - margin.bottom - y(value), rx: 2, fill: COLORS.train, opacity: .84 }));
    svg.append(svgElement("rect", { x: baseX + groupWidth * .5, y: y(testCounts[index]), width: Math.max(1, groupWidth * .47 - 3), height: height - margin.bottom - y(testCounts[index]), rx: 2, fill: COLORS.test, opacity: .78 }));
  });
  for (let tick = 0; tick <= 4; tick += 1) {
    const value = min + tick * (max - min) / 4;
    addText(svg, compactNumber(value), { x: x(value), y: height - margin.bottom + 20, class: "n4viz-tick", "text-anchor": "middle" });
  }
  svg.append(svgElement("line", { x1: margin.left, y1: height - margin.bottom, x2: width - margin.right, y2: height - margin.bottom, class: "n4viz-axis" }));
  addText(svg, data.meta.targetName, { x: margin.left + (width - margin.left - margin.right) / 2, y: height - 8, class: "n4viz-axis-label", "text-anchor": "middle" });
  addText(svg, "samples", { x: 14, y: height / 2, class: "n4viz-axis-label", transform: `rotate(-90 14 ${height / 2})`, "text-anchor": "middle" });
  [["Calibration", COLORS.train], ["Validation", COLORS.test]].forEach(([label, color], index) => {
    const offset = 315 + index * 90;
    svg.append(svgElement("rect", { x: offset, y: 16, width: 8, height: 8, rx: 2, fill: color }));
    addText(svg, label, { x: offset + 13, y: 24, class: "n4viz-legend-label" });
  });
}

function plotPlaceholder(id, message, viewBox = [0, 0, 700, 420]) {
  const svg = byId(id);
  svg.replaceChildren();
  const [x, y, width, height] = viewBox;
  addText(svg, message, { x: x + width / 2, y: y + height / 2, class: "n4viz-axis-label", "text-anchor": "middle" });
}

function resetResults() {
  [
    "pls-default-selection", "pls-default-rmse", "pls-default-mae", "pls-default-r2", "pls-default-time",
    "pls-hpo-selection", "pls-hpo-rmse", "pls-hpo-mae", "pls-hpo-r2", "pls-hpo-time",
    "aom-pls-selection", "aom-pls-rmse", "aom-pls-mae", "aom-pls-r2", "aom-pls-time",
    "ridge-default-selection", "ridge-default-rmse", "ridge-default-mae", "ridge-default-r2", "ridge-default-time",
    "ridge-hpo-selection", "ridge-hpo-rmse", "ridge-hpo-mae", "ridge-hpo-r2", "ridge-hpo-time",
    "aom-ridge-selection", "aom-ridge-rmse", "aom-ridge-mae", "aom-ridge-r2", "aom-ridge-time",
  ].forEach((id) => { byId(id).textContent = "—"; });
  byId("operator").textContent = "—";
  byId("operator-detail").textContent = "The selected operator will appear here.";
  byId("rmse-delta").textContent = "—";
  byId("rmse-delta").className = "";
  byId("delta-detail").textContent = "held-out RMSE difference";
  byId("ridge-rmse-delta").textContent = "—";
  byId("ridge-rmse-delta").className = "";
  byId("ridge-delta-detail").textContent = "held-out RMSE difference";
  byId("result-summary").textContent = "Run the comparison to populate six held-out results, selected settings and diagnostic plots.";
  byId("operator-preview-title").textContent = "Raw vs selected operator view";
  byId("operator-explanation").textContent = "AOM will select one operator from the configured bank.";
  plotPlaceholder("rmse-chart", "Awaiting six fitted routes", [0, 0, 1280, 420]);
  plotPlaceholder("pls-prediction-chart", "Awaiting the PLS comparison", [0, 0, 620, 420]);
  plotPlaceholder("ridge-prediction-chart", "Awaiting the Ridge comparison", [0, 0, 620, 420]);
  plotPlaceholder("operator-chart", "Awaiting AOM operator selection", [0, 0, 560, 420]);
  plotPlaceholder("coefficient-chart", "Awaiting deployable coefficients", [0, 0, 1280, 360]);
}

function sourceUrl(dataset) {
  return `${manifest.snapshot.repository}/tree/${manifest.snapshot.commit}/${dataset.sourcePath}`;
}

function renderDatasetOptions() {
  const container = byId("dataset-options");
  container.replaceChildren();
  manifest.datasets.forEach((dataset) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "dataset-option";
    button.setAttribute("role", "radio");
    button.setAttribute("aria-checked", String(dataset.id === activeDatasetId));
    button.dataset.loading = String(dataset.id === loadingDatasetId);
    button.setAttribute("aria-busy", String(dataset.id === loadingDatasetId));
    const radio = document.createElement("span");
    radio.className = "radio";
    const copy = document.createElement("span");
    const strong = document.createElement("strong");
    strong.textContent = dataset.label;
    const small = document.createElement("small");
    small.textContent = dataset.short;
    copy.append(strong, small);
    const unit = document.createElement("span");
    unit.className = "unit";
    unit.textContent = dataset.id === loadingDatasetId ? "Loading…" : axisUnit(dataset.unit);
    button.append(radio, copy, unit);
    button.addEventListener("click", () => loadBundledDataset(dataset.id));
    container.append(button);
  });
}

function setDatasetUi(data) {
  byId("dataset-name").textContent = data.meta.label;
  byId("dataset-kind").textContent = data.meta.kind;
  byId("dataset-description").textContent = data.meta.description;
  byId("train-shape").textContent = `${data.trainRows} × ${data.cols}`;
  byId("test-shape").textContent = `${data.testRows} × ${data.cols}`;
  byId("axis-range").textContent = `${compactNumber(data.axis[0])} → ${compactNumber(data.axis.at(-1))} ${axisUnit(data.meta.unit)}`;
  const [targetMin, targetMax] = extent([...data.trainY, ...data.testY]);
  byId("target-range").textContent = `${compactNumber(targetMin)} → ${compactNumber(targetMax)}`;
  byId("dataset-provenance").textContent = data.meta.provenance;
  const link = byId("dataset-source-link");
  if (data.meta.sourceUrl) {
    link.href = data.meta.sourceUrl;
    link.hidden = false;
  } else {
    link.hidden = true;
  }
  byId("fairness-text").textContent = `${data.trainRows} calibration rows · ${data.testRows} held-out rows · ${data.cols} shared features`;
  drawSpectra(data);
  drawTargetHistogram(data);
  resetResults();
}

async function loadBundledDataset(id, runAfterLoad = false, announceReady = true) {
  const dataset = manifest.datasets.find((item) => item.id === id);
  if (!dataset) throw new Error(`Unknown bundled dataset: ${id}`);
  activeDatasetId = id;
  loadingDatasetId = id;
  renderDatasetOptions();
  byId("dataset-name").textContent = "Loading dataset…";
  setActivity({
    state: "loading", progress: 10, phase: "data",
    title: "Loading dataset",
    detail: `Reading ${dataset.label}: Xcal, Ycal, Xval and Yval…`,
  });
  const base = `datasets/${dataset.id}`;
  try {
    const responses = await Promise.all(["Xcal.csv", "Ycal.csv", "Xval.csv", "Yval.csv"].map((name) => fetch(`${base}/${name}`)));
    responses.forEach((response) => {
      if (!response.ok) throw new Error(`Could not load ${response.url} (${response.status}).`);
    });
    const texts = await Promise.all(responses.map((response) => response.text()));
    const trainX = parseXText(texts[0], { hasHeader: true });
    const trainY = parseYText(texts[1]);
    const testX = parseXText(texts[2], { hasHeader: true });
    const testY = parseYText(texts[3]);
    validatePartitions(trainX, trainY, testX, testY);
    currentData = {
      trainX, trainY: trainY.data, testX, testY: testY.data,
      trainRows: trainX.rows, testRows: testX.rows, cols: trainX.cols, axis: trainX.axis,
      meta: {
        label: dataset.label,
        kind: "Bundled fixture",
        unit: dataset.unit,
        signalType: dataset.signalType,
        targetName: trainY.targetName || dataset.target,
        description: dataset.description,
        provenance: dataset.provenance,
        sourceUrl: sourceUrl(dataset),
      },
    };
    setDatasetUi(currentData);
    loadingDatasetId = null;
    renderDatasetOptions();
    byId("run-note").textContent = `${dataset.label} is ready. Review the settings, then run all six routes.`;
    byId("run-note").className = "form-status success";
    if (announceReady) {
      setActivity({
        state: "ready", progress: 25, phase: "pls",
        title: "Dataset ready",
        detail: `${dataset.label}: ${trainX.rows} calibration rows, ${testX.rows} validation rows and ${trainX.cols} features. Run the PLS and Ridge comparison when ready.`,
      });
    }
    if (runAfterLoad && runtimeReady) await runComparison();
  } catch (error) {
    console.error(error);
    loadingDatasetId = null;
    renderDatasetOptions();
    byId("dataset-name").textContent = "Dataset failed to load";
    byId("dataset-description").textContent = location.protocol === "file:"
      ? "Serve this directory over HTTP; browsers cannot fetch the CSV and WASM files from file://."
      : error.message;
    setActivity({ state: "error", progress: 10, phase: "data", title: "Dataset could not be loaded", detail: error.message });
  }
}

function selectedOperators() {
  return [...document.querySelectorAll("#operator-controls input:checked")]
    .map((input) => OPERATORS.find((operator) => operator.kind === Number(input.value)))
    .filter(Boolean);
}

function renderOperatorControls() {
  const container = byId("operator-controls");
  OPERATORS.forEach((operator) => {
    const label = document.createElement("label");
    label.className = "operator-check";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = String(operator.kind);
    input.checked = true;
    const name = document.createElement("span");
    name.textContent = operator.name;
    const detail = document.createElement("small");
    detail.textContent = operator.short;
    label.append(input, name, detail);
    container.append(label);
    input.addEventListener("change", () => {
      if (selectedOperators().length === 0) {
        input.checked = true;
        byId("run-note").textContent = "Keep at least one operator in the AOM bank.";
        byId("run-note").className = "form-status error";
        setActivity({ state: "error", progress: 25, phase: "aom-pls", title: "Operator bank cannot be empty", detail: "Keep at least one spectral operator selected." });
      } else {
        markResultsStale();
      }
    });
  });
}

function markResultsStale() {
  if (!currentData) return;
  resetResults();
  byId("run-note").textContent = "Configuration changed. Run again to refresh the held-out comparison.";
  byId("run-note").className = "form-status";
  setActivity({
    state: "ready", progress: 25, phase: "pls",
    title: "Configuration ready",
    detail: "Settings changed. Run the PLS and Ridge comparison to calculate new results.",
  });
}

function selectRows(buffer, rowIndices, cols) {
  const output = new Float64Array(rowIndices.length * cols);
  rowIndices.forEach((sourceRow, outputRow) => {
    output.set(buffer.subarray(sourceRow * cols, (sourceRow + 1) * cols), outputRow * cols);
  });
  return output;
}

function contiguousFolds(rows, count) {
  const folds = Array.from({ length: count }, () => []);
  for (let row = 0; row < rows; row += 1) folds[Math.floor(row * count / rows)].push(row);
  return folds;
}

function metrics(actual, predicted) {
  const mean = actual.reduce((sum, value) => sum + value, 0) / actual.length;
  let squaredError = 0;
  let absoluteError = 0;
  let total = 0;
  for (let index = 0; index < actual.length; index += 1) {
    const error = actual[index] - predicted[index];
    squaredError += error * error;
    absoluteError += Math.abs(error);
    total += (actual[index] - mean) ** 2;
  }
  return {
    rmse: Math.sqrt(squaredError / actual.length),
    mae: absoluteError / actual.length,
    r2: total > 0 ? 1 - squaredError / total : NaN,
  };
}

async function fitCrossValidatedPls(data, maxComponents, foldCount, onProgress) {
  let elapsed = 0;
  const folds = contiguousFolds(data.trainRows, foldCount);
  const allRows = Array.from({ length: data.trainRows }, (_, index) => index);
  const maxAllowed = Math.max(1, Math.min(maxComponents, data.cols, ...folds.map((held) => data.trainRows - held.length - 1)));
  const candidates = [];
  const totalFits = maxAllowed * folds.length + 1;
  let completedFits = 0;
  for (let components = 1; components <= maxAllowed; components += 1) {
    const oof = new Float64Array(data.trainRows);
    let validCandidate = true;
    for (const heldRows of folds) {
      const held = new Set(heldRows);
      const fitRows = allRows.filter((row) => !held.has(row));
      const xFit = selectRows(data.trainX.data, fitRows, data.cols);
      const yFit = selectRows(data.trainY, fitRows, 1);
      const xHeld = selectRows(data.trainX.data, heldRows, data.cols);
      const fitStarted = performance.now();
      try {
        const model = fitPls(matrix(xFit, fitRows.length, data.cols), matrix(yFit, fitRows.length, 1), components);
        const predictions = predictPls(model, matrix(xHeld, heldRows.length, data.cols)).data;
        elapsed += performance.now() - fitStarted;
        heldRows.forEach((row, index) => { oof[row] = predictions[index]; });
      } catch (error) {
        elapsed += performance.now() - fitStarted;
        validCandidate = false;
      }
      completedFits += 1;
      onProgress?.(completedFits / totalFits, components, maxAllowed);
      if (!validCandidate) break;
    }
    if (validCandidate) candidates.push({ components, rmse: metrics(data.trainY, oof).rmse });
    await yieldToBrowser();
  }
  if (candidates.length === 0) throw new Error("No numerically stable PLS component count was found.");
  candidates.sort((left, right) => left.rmse - right.rmse || left.components - right.components);
  const selected = candidates[0];
  const finalFitStarted = performance.now();
  const model = fitPls(matrix(data.trainX.data, data.trainRows, data.cols), matrix(data.trainY, data.trainRows, 1), selected.components);
  completedFits += 1;
  onProgress?.(completedFits / totalFits, selected.components, maxAllowed);
  const predictions = predictPls(model, matrix(data.testX.data, data.testRows, data.cols)).data;
  elapsed += performance.now() - finalFitStarted;
  return { model, predictions, components: selected.components, cvRmse: selected.rmse, elapsed, maxAllowed, candidateFits: completedFits };
}

function transformedDataset(data, operator) {
  if (operator.kind === 0) return data;
  return {
    ...data,
    trainX: matrix(operatorView(data.trainX.data, data.trainRows, data.cols, operator.kind), data.trainRows, data.cols),
    testX: matrix(operatorView(data.testX.data, data.testRows, data.cols, operator.kind), data.testRows, data.cols),
  };
}

async function fitPreprocessingHpoPls(data, maxComponents, foldCount, operators, onProgress) {
  const candidates = [];
  let elapsed = 0;
  let candidateFits = 0;
  for (let operatorIndex = 0; operatorIndex < operators.length; operatorIndex += 1) {
    const operator = operators[operatorIndex];
    const transformStarted = performance.now();
    const transformed = transformedDataset(data, operator);
    elapsed += performance.now() - transformStarted;
    try {
      const result = await fitCrossValidatedPls(transformed, maxComponents, foldCount, (fraction, component, total) => {
        onProgress?.((operatorIndex + fraction) / operators.length, operator, component, total);
      });
      elapsed += result.elapsed;
      candidateFits += result.candidateFits;
      candidates.push({ operator, result });
    } catch (error) {
      onProgress?.((operatorIndex + 1) / operators.length, operator, maxComponents, maxComponents);
    }
  }
  if (candidates.length === 0) throw new Error("No numerically stable PLS preprocessing route was found.");
  candidates.sort((left, right) => left.result.cvRmse - right.result.cvRmse
    || left.result.components - right.result.components
    || left.operator.kind - right.operator.kind);
  const selected = candidates[0];
  return { ...selected.result, operator: selected.operator, elapsed, candidateFits };
}

async function fitCrossValidatedRidge(data, foldCount, alphas, onProgress) {
  let elapsed = 0;
  const folds = contiguousFolds(data.trainRows, foldCount);
  const allRows = Array.from({ length: data.trainRows }, (_, index) => index);
  const candidates = [];
  const totalFits = alphas.length * folds.length + 1;
  let completedFits = 0;
  for (let alphaIndex = 0; alphaIndex < alphas.length; alphaIndex += 1) {
    const alpha = alphas[alphaIndex];
    const oof = new Float64Array(data.trainRows);
    let validCandidate = true;
    for (const heldRows of folds) {
      const held = new Set(heldRows);
      const fitRows = allRows.filter((row) => !held.has(row));
      const xFit = selectRows(data.trainX.data, fitRows, data.cols);
      const yFit = selectRows(data.trainY, fitRows, 1);
      const xHeld = selectRows(data.trainX.data, heldRows, data.cols);
      const fitStarted = performance.now();
      try {
        const model = fitModel("Ridge", matrix(xFit, fitRows.length, data.cols), matrix(yFit, fitRows.length, 1), 1, [alpha]);
        const predictions = predictModel(model, matrix(xHeld, heldRows.length, data.cols)).data;
        elapsed += performance.now() - fitStarted;
        heldRows.forEach((row, index) => { oof[row] = predictions[index]; });
      } catch (error) {
        elapsed += performance.now() - fitStarted;
        validCandidate = false;
      }
      completedFits += 1;
      onProgress?.(completedFits / totalFits, alpha, alphaIndex + 1, alphas.length);
      if (!validCandidate) break;
    }
    if (validCandidate) candidates.push({ alpha, rmse: metrics(data.trainY, oof).rmse });
    await yieldToBrowser();
  }
  if (candidates.length === 0) throw new Error("No numerically stable Ridge regularisation value was found.");
  candidates.sort((left, right) => left.rmse - right.rmse || left.alpha - right.alpha);
  const selected = candidates[0];
  const finalFitStarted = performance.now();
  const model = fitModel(
    "Ridge",
    matrix(data.trainX.data, data.trainRows, data.cols),
    matrix(data.trainY, data.trainRows, 1),
    1,
    [selected.alpha],
  );
  const predictions = predictModel(model, matrix(data.testX.data, data.testRows, data.cols)).data;
  elapsed += performance.now() - finalFitStarted;
  completedFits += 1;
  onProgress?.(completedFits / totalFits, selected.alpha, alphas.length, alphas.length);
  return { model, predictions, alpha: selected.alpha, cvRmse: selected.rmse, elapsed, candidateFits: completedFits };
}

async function fitPreprocessingHpoRidge(data, foldCount, alphas, operators, onProgress) {
  const candidates = [];
  let elapsed = 0;
  let candidateFits = 0;
  for (let operatorIndex = 0; operatorIndex < operators.length; operatorIndex += 1) {
    const operator = operators[operatorIndex];
    const transformStarted = performance.now();
    const transformed = transformedDataset(data, operator);
    elapsed += performance.now() - transformStarted;
    try {
      const result = await fitCrossValidatedRidge(transformed, foldCount, alphas, (fraction, alpha, alphaIndex, alphaCount) => {
        onProgress?.((operatorIndex + fraction) / operators.length, operator, alpha, alphaIndex, alphaCount);
      });
      elapsed += result.elapsed;
      candidateFits += result.candidateFits;
      candidates.push({ operator, result });
    } catch (error) {
      onProgress?.((operatorIndex + 1) / operators.length, operator, alphas.at(-1), alphas.length, alphas.length);
    }
  }
  if (candidates.length === 0) throw new Error("No numerically stable Ridge preprocessing route was found.");
  candidates.sort((left, right) => left.result.cvRmse - right.result.cvRmse
    || left.result.alpha - right.result.alpha
    || left.operator.kind - right.operator.kind);
  const selected = candidates[0];
  return { ...selected.result, operator: selected.operator, elapsed, candidateFits };
}

function formatMetric(value) {
  if (!Number.isFinite(value)) return "n/a";
  const absolute = Math.abs(value);
  if (absolute !== 0 && absolute < .001) return value.toExponential(3);
  return value.toFixed(4);
}

function formatTime(milliseconds) {
  if (milliseconds < .1) return "<0.1 ms";
  if (milliseconds < 1000) return `${milliseconds.toFixed(1)} ms`;
  return `${(milliseconds / 1000).toFixed(2)} s`;
}

function signedPercent(aom, baseline, lowerIsBetter = true) {
  if (!Number.isFinite(aom) || !Number.isFinite(baseline) || baseline === 0) return { text: "n/a", improvement: 0, raw: NaN };
  const raw = (aom - baseline) / Math.abs(baseline) * 100;
  const improvement = lowerIsBetter ? -raw : raw;
  return { text: `${raw >= 0 ? "+" : ""}${raw.toFixed(1)}%`, improvement, raw };
}

function classForImprovement(improvement, tolerance = .05) {
  if (improvement > tolerance) return "positive";
  if (improvement < -tolerance) return "negative";
  return "neutral";
}

function setDeltaCell(id, delta) {
  const cell = byId(id);
  cell.textContent = delta.text;
  cell.className = classForImprovement(delta.improvement);
}

function drawPredictionChart(id, actual, series) {
  const svg = byId(id);
  svg.replaceChildren();
  const width = 620;
  const height = 420;
  const margin = { left: 62, right: 20, top: 22, bottom: 54 };
  const [min, max] = paddedExtent([...actual, ...series.flatMap((item) => [...item.predictions])], .08);
  const axis = Float64Array.from({ length: 101 }, (_, index) => min + index * (max - min) / 100);
  const scales = addAxes(svg, { width, height, margin, axis, yMin: min, yMax: max, xLabel: "Measured response", yLabel: "Predicted response", xTicks: 4, yTicks: 4 });
  const xValue = (value) => margin.left + (value - min) / (max - min) * (width - margin.left - margin.right);
  svg.append(svgElement("line", { x1: xValue(min), y1: scales.y(min), x2: xValue(max), y2: scales.y(max), class: "identity-line" }));
  series.forEach((item, seriesIndex) => {
    item.predictions.forEach((value, index) => svg.append(svgElement("circle", {
      cx: xValue(actual[index]), cy: scales.y(value), r: 5.4 - seriesIndex * .45, class: `prediction-point ${item.className}`,
    })));
  });
}

function drawRmseChart(results) {
  const svg = byId("rmse-chart");
  svg.replaceChildren();
  const width = 1280;
  const height = 420;
  const margin = { left: 78, right: 30, top: 30, bottom: 76 };
  const max = Math.max(...results.map((item) => item.rmse)) * 1.16;
  const plotHeight = height - margin.top - margin.bottom;
  const y = (value) => margin.top + (max - value) / max * plotHeight;
  const groupCenters = [width * .31, width * .72];
  const barWidth = 116;
  const offsets = [-barWidth - 12, 0, barWidth + 12];
  for (let tick = 0; tick <= 4; tick += 1) {
    const value = max * tick / 4;
    const position = y(value);
    svg.append(svgElement("line", { x1: margin.left, y1: position, x2: width - margin.right, y2: position, class: "n4viz-grid" }));
    addText(svg, compactNumber(value), { x: margin.left - 10, y: position + 4, class: "n4viz-tick", "text-anchor": "end" });
  }
  const colors = [COLORS.baseline, COLORS.hpo, COLORS.adaptive];
  results.forEach((item, index) => {
    const familyIndex = index < 3 ? 0 : 1;
    const routeIndex = index % 3;
    const x = groupCenters[familyIndex] + offsets[routeIndex] - barWidth / 2;
    const top = y(item.rmse);
    svg.append(svgElement("rect", { x, y: top, width: barWidth, height: height - margin.bottom - top, rx: 7, fill: colors[routeIndex], opacity: routeIndex === 1 ? .84 : .92 }));
    addText(svg, formatMetric(item.rmse), { x: x + barWidth / 2, y: top - 10, class: "bar-value", "text-anchor": "middle" });
    addText(svg, ["Raw", "HPO", "AOM"][routeIndex], { x: x + barWidth / 2, y: height - margin.bottom + 22, class: "n4viz-tick", "text-anchor": "middle" });
  });
  addText(svg, "PLS", { x: groupCenters[0], y: height - 16, class: "bar-family", "text-anchor": "middle" });
  addText(svg, "Ridge", { x: groupCenters[1], y: height - 16, class: "bar-family", "text-anchor": "middle" });
  addText(svg, "Validation RMSE", { x: 18, y: height / 2, class: "n4viz-axis-label", transform: `rotate(-90 18 ${height / 2})`, "text-anchor": "middle" });
}

function xcorrZeroPad(buffer, rows, cols, kernel) {
  const output = new Float64Array(buffer.length);
  const half = Math.floor((kernel.length - 1) / 2);
  for (let row = 0; row < rows; row += 1) {
    for (let col = 0; col < cols; col += 1) {
      let sum = 0;
      kernel.forEach((coefficient, kernelIndex) => {
        const source = col + kernelIndex - half;
        if (source >= 0 && source < cols) sum += coefficient * buffer[row * cols + source];
      });
      output[row * cols + col] = sum;
    }
  }
  return output;
}

function detrendLinear(buffer, rows, cols) {
  const output = new Float64Array(buffer.length);
  const x = Float64Array.from({ length: cols }, (_, index) => cols > 1 ? -1 + 2 * index / (cols - 1) : 0);
  const sumX = x.reduce((sum, value) => sum + value, 0);
  const sumXX = x.reduce((sum, value) => sum + value * value, 0);
  for (let row = 0; row < rows; row += 1) {
    let sumY = 0;
    let sumXY = 0;
    for (let col = 0; col < cols; col += 1) {
      const value = buffer[row * cols + col];
      sumY += value;
      sumXY += x[col] * value;
    }
    const denominator = cols * sumXX - sumX * sumX;
    const slope = (cols * sumXY - sumX * sumY) / denominator;
    const intercept = (sumY - slope * sumX) / cols;
    for (let col = 0; col < cols; col += 1) output[row * cols + col] = buffer[row * cols + col] - intercept - slope * x[col];
  }
  return output;
}

function operatorView(buffer, rows, cols, kind) {
  if (kind === 0) return buffer.slice();
  if (kind === 7) return detrendLinear(buffer, rows, cols);
  if (kind === 8) return xcorrZeroPad(buffer, rows, cols, [-3 / 35, 12 / 35, 17 / 35, 12 / 35, -3 / 35]);
  if (kind === 9) return xcorrZeroPad(buffer, rows, cols, [-.2, -.1, 0, .1, .2]);
  if (kind === 15) return xcorrZeroPad(buffer, rows, cols, [-.5, 0, .5]);
  return buffer.slice();
}

function drawOperatorPanel(svg, values, data, top, bottom, color, title, trim = 0) {
  const width = 560;
  const margin = { left: 60, right: 18 };
  const visibleValues = trim > 0 ? values.slice(trim, values.length - trim) : values;
  const [yMin, yMax] = paddedExtent(visibleValues, .08);
  const x = (index) => margin.left + index / (values.length - 1) * (width - margin.left - margin.right);
  const y = (value) => Math.max(top, Math.min(bottom, top + (yMax - value) / (yMax - yMin) * (bottom - top)));
  for (let tick = 0; tick <= 2; tick += 1) {
    const value = yMin + tick * (yMax - yMin) / 2;
    const position = y(value);
    svg.append(svgElement("line", { x1: margin.left, y1: position, x2: width - margin.right, y2: position, class: "n4viz-grid" }));
    addText(svg, compactNumber(value), { x: margin.left - 8, y: position + 3, class: "n4viz-tick", "text-anchor": "end" });
  }
  addText(svg, title, { x: margin.left, y: top - 10, class: "n4viz-axis-label" });
  svg.append(svgElement("path", { d: pathFromValues(values, x, y), class: "plot-line mean", stroke: color }));
  return x;
}

function drawOperatorChart(data, operator) {
  const svg = byId("operator-chart");
  svg.replaceChildren();
  const sortedRows = Array.from({ length: data.trainRows }, (_, index) => index)
    .sort((left, right) => data.trainY[left] - data.trainY[right]);
  const representativeRow = sortedRows[Math.floor(sortedRows.length / 2)];
  const rawSpectrum = data.trainX.data.slice(representativeRow * data.cols, (representativeRow + 1) * data.cols);
  const transformed = operatorView(data.trainX.data, data.trainRows, data.cols, operator.kind);
  const transformedSpectrum = transformed.slice(representativeRow * data.cols, (representativeRow + 1) * data.cols);
  const trim = operator.kind === 8 || operator.kind === 9 ? 2 : operator.kind === 15 ? 1 : 0;
  const x = drawOperatorPanel(svg, rawSpectrum, data, 54, 178, COLORS.baseline, `A · raw representative spectrum (${signalLabel(data.meta.signalType)})`);
  drawOperatorPanel(svg, transformedSpectrum, data, 244, 368, COLORS.adaptive, `B · ${operator.name} view (independent y scale)`, trim);
  for (let tick = 0; tick <= 4; tick += 1) {
    const index = Math.round(tick * (data.axis.length - 1) / 4);
    addText(svg, compactNumber(data.axis[index]), { x: x(index), y: 397, class: "n4viz-tick", "text-anchor": "middle" });
  }
  addText(svg, axisUnit(data.meta.unit), { x: 310, y: 416, class: "n4viz-axis-label", "text-anchor": "middle" });
}

function drawCoefficientChart(data, plsCoefficients, aomCoefficients) {
  const svg = byId("coefficient-chart");
  svg.replaceChildren();
  const width = 1280;
  const height = 360;
  const margin = { left: 72, right: 24, top: 22, bottom: 52 };
  const [yMin, yMax] = paddedExtent([...plsCoefficients, ...aomCoefficients], .07);
  const scales = addAxes(svg, { width, height, margin, axis: data.axis, yMin, yMax, xLabel: axisUnit(data.meta.unit), yLabel: "coefficient", xTicks: 6, yTicks: 4 });
  if (yMin < 0 && yMax > 0) svg.append(svgElement("line", { x1: margin.left, y1: scales.y(0), x2: width - margin.right, y2: scales.y(0), class: "n4viz-axis" }));
  svg.append(svgElement("path", { d: pathFromValues(plsCoefficients, scales.x, scales.y), class: "plot-line coefficient-pls" }));
  svg.append(svgElement("path", { d: pathFromValues(aomCoefficients, scales.x, scales.y), class: "plot-line coefficient-aom" }));
}

function formatAlpha(alpha) {
  if (!Number.isFinite(alpha)) return "n/a";
  if (alpha >= .01 && alpha < 1000) return alpha.toLocaleString("en-US", { maximumFractionDigits: 4 });
  return alpha.toExponential(0).replace("e+", "e");
}

function renderMethodResult(prefix, result, stats, selection) {
  byId(`${prefix}-selection`).textContent = selection;
  byId(`${prefix}-rmse`).textContent = formatMetric(stats.rmse);
  byId(`${prefix}-mae`).textContent = formatMetric(stats.mae);
  byId(`${prefix}-r2`).textContent = formatMetric(stats.r2);
  byId(`${prefix}-time`).textContent = `${formatTime(result.elapsed)} · ${result.searchLabel || `${result.candidateFits ?? 1} fit calls`}`;
}

function setComparisonBanner(valueId, detailId, aomStats, hpoStats, label) {
  const delta = signedPercent(aomStats.rmse, hpoStats.rmse, true);
  const value = byId(valueId);
  value.className = classForImprovement(delta.improvement);
  value.textContent = Math.abs(delta.raw) < .05
    ? "no material change"
    : `${Math.abs(delta.raw).toFixed(1)}% ${delta.raw < 0 ? "lower" : "higher"}`;
  byId(detailId).textContent = `${label}: AOM ${formatMetric(aomStats.rmse)} vs HPO ${formatMetric(hpoStats.rmse)} RMSE`;
}

function fitAomPlsWithStableBudget(data, requestedBudget, foldCount, operatorKinds) {
  const budgets = [...new Set([requestedBudget, 20, 15, 10, 5, 3, 1])]
    .filter((value) => value <= requestedBudget && value >= 1)
    .sort((left, right) => right - left);
  let lastError = null;
  for (const budget of budgets) {
    try {
      const model = fitAom(
        matrix(data.trainX.data, data.trainRows, data.cols),
        matrix(data.trainY, data.trainRows, 1),
        budget,
        foldCount,
        0,
        operatorKinds,
      );
      return { model, budget };
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError || new Error("AOM-PLS could not find a numerically stable component budget.");
}

async function runComparison() {
  if (!runtimeReady || !currentData) return;
  const serial = ++comparisonSerial;
  const button = byId("run");
  const operators = selectedOperators();
  resetResults();
  setControlsLocked(true);
  button.disabled = true;
  button.querySelector("span").textContent = "Comparison in progress…";
  byId("run-note").textContent = "Step 1/6: selecting the raw PLS component count by calibration CV.";
  byId("run-note").className = "form-status";
  setActivity({
    state: "running", progress: 26, phase: "pls",
    title: "PLS · raw reference",
    detail: "Cross-validating component counts on the raw calibration spectra…",
  });
  await yieldToBrowser();

  try {
    const requestedComponents = Number(byId("components").value);
    const foldCount = Math.max(2, Math.min(Number(byId("folds").value), currentData.trainRows));
    const minFoldTrain = currentData.trainRows - Math.ceil(currentData.trainRows / foldCount);
    const componentBudget = Math.max(1, Math.min(requestedComponents, currentData.cols, minFoldTrain - 1));
    const rawPls = await fitCrossValidatedPls(currentData, componentBudget, foldCount, (fraction, component, total) => {
      setActivity({
        state: "running", progress: 26 + fraction * 8, phase: "pls",
        title: "PLS · raw reference",
        detail: `Calibration CV: component ${component}/${total}, ${foldCount} folds.`,
      });
    });

    byId("run-note").textContent = `Step 2/6: conventional PLS HPO is screening ${operators.length} operators × ${componentBudget} component counts.`;
    setActivity({
      state: "running", progress: 34, phase: "pls",
      title: "PLS · preprocessing HPO",
      detail: `External CV grid: ${operators.length} operators × ${componentBudget} component counts…`,
    });
    await yieldToBrowser();
    const hpoPls = await fitPreprocessingHpoPls(currentData, componentBudget, foldCount, operators, (fraction, operator, component, total) => {
      setActivity({
        state: "running", progress: 34 + fraction * 18, phase: "pls",
        title: "PLS · preprocessing HPO",
        detail: `${operator.name}: component ${component}/${total}, ${foldCount} folds.`,
      });
    });

    byId("run-note").textContent = `Step 3/6: native AOM-PLS is screening the same ${operators.length}-operator bank up to ${componentBudget} components.`;
    setActivity({
      state: "running", progress: 52, phase: "aom-pls",
      title: "Running AOM-PLS",
      detail: `Native operator/component selection on the calibration rows…`,
    });
    await yieldToBrowser();
    const aomPlsStarted = performance.now();
    const aomPlsFit = fitAomPlsWithStableBudget(
      currentData,
      componentBudget,
      foldCount,
      operators.map((operator) => operator.kind),
    );
    const aomPlsModel = aomPlsFit.model;
    const aomPlsPredictions = predictModel(aomPlsModel, matrix(currentData.testX.data, currentData.testRows, currentData.cols)).data;
    const aomPls = {
      model: aomPlsModel,
      predictions: aomPlsPredictions,
      elapsed: performance.now() - aomPlsStarted,
      candidateFits: operators.length * aomPlsFit.budget * foldCount + 1,
      searchLabel: `${operators.length} ops × H≤${aomPlsFit.budget}`,
    };

    byId("run-note").textContent = `Step 4/6: selecting Ridge α on raw spectra, then screening preprocessing + α.`;
    setActivity({
      state: "running", progress: 63, phase: "ridge",
      title: "Ridge · raw reference",
      detail: `Cross-validating ${RIDGE_ALPHAS.length} logarithmic regularisation values…`,
    });
    await yieldToBrowser();
    const rawRidge = await fitCrossValidatedRidge(currentData, foldCount, RIDGE_ALPHAS, (fraction, alpha) => {
      setActivity({
        state: "running", progress: 63 + fraction * 5, phase: "ridge",
        title: "Ridge · raw reference",
        detail: `Calibration CV: α ${formatAlpha(alpha)}, ${foldCount} folds.`,
      });
    });

    byId("run-note").textContent = `Step 5/6: conventional Ridge HPO is screening ${operators.length} operators × ${RIDGE_ALPHAS.length} α values.`;
    const hpoRidge = await fitPreprocessingHpoRidge(currentData, foldCount, RIDGE_ALPHAS, operators, (fraction, operator, alpha) => {
      setActivity({
        state: "running", progress: 68 + fraction * 16, phase: "ridge",
        title: "Ridge · preprocessing HPO",
        detail: `${operator.name}: α ${formatAlpha(alpha)}, ${foldCount} folds.`,
      });
    });

    byId("run-note").textContent = "Step 6/6: fitting the native compact AOM-Ridge simplex blender.";
    setActivity({
      state: "running", progress: 85, phase: "aom-ridge",
      title: "Running AOM-Ridge Blender",
      detail: `Blending compact operator-chain × Ridge-α candidates with ${foldCount}-fold calibration CV…`,
    });
    await yieldToBrowser();
    const aomRidgeStarted = performance.now();
    const aomRidgeModel = fitAomRidge(
      matrix(currentData.trainX.data, currentData.trainRows, currentData.cols),
      matrix(currentData.trainY, currentData.trainRows, 1),
      { profile: 0, cv: foldCount, ridgeLambdas: RIDGE_ALPHAS, regularizer: .01 },
    );
    const aomRidge = {
      model: aomRidgeModel,
      predictions: predictModel(aomRidgeModel, matrix(currentData.testX.data, currentData.testRows, currentData.cols)).data,
      elapsed: performance.now() - aomRidgeStarted,
      candidateFits: 12 * RIDGE_ALPHAS.length * foldCount + 12,
      searchLabel: `12 chains × ${RIDGE_ALPHAS.length} α`,
    };
    if (serial !== comparisonSerial) return;

    setActivity({
      state: "running", progress: 94, phase: "results",
      title: "Calculating held-out results",
      detail: `Comparing six prediction vectors on ${currentData.testRows} untouched validation rows…`,
    });
    await yieldToBrowser();

    const rawPlsStats = metrics(currentData.testY, rawPls.predictions);
    const hpoPlsStats = metrics(currentData.testY, hpoPls.predictions);
    const aomPlsStats = metrics(currentData.testY, aomPls.predictions);
    const rawRidgeStats = metrics(currentData.testY, rawRidge.predictions);
    const hpoRidgeStats = metrics(currentData.testY, hpoRidge.predictions);
    const aomRidgeStats = metrics(currentData.testY, aomRidge.predictions);
    const selected = operators[aomPlsModel.selectedOperator] || { name: `Bank entry ${aomPlsModel.selectedOperator}`, short: "custom", detail: "Selected entry in the configured operator bank.", kind: operators[0].kind };

    byId("operator").textContent = selected.name;
    byId("operator-detail").textContent = `${selected.short} · bank entry ${aomPlsModel.selectedOperator + 1}/${operators.length} · CV RMSE ${formatMetric(aomPlsModel.score)}`;
    renderMethodResult("pls-default", rawPls, rawPlsStats, `${rawPls.components} comp. · CV ${formatMetric(rawPls.cvRmse)}`);
    renderMethodResult("pls-hpo", hpoPls, hpoPlsStats, `${hpoPls.operator.short} · ${hpoPls.components} comp. · CV ${formatMetric(hpoPls.cvRmse)}`);
    const aomBudgetNote = aomPlsFit.budget < componentBudget ? ` (stable limit; requested ${componentBudget})` : "";
    renderMethodResult("aom-pls", aomPls, aomPlsStats, `${selected.short} · H ≤ ${aomPlsFit.budget}${aomBudgetNote} · CV ${formatMetric(aomPlsModel.score)}`);
    renderMethodResult("ridge-default", rawRidge, rawRidgeStats, `α ${formatAlpha(rawRidge.alpha)} · CV ${formatMetric(rawRidge.cvRmse)}`);
    renderMethodResult("ridge-hpo", hpoRidge, hpoRidgeStats, `${hpoRidge.operator.short} · α ${formatAlpha(hpoRidge.alpha)} · CV ${formatMetric(hpoRidge.cvRmse)}`);
    renderMethodResult("aom-ridge", aomRidge, aomRidgeStats, `compact 12-chain blend · ${RIDGE_ALPHAS.length} α`);

    setComparisonBanner("rmse-delta", "delta-detail", aomPlsStats, hpoPlsStats, "PLS");
    setComparisonBanner("ridge-rmse-delta", "ridge-delta-detail", aomRidgeStats, hpoRidgeStats, "Ridge");
    const namedResults = [
      { name: "raw PLS", stats: rawPlsStats }, { name: "PLS-HPO", stats: hpoPlsStats }, { name: "AOM-PLS", stats: aomPlsStats },
      { name: "raw Ridge", stats: rawRidgeStats }, { name: "Ridge-HPO", stats: hpoRidgeStats }, { name: "AOM-Ridge", stats: aomRidgeStats },
    ];
    const best = [...namedResults].sort((left, right) => left.stats.rmse - right.stats.rmse)[0];
    byId("result-summary").textContent = `On these ${currentData.testRows} held-out rows, ${best.name} has the lowest RMSE (${formatMetric(best.stats.rmse)}). This is one local result; the paper-context panel below reports the 32-dataset evidence.`;
    byId("operator-preview-title").textContent = `Raw vs ${selected.name.toLowerCase()}`;
    const edgeNote = selected.kind === 8 || selected.kind === 9 || selected.kind === 15
      ? " Boundary transients are clipped only in this preview; fitting uses the complete transformed matrix."
      : "";
    byId("operator-explanation").textContent = `${selected.detail} The two panels use independent y scales so shape changes remain legible.${edgeNote}`;
    byId("fairness-text").textContent = `${currentData.trainRows} calibration · ${currentData.testRows} held out · ${foldCount} folds · PLS H 1–${componentBudget} · Ridge ${RIDGE_ALPHAS.length}-α grid`;

    drawRmseChart([
      { rmse: rawPlsStats.rmse }, { rmse: hpoPlsStats.rmse }, { rmse: aomPlsStats.rmse },
      { rmse: rawRidgeStats.rmse }, { rmse: hpoRidgeStats.rmse }, { rmse: aomRidgeStats.rmse },
    ]);
    drawPredictionChart("pls-prediction-chart", currentData.testY, [
      { predictions: rawPls.predictions, className: "baseline" },
      { predictions: hpoPls.predictions, className: "hpo" },
      { predictions: aomPls.predictions, className: "aom" },
    ]);
    drawPredictionChart("ridge-prediction-chart", currentData.testY, [
      { predictions: rawRidge.predictions, className: "baseline" },
      { predictions: hpoRidge.predictions, className: "hpo" },
      { predictions: aomRidge.predictions, className: "aom" },
    ]);
    drawOperatorChart(currentData, selected);
    drawCoefficientChart(currentData, rawPls.model.coefficients, aomPlsModel.coefficients);
    byId("run-note").textContent = `Complete: ${currentData.meta.label}; all metrics use the untouched validation partition.`;
    byId("run-note").className = "form-status success";
    setActivity({
      state: "complete", progress: 100, phase: "results",
      title: "Comparison complete",
      detail: `Six routes complete · best local RMSE ${formatMetric(best.stats.rmse)} (${best.name}) · ${currentData.testRows} held-out rows.`,
    });

    if (new URLSearchParams(location.search).has("selftest")) {
      document.documentElement.dataset.selftest = parserSelfTest()
        && namedResults.every((item) => Number.isFinite(item.stats.rmse))
        && byId("rmse-chart").children.length > 10
        && byId("ridge-prediction-chart").children.length > 10 ? "pass" : "fail";
      document.documentElement.dataset.selftestViewport = `${window.innerWidth}/${document.documentElement.scrollWidth}`;
    }
  } catch (error) {
    console.error(error);
    const failedStage = byId("run-note").textContent;
    byId("run-note").textContent = `Fit failed during “${failedStage}”: ${error.message}`;
    byId("run-note").className = "form-status error";
    setActivity({ state: "error", progress: 0, phase: "results", title: "Comparison failed", detail: `${failedStage} ${error.message}` });
    if (new URLSearchParams(location.search).has("selftest")) document.documentElement.dataset.selftest = "fail";
  } finally {
    setControlsLocked(false);
    button.disabled = false;
    button.querySelector("span").textContent = "Run PLS and Ridge comparison";
  }
}

async function loadUploadedFiles() {
  const status = byId("upload-status");
  const inputs = ["x-cal-file", "y-cal-file", "x-val-file", "y-val-file"].map((id) => byId(id));
  if (inputs.some((input) => !input.files[0])) {
    status.textContent = "Choose all four files: Xcal, Ycal, Xval and Yval.";
    status.className = "form-status error";
    return;
  }
  status.textContent = "Reading and validating locally…";
  status.className = "form-status";
  setActivity({ state: "loading", progress: 8, phase: "data", title: "Validating local files", detail: "Reading X/y calibration and validation files in this browser…" });
  try {
    const texts = await Promise.all(inputs.map((input) => input.files[0].text()));
    setActivity({ state: "loading", progress: 15, phase: "data", title: "Parsing local dataset", detail: "Checking delimiters, numeric values, dimensions and feature headers…" });
    await yieldToBrowser();
    const hasHeader = byId("upload-header").checked;
    const trainX = parseXText(texts[0], { hasHeader });
    const trainY = parseYText(texts[1]);
    const testX = parseXText(texts[2], { hasHeader });
    const testY = parseYText(texts[3]);
    validatePartitions(trainX, trainY, testX, testY);
    activeDatasetId = null;
    renderDatasetOptions();
    currentData = {
      trainX, trainY: trainY.data, testX, testY: testY.data,
      trainRows: trainX.rows, testRows: testX.rows, cols: trainX.cols, axis: trainX.axis,
      meta: {
        label: inputs[0].files[0].name.replace(/\.[^.]+$/, "") || "Uploaded dataset",
        kind: "Local upload",
        unit: byId("upload-unit").value,
        signalType: byId("upload-signal").value,
        targetName: trainY.targetName,
        description: "User-provided calibration and validation files parsed in this browser using the nirs4all separate-X/y convention.",
        provenance: `Local files ${inputs.map((input) => input.files[0].name).join(", ")}; no bytes were uploaded.`,
        sourceUrl: null,
      },
    };
    setDatasetUi(currentData);
    status.textContent = `Accepted ${trainX.rows} calibration and ${testX.rows} validation rows with ${trainX.cols} shared features. Review the plots, then click Compare.`;
    status.className = "form-status success";
    byId("run-note").textContent = "Local dataset ready. Review the settings, then run all six routes.";
    byId("run-note").className = "form-status success";
    setActivity({
      state: "ready", progress: 25, phase: "pls",
      title: "Local dataset ready",
      detail: `${trainX.rows} calibration rows, ${testX.rows} validation rows and ${trainX.cols} features. Run the PLS and Ridge comparison when ready.`,
    });
  } catch (error) {
    console.error(error);
    status.textContent = error.message;
    status.className = "form-status error";
    setActivity({ state: "error", progress: 8, phase: "data", title: "Local dataset rejected", detail: error.message });
  }
}

function parserSelfTest() {
  try {
    const xCal = parseXText("1100;1105;1110\n1;2;3\n2;3;4\n3;4;5\n4;5;6", { hasHeader: true });
    const yCal = parseYText("target\n1\n2\n3\n4");
    const xVal = parseXText("1100,1105,1110\n5,6,7", { hasHeader: true });
    const yVal = parseYText("target\n5");
    validatePartitions(xCal, yCal, xVal, yVal);
    return xCal.rows === 4 && xCal.cols === 3 && yCal.data[3] === 4;
  } catch (error) {
    console.error("Parser self-test failed", error);
    return false;
  }
}

async function initialise() {
  renderOperatorControls();
  setupCodeWorkbench();
  resetResults();
  setActivity({ state: "loading", progress: 4, phase: "data", title: "Initialising the demonstration", detail: "Loading the bundled dataset catalogue…" });
  byId("run").addEventListener("click", runComparison);
  byId("load-upload").addEventListener("click", loadUploadedFiles);
  byId("components").addEventListener("change", markResultsStale);
  byId("folds").addEventListener("change", markResultsStale);
  ["x-cal-file", "y-cal-file", "x-val-file", "y-val-file"].forEach((id) => byId(id).addEventListener("change", updateUploadReadiness));
  updateUploadReadiness();

  const manifestResponse = await fetch("datasets/manifest.json");
  if (!manifestResponse.ok) throw new Error(`Dataset manifest failed to load (${manifestResponse.status}).`);
  manifest = await manifestResponse.json();
  const requestedDataset = new URLSearchParams(location.search).get("dataset");
  activeDatasetId = manifest.datasets.some((dataset) => dataset.id === requestedDataset)
    ? requestedDataset
    : manifest.datasets[0].id;
  renderDatasetOptions();
  await loadBundledDataset(activeDatasetId, false, false);
  if (!currentData) throw new Error("The initial dataset is unavailable.");

  try {
    setActivity({ state: "loading", progress: 20, phase: "data", title: "Loading the numerical engine", detail: "Starting n4m WebAssembly; fitting remains local to this tab…" });
    await loadModule();
    runtimeReady = true;
    const abi = abiVersion().join(".");
    byId("runtime-status").textContent = "WebAssembly ready";
    byId("runtime-version").textContent = `n4m ${version()} · ABI ${abi}`;
    byId("runtime-dot").classList.replace("loading", "ready");
    byId("run").disabled = false;
    setActivity({ state: "ready", progress: 25, phase: "pls", title: "Ready to compare", detail: `${currentData.meta.label} and the WebAssembly engine are ready. Review the settings, then run the PLS and Ridge comparison.` });
  } catch (error) {
    console.error(error);
    byId("runtime-status").textContent = "WASM failed";
    byId("runtime-version").textContent = location.protocol === "file:" ? "Serve over HTTP" : error.message;
    byId("runtime-dot").classList.replace("loading", "error");
    byId("run-note").textContent = location.protocol === "file:"
      ? "Serve this directory over HTTP; browsers block WASM and CSV fetches from file://."
      : `WebAssembly failed to load: ${error.message}`;
    byId("run-note").className = "form-status error";
    setActivity({ state: "error", progress: 20, phase: "data", title: "WebAssembly could not start", detail: error.message });
  }
  if (runtimeReady && currentData && new URLSearchParams(location.search).has("selftest")) await runComparison();
}

window.__AOM_DEMO__ = { parseXText, parseYText, validatePartitions, parserSelfTest };

initialise().catch((error) => {
  console.error(error);
  byId("runtime-status").textContent = "Demo failed";
  byId("runtime-version").textContent = error.message;
  byId("runtime-dot").classList.replace("loading", "error");
  setActivity({ state: "error", progress: 0, phase: "data", title: "Demonstration could not start", detail: error.message });
  if (new URLSearchParams(location.search).has("selftest")) document.documentElement.dataset.selftest = "fail";
});
