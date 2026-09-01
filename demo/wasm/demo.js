import {
  abiVersion,
  fitAom,
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

const PHASES = ["data", "baseline", "aom", "results"];

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
  ["pls-rmse", "aom-rmse", "pls-mae", "aom-mae", "pls-r2", "aom-r2", "pls-cv", "aom-cv", "pls-time", "aom-time", "rmse-change", "mae-change", "r2-change", "selection-note", "time-change"].forEach((id) => { byId(id).textContent = "—"; });
  byId("operator").textContent = "—";
  byId("operator-detail").textContent = "The selected operator will appear here.";
  byId("rmse-delta").textContent = "—";
  byId("rmse-delta").className = "";
  byId("delta-detail").textContent = "relative RMSE versus raw PLS";
  byId("result-summary").textContent = "Run the comparison to populate the operator audit, performance table and diagnostic plots.";
  byId("operator-preview-title").textContent = "Raw vs selected operator view";
  byId("operator-explanation").textContent = "AOM will select one operator from the configured bank.";
  plotPlaceholder("prediction-chart", "Awaiting a fitted comparison");
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
    byId("run-note").textContent = `${dataset.label} is ready. Review the settings, then compare both approaches.`;
    byId("run-note").className = "form-status success";
    if (announceReady) {
      setActivity({
        state: "ready", progress: 25, phase: "baseline",
        title: "Dataset ready",
        detail: `${dataset.label}: ${trainX.rows} calibration rows, ${testX.rows} validation rows and ${trainX.cols} features. Click Compare to run both methods.`,
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
        setActivity({ state: "error", progress: 25, phase: "aom", title: "AOM bank cannot be empty", detail: "Keep at least one spectral operator selected." });
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
    state: "ready", progress: 25, phase: "baseline",
    title: "Configuration ready",
    detail: "Settings changed. Click Compare raw PLS and AOM-PLS to calculate new results.",
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
    for (const heldRows of folds) {
      const held = new Set(heldRows);
      const fitRows = allRows.filter((row) => !held.has(row));
      const xFit = selectRows(data.trainX.data, fitRows, data.cols);
      const yFit = selectRows(data.trainY, fitRows, 1);
      const xHeld = selectRows(data.trainX.data, heldRows, data.cols);
      const fitStarted = performance.now();
      const model = fitPls(matrix(xFit, fitRows.length, data.cols), matrix(yFit, fitRows.length, 1), components);
      const predictions = predictPls(model, matrix(xHeld, heldRows.length, data.cols)).data;
      elapsed += performance.now() - fitStarted;
      heldRows.forEach((row, index) => { oof[row] = predictions[index]; });
      completedFits += 1;
      onProgress?.(completedFits / totalFits, components, maxAllowed);
    }
    candidates.push({ components, rmse: metrics(data.trainY, oof).rmse });
    await yieldToBrowser();
  }
  candidates.sort((left, right) => left.rmse - right.rmse || left.components - right.components);
  const selected = candidates[0];
  const finalFitStarted = performance.now();
  const model = fitPls(matrix(data.trainX.data, data.trainRows, data.cols), matrix(data.trainY, data.trainRows, 1), selected.components);
  completedFits += 1;
  onProgress?.(completedFits / totalFits, selected.components, maxAllowed);
  const predictions = predictPls(model, matrix(data.testX.data, data.testRows, data.cols)).data;
  elapsed += performance.now() - finalFitStarted;
  return { model, predictions, components: selected.components, cvRmse: selected.rmse, elapsed, maxAllowed };
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

function drawPredictionChart(actual, aom, pls) {
  const svg = byId("prediction-chart");
  svg.replaceChildren();
  const width = 700;
  const height = 420;
  const margin = { left: 62, right: 20, top: 22, bottom: 54 };
  const [min, max] = paddedExtent([...actual, ...aom, ...pls], .08);
  const axis = Float64Array.from({ length: 101 }, (_, index) => min + index * (max - min) / 100);
  const scales = addAxes(svg, { width, height, margin, axis, yMin: min, yMax: max, xLabel: "Measured response", yLabel: "Predicted response", xTicks: 4, yTicks: 4 });
  const xValue = (value) => margin.left + (value - min) / (max - min) * (width - margin.left - margin.right);
  svg.append(svgElement("line", { x1: xValue(min), y1: scales.y(min), x2: xValue(max), y2: scales.y(max), class: "identity-line" }));
  pls.forEach((value, index) => svg.append(svgElement("circle", { cx: xValue(actual[index]), cy: scales.y(value), r: 5.2, class: "prediction-point pls" })));
  aom.forEach((value, index) => svg.append(svgElement("circle", { cx: xValue(actual[index]), cy: scales.y(value), r: 4.6, class: "prediction-point aom" })));
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

async function runComparison() {
  if (!runtimeReady || !currentData) return;
  const serial = ++comparisonSerial;
  const button = byId("run");
  const operators = selectedOperators();
  resetResults();
  setControlsLocked(true);
  button.disabled = true;
  button.querySelector("span").textContent = "Comparison in progress…";
  byId("run-note").textContent = "Step 1/2: selecting the raw PLS component count by calibration CV.";
  byId("run-note").className = "form-status";
  setActivity({
    state: "running", progress: 26, phase: "baseline",
    title: "Running raw PLS",
    detail: "Cross-validating component counts on calibration rows…",
  });
  await yieldToBrowser();

  try {
    const requestedComponents = Number(byId("components").value);
    const foldCount = Math.max(2, Math.min(Number(byId("folds").value), currentData.trainRows));
    const minFoldTrain = currentData.trainRows - Math.ceil(currentData.trainRows / foldCount);
    const componentBudget = Math.max(1, Math.min(requestedComponents, currentData.cols, minFoldTrain - 1));
    const baseline = await fitCrossValidatedPls(currentData, componentBudget, foldCount, (fraction, component, total) => {
      setActivity({
        state: "running", progress: 26 + fraction * 32, phase: "baseline",
        title: "Running raw PLS",
        detail: `Calibration CV: component ${component}/${total}, ${foldCount} folds.`,
      });
    });

    byId("run-note").textContent = `Step 2/2: AOM-PLS is screening ${operators.length} operators with the same ${foldCount} folds.`;
    setActivity({
      state: "running", progress: 62, phase: "aom",
      title: "Running AOM-PLS",
      detail: `Screening ${operators.length} operators and up to ${componentBudget} components on calibration rows…`,
    });
    await yieldToBrowser();
    const aomStarted = performance.now();
    const aomModel = fitAom(
      matrix(currentData.trainX.data, currentData.trainRows, currentData.cols),
      matrix(currentData.trainY, currentData.trainRows, 1),
      componentBudget,
      foldCount,
      0,
      operators.map((operator) => operator.kind),
    );
    const aomPredictions = predictModel(aomModel, matrix(currentData.testX.data, currentData.testRows, currentData.cols)).data;
    const aomElapsed = performance.now() - aomStarted;
    if (serial !== comparisonSerial) return;

    setActivity({
      state: "running", progress: 88, phase: "results",
      title: "Calculating held-out results",
      detail: `Comparing both prediction vectors on ${currentData.testRows} untouched validation rows…`,
    });
    await yieldToBrowser();

    const plsStats = metrics(currentData.testY, baseline.predictions);
    const aomStats = metrics(currentData.testY, aomPredictions);
    const selected = operators[aomModel.selectedOperator] || { name: `Bank entry ${aomModel.selectedOperator}`, short: "custom", detail: "Selected entry in the configured operator bank.", kind: operators[0].kind };
    const rmseDelta = signedPercent(aomStats.rmse, plsStats.rmse, true);
    const maeDelta = signedPercent(aomStats.mae, plsStats.mae, true);
    const r2Delta = { text: `${aomStats.r2 - plsStats.r2 >= 0 ? "+" : ""}${(aomStats.r2 - plsStats.r2).toFixed(3)}`, improvement: aomStats.r2 - plsStats.r2 };

    byId("operator").textContent = selected.name;
    byId("operator-detail").textContent = `${selected.short} · bank entry ${aomModel.selectedOperator + 1}/${operators.length}`;
    byId("pls-rmse").textContent = formatMetric(plsStats.rmse);
    byId("aom-rmse").textContent = formatMetric(aomStats.rmse);
    byId("pls-mae").textContent = formatMetric(plsStats.mae);
    byId("aom-mae").textContent = formatMetric(aomStats.mae);
    byId("pls-r2").textContent = formatMetric(plsStats.r2);
    byId("aom-r2").textContent = formatMetric(aomStats.r2);
    byId("pls-cv").textContent = `${formatMetric(baseline.cvRmse)} · ${baseline.components} comp.`;
    byId("aom-cv").textContent = `${formatMetric(aomModel.score)} · operator + comp.`;
    byId("selection-note").textContent = `budget 1–${componentBudget}`;
    byId("pls-time").textContent = formatTime(baseline.elapsed);
    byId("aom-time").textContent = formatTime(aomElapsed);
    byId("time-change").textContent = `${(aomElapsed / Math.max(baseline.elapsed, .001)).toFixed(1)}× PLS route`;
    setDeltaCell("rmse-change", rmseDelta);
    setDeltaCell("mae-change", maeDelta);
    setDeltaCell("r2-change", r2Delta);

    const banner = byId("rmse-delta");
    banner.className = classForImprovement(rmseDelta.improvement);
    if (Math.abs(rmseDelta.raw) < .05) {
      banner.textContent = "no material change";
    } else {
      banner.textContent = `${Math.abs(rmseDelta.raw).toFixed(1)}% ${rmseDelta.raw < 0 ? "lower" : "higher"} RMSE`;
    }
    byId("delta-detail").textContent = `AOM ${formatMetric(aomStats.rmse)} vs raw PLS ${formatMetric(plsStats.rmse)} on ${currentData.testRows} rows`;
    byId("result-summary").textContent = `Validation set (${currentData.testRows} rows): raw PLS RMSE ${formatMetric(plsStats.rmse)}; AOM-PLS RMSE ${formatMetric(aomStats.rmse)}. AOM selected ${selected.name.toLowerCase()}.`;
    byId("operator-preview-title").textContent = `Raw vs ${selected.name.toLowerCase()}`;
    const edgeNote = selected.kind === 8 || selected.kind === 9 || selected.kind === 15
      ? " Boundary transients are clipped only in this preview; fitting uses the complete transformed matrix."
      : "";
    byId("operator-explanation").textContent = `${selected.detail} The two panels use independent y scales so shape changes remain legible.${edgeNote}`;
    byId("fairness-text").textContent = `${currentData.trainRows} calibration · ${currentData.testRows} held out · ${foldCount} folds · component budget 1–${componentBudget}`;

    drawPredictionChart(currentData.testY, aomPredictions, baseline.predictions);
    drawOperatorChart(currentData, selected);
    drawCoefficientChart(currentData, baseline.model.coefficients, aomModel.coefficients);
    byId("run-note").textContent = `Complete: ${currentData.meta.label}; all metrics use the untouched validation partition.`;
    byId("run-note").className = "form-status success";
    setActivity({
      state: "complete", progress: 100, phase: "results",
      title: "Comparison complete",
      detail: `Raw PLS RMSE ${formatMetric(plsStats.rmse)} · AOM-PLS RMSE ${formatMetric(aomStats.rmse)} · ${selected.name}.`,
    });

    if (new URLSearchParams(location.search).has("selftest")) {
      document.documentElement.dataset.selftest = parserSelfTest() && Number.isFinite(aomStats.rmse) && byId("prediction-chart").children.length > 10 ? "pass" : "fail";
      document.documentElement.dataset.selftestViewport = `${window.innerWidth}/${document.documentElement.scrollWidth}`;
    }
  } catch (error) {
    console.error(error);
    byId("run-note").textContent = `Fit failed: ${error.message}`;
    byId("run-note").className = "form-status error";
    setActivity({ state: "error", progress: 0, phase: "results", title: "Comparison failed", detail: error.message });
    if (new URLSearchParams(location.search).has("selftest")) document.documentElement.dataset.selftest = "fail";
  } finally {
    setControlsLocked(false);
    button.disabled = false;
    button.querySelector("span").textContent = "Compare raw PLS and AOM-PLS";
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
    byId("run-note").textContent = "Local dataset ready. Review the settings, then compare both approaches.";
    byId("run-note").className = "form-status success";
    setActivity({
      state: "ready", progress: 25, phase: "baseline",
      title: "Local dataset ready",
      detail: `${trainX.rows} calibration rows, ${testX.rows} validation rows and ${trainX.cols} features. Click Compare to run both methods.`,
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
    setActivity({ state: "ready", progress: 25, phase: "baseline", title: "Ready to compare", detail: `${currentData.meta.label} and the WebAssembly engine are ready. Review the settings, then click Compare.` });
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
