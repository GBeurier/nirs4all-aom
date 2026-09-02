import {
  abiVersion,
  fitAomChain,
  fitModel,
  loadModule,
  ppCreate,
  ppDestroy,
  ppTransform,
  predictModel,
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
  { id: "raw", kind: 0, params: [], steps: [], name: "Identity", short: "raw X", detail: "No spectral transformation; the raw view is always included." },
  { id: "detrend-1", kind: 7, params: [1], steps: [{ op: "Detrend", params: [1] }], name: "Linear detrending", short: "detrend · degree 1", detail: "Subtracts a least-squares linear baseline." },
  { id: "detrend-2", kind: 7, params: [2], steps: [{ op: "Detrend", params: [2] }], name: "Quadratic detrending", short: "detrend · degree 2", detail: "Subtracts a least-squares quadratic baseline." },
  { id: "sg-s7", kind: 8, params: [7, 2], steps: [{ op: "SavitzkyGolay", params: [7, 2, 0, 1, 0] }], name: "Savitzky–Golay smoothing 7", short: "SG 7/2 · smoothing", detail: "Seven-point, second-degree Savitzky–Golay smoothing." },
  { id: "sg-s11", kind: 8, params: [11, 3], steps: [{ op: "SavitzkyGolay", params: [11, 3, 0, 1, 0] }], name: "Savitzky–Golay smoothing 11", short: "SG 11/3 · smoothing", detail: "Eleven-point, third-degree Savitzky–Golay smoothing." },
  { id: "sg-d1-7", kind: 9, params: [7, 2, 1], steps: [{ op: "SavitzkyGolay", params: [7, 2, 1, 1, 0] }], name: "Savitzky–Golay first derivative", short: "SG 7/2 · derivative 1", detail: "Seven-point first Savitzky–Golay derivative." },
  { id: "sg-d2-11", kind: 9, params: [11, 3, 2], steps: [{ op: "SavitzkyGolay", params: [11, 3, 2, 1, 0] }], name: "Savitzky–Golay second derivative", short: "SG 11/3 · derivative 2", detail: "Eleven-point second Savitzky–Golay derivative." },
  { id: "diff-1", kind: 15, params: [1], steps: [{ op: "Derivative", params: [1] }], name: "Finite difference", short: "finite difference · order 1", detail: "Centered first finite difference." },
  { id: "gaussian-1", kind: 18, params: [1], steps: [{ op: "GaussianFilter", params: [1] }], name: "Gaussian smoothing σ1", short: "Gaussian · σ1", detail: "Gaussian smoothing with σ = 1." },
  { id: "gaussian-2", kind: 18, params: [2], steps: [{ op: "GaussianFilter", params: [2] }], name: "Gaussian smoothing σ2", short: "Gaussian · σ2", detail: "Gaussian smoothing with σ = 2." },
];

const pipeline = (id, name, short, steps = []) => ({ id, name, short, steps });
const IDENTITY_OPERATOR = OPERATORS.find((item) => item.id === "raw");

const byId = (id) => document.getElementById(id);
let manifest = null;
let currentData = null;
let activeDatasetId = null;
let runtimeReady = false;
let comparisonSerial = 0;
let loadingDatasetId = null;
let activityRunStarted = null;
let lastActivityProgress = 0;
let lastActivityAnnouncement = "";
let lastOperatorChart = null;
let operatorResizeTimer = null;
let datasetSourceMode = "bundled";
let controlsLocked = false;

const PHASES = ["data", "pls", "aom-pls", "ridge", "aom-ridge", "results"];
const RIDGE_ALPHAS = [1e-8, 1e-6, 1e-4, 1e-2, 1, 1e2, 1e4];

function setActivity({ state, progress, title, detail, phase = null }) {
  const container = byId("activity");
  const previousState = container.dataset.state;
  if (state === "running" && previousState !== "running") {
    activityRunStarted = performance.now();
    lastActivityProgress = 0;
  }
  let boundedProgress = Math.max(0, Math.min(100, Number(progress)));
  if (state === "running") boundedProgress = Math.max(lastActivityProgress, boundedProgress);
  lastActivityProgress = boundedProgress;
  const roundedProgress = Math.round(boundedProgress);
  container.dataset.state = state;
  byId("activity-title").textContent = title;
  byId("activity-detail").textContent = detail;
  byId("activity-progress-bar").style.width = `${boundedProgress.toFixed(2)}%`;
  byId("activity-progress").setAttribute("aria-valuenow", String(roundedProgress));
  byId("activity-percent").textContent = `${roundedProgress}%`;
  if (state === "running" && activityRunStarted !== null) {
    const elapsedSeconds = (performance.now() - activityRunStarted) / 1000;
    const computeFraction = Math.max(0, Math.min(1, (boundedProgress - 25) / 75));
    const etaSeconds = elapsedSeconds >= 3 && computeFraction >= .1
      ? elapsedSeconds * (1 - computeFraction) / computeFraction
      : null;
    byId("activity-time").textContent = etaSeconds === null
      ? `${elapsedSeconds.toFixed(0)} s elapsed · estimating…`
      : `${elapsedSeconds.toFixed(0)} s elapsed · about ${Math.max(0, Math.round(etaSeconds))} s left`;
  } else if (state === "complete" && activityRunStarted !== null) {
    byId("activity-time").textContent = `Completed in ${((performance.now() - activityRunStarted) / 1000).toFixed(1)} s`;
  } else {
    byId("activity-time").textContent = state === "loading" ? "Loading…" : state === "error" ? "Stopped" : "Ready";
  }
  const announcement = `${state}: ${title}`;
  if (announcement !== lastActivityAnnouncement) {
    byId("activity-announcement").textContent = `${title}. ${detail}`;
    lastActivityAnnouncement = announcement;
  }
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

function updateFilePickerName(input) {
  const name = byId(`${input.id}-name`);
  if (name) name.textContent = input.files?.[0]?.name || "No file selected";
}

function updateUploadReadiness() {
  const inputs = ["x-cal-file", "y-cal-file", "x-val-file", "y-val-file"].map((id) => byId(id));
  const selected = inputs.filter((input) => input.files?.[0]).length;
  const button = byId("load-upload");
  inputs.forEach(updateFilePickerName);
  button.disabled = controlsLocked || datasetSourceMode !== "upload" || selected !== inputs.length;
  const status = byId("upload-status");
  status.className = "form-status";
  status.textContent = selected === inputs.length
    ? "Four files selected. Validate them to inspect the dataset; nothing will be uploaded."
    : `${selected}/4 files selected. Add calibration X/y and validation X/y.${datasetSourceMode === "upload" ? "" : " Select ‘Load your X and y files’ to begin."}`;
}

function syncSourceControls() {
  const uploadSelected = datasetSourceMode === "upload";
  byId("source-upload").checked = uploadSelected;
  byId("source-bundled").checked = !uploadSelected;
  byId("source-upload").disabled = controlsLocked;
  byId("source-bundled").disabled = controlsLocked;
  document.querySelectorAll(".source-card").forEach((card) => {
    card.dataset.selected = String(card.dataset.source === datasetSourceMode);
  });
  document.querySelectorAll(".upload-card input:not([name='dataset-source']), .upload-card select")
    .forEach((control) => { control.disabled = controlsLocked || !uploadSelected; });
  document.querySelectorAll(".upload-grid .file-picker")
    .forEach((picker) => picker.setAttribute("aria-disabled", String(controlsLocked || !uploadSelected)));
  document.querySelectorAll(".dataset-option")
    .forEach((control) => { control.disabled = controlsLocked || uploadSelected; });
  updateUploadReadiness();
}

function setDatasetSourceMode(mode, markStale = false) {
  if (!["upload", "bundled"].includes(mode)) throw new Error(`Unknown dataset source: ${mode}`);
  if (datasetSourceMode !== mode && markStale) markResultsStale();
  datasetSourceMode = mode;
  syncSourceControls();
}

function setControlsLocked(locked) {
  controlsLocked = locked;
  document.querySelectorAll("#search-depth, #components, #folds, #preprocessing-order")
    .forEach((control) => { control.disabled = locked; });
  document.querySelectorAll("#operator-controls input")
    .forEach((control) => { control.disabled = locked || control.value === IDENTITY_OPERATOR.id; });
  syncSourceControls();
}

function selectedSearchProfile() {
  const id = byId("search-depth").value === "quick" ? "quick" : "full";
  return { id, label: id === "quick" ? "Quick check" : "Full comparison", pipelines: buildSharedPipelines() };
}

function updateSearchDepthUi(markStale = true) {
  const profile = selectedSearchProfile();
  const full = profile.id === "full";
  byId("search-depth-note").textContent = full
    ? `${profile.pipelines.length} shared chains · complete component and Ridge α grids · device-dependent runtime.`
    : `${profile.pipelines.length} shared chains · reduced model grids for a faster interface check.`;
  const bankWarning = profile.pipelines.length > 60 ? " Large bank: expect a longer browser run." : "";
  byId("shared-bank-summary").textContent = `${profile.pipelines.length} shared chains, from raw identity up to order ${byId("preprocessing-order").value}. HPO and AOM search them in the same listed order.${bankWarning}`;
  byId("run-search-summary").textContent = full ? "full shared-bank comparison" : "quick shared-bank check";
  if (markStale) markResultsStale();
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
  const addPartition = (buffer, rows, color, limit, partition) => {
    const step = Math.max(1, Math.ceil(rows / limit));
    for (let row = 0; row < rows; row += step) {
      const values = buffer.subarray(row * data.cols, (row + 1) * data.cols);
      svg.append(svgElement("path", { d: pathFromValues(values, scales.x, scales.y), class: `plot-line sample ${partition}`, stroke: color }));
    }
    const mean = meanRows(buffer, rows, data.cols);
    svg.append(svgElement("path", { d: pathFromValues(mean, scales.x, scales.y), class: `plot-line mean n4viz-line-mean ${partition}`, stroke: color }));
  };
  addPartition(data.trainX.data, data.trainRows, COLORS.train, 28, "train");
  addPartition(data.testX.data, data.testRows, COLORS.test, 14, "test");
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
      result[Math.max(0, Math.min(bins - 1, raw))] += 100 / values.length;
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
  addText(svg, "within-split (%)", { x: 14, y: height / 2, class: "n4viz-axis-label", transform: `rotate(-90 14 ${height / 2})`, "text-anchor": "middle" });
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
  lastOperatorChart = null;
  [
    "pls-default-selection", "pls-default-rmse", "pls-default-mae", "pls-default-r2", "pls-default-time", "pls-default-workload",
    "pls-hpo-selection", "pls-hpo-rmse", "pls-hpo-mae", "pls-hpo-r2", "pls-hpo-time", "pls-hpo-workload",
    "aom-pls-selection", "aom-pls-rmse", "aom-pls-mae", "aom-pls-r2", "aom-pls-time", "aom-pls-workload",
    "ridge-default-selection", "ridge-default-rmse", "ridge-default-mae", "ridge-default-r2", "ridge-default-time", "ridge-default-workload",
    "ridge-hpo-selection", "ridge-hpo-rmse", "ridge-hpo-mae", "ridge-hpo-r2", "ridge-hpo-time", "ridge-hpo-workload",
    "aom-ridge-selection", "aom-ridge-rmse", "aom-ridge-mae", "aom-ridge-r2", "aom-ridge-time", "aom-ridge-workload",
  ].forEach((id) => { byId(id).textContent = "—"; });
  byId("pls-raw-card").textContent = "—";
  byId("pls-raw-card-detail").textContent = "The untuned raw baseline will appear here.";
  byId("pls-hpo-card").textContent = "—";
  byId("pls-hpo-card-detail").textContent = "The winning HPO pipeline will appear here.";
  byId("operator").textContent = "—";
  byId("operator-detail").textContent = "The AOM operator and component count will appear here.";
  byId("ridge-hpo-card").textContent = "—";
  byId("ridge-hpo-card-detail").textContent = "The winning HPO pipeline will appear here.";
  byId("ridge-raw-card").textContent = "—";
  byId("ridge-raw-card-detail").textContent = "The untuned raw baseline will appear here.";
  byId("ridge-aom-card").textContent = "—";
  byId("ridge-aom-card-detail").textContent = "The AOM-selected shared chain will appear here.";
  byId("rmse-delta").textContent = "Awaiting results";
  byId("rmse-delta").className = "";
  byId("delta-detail").textContent = "Run the experiment to compare Raw, HPO and AOM directly.";
  byId("ridge-rmse-delta").textContent = "Awaiting results";
  byId("ridge-rmse-delta").className = "";
  byId("ridge-delta-detail").textContent = "Run the experiment to compare Raw, HPO and AOM directly.";
  byId("hpo-search-summary").textContent = "Available after the experiment";
  byId("hpo-protocol-detail").textContent = "The shared fold plan and score definition will appear here.";
  byId("hpo-pls-detail").textContent = "Component grid and winning preprocessing pipeline.";
  byId("hpo-ridge-detail").textContent = "Alpha grid and winning preprocessing pipeline.";
  resetHpoScoreTable();
  byId("result-summary").textContent = "Run the comparison to populate six held-out results, selected settings and diagnostic plots.";
  byId("pretreatment-hpo-name").textContent = "Awaiting selection";
  byId("pretreatment-hpo-setting").textContent = "Pipeline, components and validation RMSE will appear here.";
  byId("pretreatment-aom-name").textContent = "Awaiting selection";
  byId("pretreatment-aom-setting").textContent = "Operator, components and validation RMSE will appear here.";
  byId("operator-preview-title").textContent = "Two routes, two selected spectral views";
  byId("operator-explanation").textContent = "The two comparisons will appear after fitting. Shapes are standardized only for this display; models use the complete transformed values.";
  byId("local-conclusion-title").textContent = "Run the comparison to obtain a local conclusion";
  byId("local-conclusion-copy").textContent = "The conclusion will distinguish the held-out result from the broader evidence reported in the paper.";
  byId("conclusion-pls").textContent = "Awaiting results";
  byId("conclusion-pls-detail").textContent = "Raw, HPO and AOM on held-out rows.";
  byId("conclusion-ridge").textContent = "Awaiting results";
  byId("conclusion-ridge-detail").textContent = "Raw, HPO and AOM on held-out rows.";
  plotPlaceholder("rmse-chart", "Awaiting six fitted routes", [0, 0, 1280, 420]);
  plotPlaceholder("pls-prediction-chart", "Awaiting the PLS comparison", [0, 0, 620, 420]);
  plotPlaceholder("ridge-prediction-chart", "Awaiting the Ridge comparison", [0, 0, 620, 420]);
  const operatorBox = window.innerWidth < 640 ? [0, 0, 640, 688] : [0, 0, 1280, 360];
  byId("operator-chart").setAttribute("viewBox", operatorBox.join(" "));
  plotPlaceholder("operator-chart", "Awaiting HPO and AOM selections", operatorBox);
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
    button.disabled = controlsLocked || datasetSourceMode !== "bundled";
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
  byId("fairness-text").textContent = `${data.trainRows} calibration rows · ${data.testRows} held-out rows · raw baseline always included`;
  drawSpectra(data);
  drawTargetHistogram(data);
  const [signalMin, signalMax] = extent([...data.trainX.data, ...data.testX.data]);
  const trainMean = data.trainY.reduce((sum, value) => sum + value, 0) / data.trainY.length;
  const testMean = data.testY.reduce((sum, value) => sum + value, 0) / data.testY.length;
  byId("spectra-summary").textContent = `${data.trainRows + data.testRows} spectra across ${data.cols} wavelengths; ${data.meta.signalType} spans ${compactNumber(signalMin)} to ${compactNumber(signalMax)}.`;
  byId("target-summary").textContent = `${data.meta.targetName}: ${compactNumber(targetMin)} to ${compactNumber(targetMax)}; calibration mean ${compactNumber(trainMean)}, validation mean ${compactNumber(testMean)}.`;
  resetResults();
}

async function loadBundledDataset(id, runAfterLoad = false, announceReady = true) {
  const dataset = manifest.datasets.find((item) => item.id === id);
  if (!dataset) throw new Error(`Unknown bundled dataset: ${id}`);
  setDatasetSourceMode("bundled");
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
        kind: "Bundled example",
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
  const selected = [...document.querySelectorAll("#operator-controls input:checked")]
    .map((input) => OPERATORS.find((operator) => operator.id === input.value))
    .filter(Boolean);
  if (!IDENTITY_OPERATOR) throw new Error("The AOM identity baseline is missing from the operator catalogue.");
  return [IDENTITY_OPERATOR, ...selected.filter((operator) => operator.id !== IDENTITY_OPERATOR.id)];
}

function combinations(items, size, start = 0, prefix = [], output = []) {
  if (prefix.length === size) {
    output.push(prefix);
    return output;
  }
  for (let index = start; index <= items.length - (size - prefix.length); index += 1) {
    combinations(items, size, index + 1, [...prefix, items[index]], output);
  }
  return output;
}

function buildSharedPipelines() {
  const active = selectedOperators().filter((operator) => operator.id !== "raw");
  const maxOrder = Math.max(1, Math.min(3, Number(byId("preprocessing-order").value)));
  const pipelines = [pipeline("raw", "Raw spectrum", "raw X")];
  for (let order = 1; order <= maxOrder; order += 1) {
    combinations(active, order).forEach((chain) => {
      pipelines.push(pipeline(
        chain.map((operator) => operator.id).join("__"),
        chain.map((operator) => operator.name).join(" → "),
        chain.map((operator) => operator.short).join(" → "),
        chain.flatMap((operator) => operator.steps),
      ));
      pipelines[pipelines.length - 1].operators = chain;
    });
  }
  return pipelines;
}

function nativeChainDescriptor(pipelines) {
  const chainOffsets = [0];
  const operatorKinds = [];
  const parameterOffsets = [0];
  const parameters = [];
  pipelines.forEach((selectedPipeline) => {
    const chain = selectedPipeline.id === "raw" ? [IDENTITY_OPERATOR] : selectedPipeline.operators;
    chain.forEach((operator) => {
      operatorKinds.push(operator.kind);
      parameters.push(...operator.params);
      parameterOffsets.push(parameters.length);
    });
    chainOffsets.push(operatorKinds.length);
  });
  return { chainOffsets, operatorKinds, parameterOffsets, parameters };
}

function renderOperatorControls() {
  const container = byId("operator-controls");
  OPERATORS.forEach((operator) => {
    const label = document.createElement("label");
    label.className = "operator-check";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = operator.id;
    input.checked = true;
    input.disabled = operator.id === IDENTITY_OPERATOR.id;
    const name = document.createElement("span");
    name.textContent = operator.name;
    const detail = document.createElement("small");
    detail.textContent = operator.id === IDENTITY_OPERATOR.id ? `${operator.short} · required baseline` : operator.short;
    label.append(input, name, detail);
    container.append(label);
    input.addEventListener("change", () => {
      updateSearchDepthUi(true);
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
  const routeStarted = performance.now();
  const scored = await scorePlsCandidates(data, maxComponents, foldCount, onProgress);
  const candidates = [...scored.candidates];
  candidates.sort((left, right) => left.rmse - right.rmse || left.components - right.components);
  const selected = candidates[0];
  const model = fitModel(
    "PLS",
    matrix(data.trainX.data, data.trainRows, data.cols),
    matrix(data.trainY, data.trainRows, 1),
    selected.components,
  );
  const predictions = predictModel(model, matrix(data.testX.data, data.testRows, data.cols)).data;
  onProgress?.(1, selected.components, maxComponents);
  return {
    model,
    predictions,
    components: selected.components,
    cvRmse: selected.rmse,
    elapsed: performance.now() - routeStarted,
    maxAllowed: maxComponents,
    candidateFits: scored.candidateFits + 1,
  };
}

async function scorePlsCandidates(data, maxComponents, foldCount, onProgress) {
  const folds = contiguousFolds(data.trainRows, foldCount);
  const allRows = Array.from({ length: data.trainRows }, (_, index) => index);
  const candidates = [];
  const totalUnits = maxComponents * folds.length;
  let completedUnits = 0;
  let candidateFits = 0;
  onProgress?.(0, 0, maxComponents);
  for (let components = 1; components <= maxComponents; components += 1) {
    let squaredErrorSum = 0;
    let heldOutCount = 0;
    let validFolds = 0;
    let validCandidate = true;
    for (let foldIndex = 0; foldIndex < folds.length; foldIndex += 1) {
      const heldRows = folds[foldIndex];
      const held = new Set(heldRows);
      const fitRows = allRows.filter((row) => !held.has(row));
      const xFit = selectRows(data.trainX.data, fitRows, data.cols);
      const yFit = selectRows(data.trainY, fitRows, 1);
      const xHeld = selectRows(data.trainX.data, heldRows, data.cols);
      const yHeld = selectRows(data.trainY, heldRows, 1);
      try {
        const model = fitModel(
          "PLS",
          matrix(xFit, fitRows.length, data.cols),
          matrix(yFit, fitRows.length, 1),
          components,
        );
        const predictions = predictModel(model, matrix(xHeld, heldRows.length, data.cols)).data;
        candidateFits += 1;
        for (let index = 0; index < yHeld.length; index += 1) squaredErrorSum += (yHeld[index] - predictions[index]) ** 2;
        heldOutCount += yHeld.length;
        validFolds += 1;
      } catch (error) {
        validCandidate = false;
      }
      completedUnits += 1;
      if (!validCandidate) {
        completedUnits += folds.length - foldIndex - 1;
        break;
      }
      onProgress?.(completedUnits / totalUnits, components, maxComponents);
    }
    if (validCandidate && validFolds === folds.length) {
      candidates.push({ components, rmse: Math.sqrt(squaredErrorSum / heldOutCount) });
    }
    onProgress?.(completedUnits / totalUnits, components, maxComponents);
    await yieldToBrowser();
  }
  if (candidates.length === 0) throw new Error("No numerically stable PLS component count was found.");
  return { candidates, candidateFits };
}

function transformWithPipeline(buffer, rows, cols, selectedPipeline) {
  let transformed = buffer;
  for (const step of selectedPipeline.steps) {
    const operator = ppCreate(step.op, step.params);
    try {
      transformed = ppTransform(operator, transformed, rows, cols);
    } finally {
      ppDestroy(operator);
    }
  }
  return transformed;
}

function transformedDataset(data, selectedPipeline, includeValidation = true) {
  if (selectedPipeline.steps.length === 0) return data;
  return {
    ...data,
    trainX: matrix(transformWithPipeline(data.trainX.data, data.trainRows, data.cols, selectedPipeline), data.trainRows, data.cols),
    testX: includeValidation
      ? matrix(transformWithPipeline(data.testX.data, data.testRows, data.cols, selectedPipeline), data.testRows, data.cols)
      : data.testX,
  };
}

async function fitPreprocessingHpoPls(data, maxComponents, foldCount, pipelines, onProgress) {
  const routeStarted = performance.now();
  const candidates = [];
  let candidateFits = 0;
  for (let pipelineIndex = 0; pipelineIndex < pipelines.length; pipelineIndex += 1) {
    const selectedPipeline = pipelines[pipelineIndex];
    try {
      const transformed = transformedDataset(data, selectedPipeline, false);
      const scored = await scorePlsCandidates(transformed, maxComponents, foldCount, (fraction, component, total) => {
        const overall = (pipelineIndex + fraction) / pipelines.length;
        onProgress?.(overall, selectedPipeline, component, total);
      });
      candidateFits += scored.candidateFits;
      const pipelineCandidates = [...scored.candidates]
        .sort((left, right) => left.rmse - right.rmse || left.components - right.components);
      const best = pipelineCandidates[0];
      candidates.push({
        pipeline: selectedPipeline,
        pipelineIndex,
        components: best.components,
        cvRmse: best.rmse,
      });
    } catch (error) {
      onProgress?.((pipelineIndex + 1) / pipelines.length, selectedPipeline, maxComponents, maxComponents);
    }
  }
  if (candidates.length === 0) throw new Error("No numerically stable PLS preprocessing route was found.");
  const rawCandidate = [...candidates]
    .filter((candidate) => candidate.pipeline.id === "raw")
    .sort((left, right) => left.cvRmse - right.cvRmse || left.components - right.components)[0];
  const pipelineResults = [...candidates].sort((left, right) => left.pipelineIndex - right.pipelineIndex);
  candidates.sort((left, right) => left.cvRmse - right.cvRmse
    || left.components - right.components
    || left.pipelineIndex - right.pipelineIndex);
  const selected = candidates[0];
  const finalData = transformedDataset(data, selected.pipeline);
  const model = fitModel(
    "PLS",
    matrix(finalData.trainX.data, finalData.trainRows, finalData.cols),
    matrix(finalData.trainY, finalData.trainRows, 1),
    selected.components,
  );
  const predictions = predictModel(model, matrix(finalData.testX.data, finalData.testRows, finalData.cols)).data;
  return { model, predictions, components: selected.components, cvRmse: selected.cvRmse, operator: selected.pipeline, elapsed: performance.now() - routeStarted, candidateFits: candidateFits + 1, rawCandidate, pipelineResults };
}

async function scoreRidgeCandidates(data, foldCount, alphas, onProgress) {
  const folds = contiguousFolds(data.trainRows, foldCount);
  const allRows = Array.from({ length: data.trainRows }, (_, index) => index);
  const candidates = [];
  const totalUnits = alphas.length * folds.length;
  let completedUnits = 0;
  let candidateFits = 0;
  for (let alphaIndex = 0; alphaIndex < alphas.length; alphaIndex += 1) {
    const alpha = alphas[alphaIndex];
    let squaredErrorSum = 0;
    let heldOutCount = 0;
    let validFolds = 0;
    let validCandidate = true;
    for (let foldIndex = 0; foldIndex < folds.length; foldIndex += 1) {
      const heldRows = folds[foldIndex];
      const held = new Set(heldRows);
      const fitRows = allRows.filter((row) => !held.has(row));
      const xFit = selectRows(data.trainX.data, fitRows, data.cols);
      const yFit = selectRows(data.trainY, fitRows, 1);
      const xHeld = selectRows(data.trainX.data, heldRows, data.cols);
      const yHeld = selectRows(data.trainY, heldRows, 1);
      try {
        const model = fitModel("Ridge", matrix(xFit, fitRows.length, data.cols), matrix(yFit, fitRows.length, 1), 1, [alpha]);
        const predictions = predictModel(model, matrix(xHeld, heldRows.length, data.cols)).data;
        candidateFits += 1;
        for (let index = 0; index < yHeld.length; index += 1) squaredErrorSum += (yHeld[index] - predictions[index]) ** 2;
        heldOutCount += yHeld.length;
        validFolds += 1;
      } catch (error) {
        validCandidate = false;
      }
      completedUnits += 1;
      if (!validCandidate) {
        completedUnits += folds.length - foldIndex - 1;
        break;
      }
      onProgress?.(completedUnits / totalUnits, alpha, alphaIndex + 1, alphas.length);
    }
    if (validCandidate && validFolds === folds.length) {
      candidates.push({ alpha, rmse: Math.sqrt(squaredErrorSum / heldOutCount) });
    }
    onProgress?.(completedUnits / totalUnits, alpha, alphaIndex + 1, alphas.length);
    await yieldToBrowser();
  }
  if (candidates.length === 0) throw new Error("No numerically stable Ridge regularisation value was found.");
  return { candidates, candidateFits };
}

async function fitCrossValidatedRidge(data, foldCount, alphas, onProgress) {
  const routeStarted = performance.now();
  const scored = await scoreRidgeCandidates(data, foldCount, alphas, onProgress);
  const candidates = [...scored.candidates];
  candidates.sort((left, right) => left.rmse - right.rmse || left.alpha - right.alpha);
  const selected = candidates[0];
  const model = fitModel(
    "Ridge",
    matrix(data.trainX.data, data.trainRows, data.cols),
    matrix(data.trainY, data.trainRows, 1),
    1,
    [selected.alpha],
  );
  const predictions = predictModel(model, matrix(data.testX.data, data.testRows, data.cols)).data;
  onProgress?.(1, selected.alpha, alphas.length, alphas.length);
  return { model, predictions, alpha: selected.alpha, cvRmse: selected.rmse, elapsed: performance.now() - routeStarted, candidateFits: scored.candidateFits + 1 };
}

async function fitPreprocessingHpoRidge(data, foldCount, alphas, pipelines, onProgress) {
  const routeStarted = performance.now();
  const candidates = [];
  let candidateFits = 0;
  for (let pipelineIndex = 0; pipelineIndex < pipelines.length; pipelineIndex += 1) {
    const selectedPipeline = pipelines[pipelineIndex];
    try {
      const transformed = transformedDataset(data, selectedPipeline, false);
      const scored = await scoreRidgeCandidates(transformed, foldCount, alphas, (fraction, alpha, alphaIndex, alphaCount) => {
        const overall = (pipelineIndex + fraction) / pipelines.length;
        onProgress?.(overall, selectedPipeline, alpha, alphaIndex, alphaCount);
      });
      candidateFits += scored.candidateFits;
      scored.candidates.forEach(({ alpha, rmse }) => {
        candidates.push({ pipeline: selectedPipeline, pipelineIndex, alpha, cvRmse: rmse });
      });
    } catch (error) {
      onProgress?.((pipelineIndex + 1) / pipelines.length, selectedPipeline, alphas.at(-1), alphas.length, alphas.length);
    }
  }
  if (candidates.length === 0) throw new Error("No numerically stable Ridge preprocessing route was found.");
  const rawCandidate = [...candidates]
    .filter((candidate) => candidate.pipeline.id === "raw")
    .sort((left, right) => left.cvRmse - right.cvRmse || left.alpha - right.alpha)[0];
  const pipelineResults = pipelines.map((selectedPipeline) => [...candidates]
    .filter((candidate) => candidate.pipeline.id === selectedPipeline.id)
    .sort((left, right) => left.cvRmse - right.cvRmse || left.alpha - right.alpha)[0])
    .filter(Boolean);
  candidates.sort((left, right) => left.cvRmse - right.cvRmse
    || left.alpha - right.alpha
    || left.pipelineIndex - right.pipelineIndex);
  const selected = candidates[0];
  const finalData = transformedDataset(data, selected.pipeline);
  const model = fitModel("Ridge", matrix(finalData.trainX.data, finalData.trainRows, finalData.cols), matrix(finalData.trainY, finalData.trainRows, 1), 1, [selected.alpha]);
  const predictions = predictModel(model, matrix(finalData.testX.data, finalData.testRows, finalData.cols)).data;
  return { model, predictions, alpha: selected.alpha, cvRmse: selected.cvRmse, operator: selected.pipeline, elapsed: performance.now() - routeStarted, candidateFits: candidateFits + 1, rawCandidate, pipelineResults };
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

function protocolScoresMatch(left, right) {
  if (!Number.isFinite(left) || !Number.isFinite(right)) return false;
  const scale = Math.max(1, Math.abs(left), Math.abs(right));
  return Math.abs(left - right) <= scale * 1e-6;
}

function assertProtocolParity(condition, detail) {
  if (!condition) throw new Error(`Protocol parity failed: ${detail}`);
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
    item.predictions.forEach((value, index) => {
      const cx = xValue(actual[index]);
      const cy = scales.y(value);
      if (seriesIndex === 0) {
        svg.append(svgElement("circle", { cx, cy, r: 5, class: `prediction-point ${item.className}` }));
      } else if (seriesIndex === 1) {
        svg.append(svgElement("rect", { x: cx - 4.4, y: cy - 4.4, width: 8.8, height: 8.8, rx: 1, class: `prediction-point ${item.className}` }));
      } else {
        svg.append(svgElement("path", { d: `M${cx},${cy - 5} L${cx + 5},${cy} L${cx},${cy + 5} L${cx - 5},${cy} Z`, class: `prediction-point ${item.className}` }));
      }
    });
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

function pipelinePreviewTrim(selectedPipeline) {
  let trim = 0;
  for (const step of selectedPipeline.steps) {
    if (step.op === "SavitzkyGolay") trim = Math.max(trim, Math.floor((step.params[0] || 1) / 2));
    if (step.op === "Derivative") trim = Math.max(trim, Number(step.params[0]) || 1);
    if (step.op === "GaussianFilter") trim = Math.max(trim, Math.ceil(3 * (Number(step.params[0]) || 1)));
  }
  return trim;
}

function standardizedShape(values) {
  const mean = values.reduce((sum, value) => sum + value, 0) / Math.max(1, values.length);
  const variance = values.reduce((sum, value) => sum + (value - mean) ** 2, 0) / Math.max(1, values.length - 1);
  const scale = Math.sqrt(variance) || 1;
  return Float64Array.from(values, (value) => Math.max(-3.25, Math.min(3.25, (value - mean) / scale)));
}

function drawTreatmentCard(svg, rawValues, treatedValues, data, { x0, y0 = 12, width, title, routeClass, trim = 0 }) {
  const top = y0 + 46;
  const bottom = y0 + 274;
  const left = x0 + 36;
  const right = x0 + width - 20;
  const safeTrim = Math.min(trim, Math.max(0, Math.floor((rawValues.length - 3) / 2)));
  const raw = standardizedShape(rawValues.slice(safeTrim, rawValues.length - safeTrim || undefined));
  const treated = standardizedShape(treatedValues.slice(safeTrim, treatedValues.length - safeTrim || undefined));
  const axis = data.axis.slice(safeTrim, data.axis.length - safeTrim || undefined);
  const x = (index) => left + index / Math.max(1, raw.length - 1) * (right - left);
  const y = (value) => top + (3.5 - value) / 7 * (bottom - top);

  svg.append(svgElement("rect", { x: x0, y: y0, width, height: 322, rx: 12, class: "treatment-card-bg" }));
  addText(svg, title, { x: x0 + 22, y: y0 + 28, class: "treatment-panel-title" });
  addText(svg, "standardized spectral shape", { x: x0 + width - 22, y: y0 + 28, class: "treatment-panel-note", "text-anchor": "end" });
  [-2, 0, 2].forEach((value) => {
    svg.append(svgElement("line", { x1: left, y1: y(value), x2: right, y2: y(value), class: "treatment-grid" }));
  });
  svg.append(svgElement("path", { d: pathFromValues(raw, x, y), class: "treatment-raw-line" }));
  svg.append(svgElement("path", { d: pathFromValues(treated, x, y), class: routeClass }));
  [0, .5, 1].forEach((fraction) => {
    const index = Math.round(fraction * (axis.length - 1));
    addText(svg, compactNumber(axis[index]), { x: x(index), y: y0 + 297, class: "n4viz-tick", "text-anchor": "middle" });
  });
  addText(svg, axisUnit(data.meta.unit), { x: x0 + width / 2, y: y0 + 316, class: "treatment-panel-note", "text-anchor": "middle" });
}

function drawOperatorChart(data, hpoPipeline, aomPipeline) {
  lastOperatorChart = { data, hpoPipeline, aomOperator: aomPipeline };
  const svg = byId("operator-chart");
  svg.replaceChildren();
  const compact = window.innerWidth < 640;
  svg.setAttribute("viewBox", compact ? "0 0 640 688" : "0 0 1280 360");
  const sortedRows = Array.from({ length: data.trainRows }, (_, index) => index)
    .sort((left, right) => data.trainY[left] - data.trainY[right]);
  const representativeRow = sortedRows[Math.floor(sortedRows.length / 2)];
  const rawSpectrum = data.trainX.data.slice(representativeRow * data.cols, (representativeRow + 1) * data.cols);
  const hpoTransformed = transformWithPipeline(data.trainX.data, data.trainRows, data.cols, hpoPipeline);
  const hpoSpectrum = hpoTransformed.slice(representativeRow * data.cols, (representativeRow + 1) * data.cols);
  const aomTransformed = transformWithPipeline(data.trainX.data, data.trainRows, data.cols, aomPipeline);
  const aomSpectrum = aomTransformed.slice(representativeRow * data.cols, (representativeRow + 1) * data.cols);
  const aomTrim = pipelinePreviewTrim(aomPipeline);
  if (compact) {
    drawTreatmentCard(svg, rawSpectrum, hpoSpectrum, data, {
      x0: 10, y0: 8, width: 620, title: "HPO-selected view", routeClass: "treatment-hpo-line", trim: pipelinePreviewTrim(hpoPipeline),
    });
    drawTreatmentCard(svg, rawSpectrum, aomSpectrum, data, {
      x0: 10, y0: 350, width: 620, title: "AOM-selected view", routeClass: "treatment-aom-line", trim: aomTrim,
    });
  } else {
    drawTreatmentCard(svg, rawSpectrum, hpoSpectrum, data, {
      x0: 12, width: 620, title: "HPO-selected view", routeClass: "treatment-hpo-line", trim: pipelinePreviewTrim(hpoPipeline),
    });
    drawTreatmentCard(svg, rawSpectrum, aomSpectrum, data, {
      x0: 648, width: 620, title: "AOM-selected view", routeClass: "treatment-aom-line", trim: aomTrim,
    });
  }
}

window.addEventListener("resize", () => {
  window.clearTimeout(operatorResizeTimer);
  operatorResizeTimer = window.setTimeout(() => {
    if (lastOperatorChart) drawOperatorChart(lastOperatorChart.data, lastOperatorChart.hpoPipeline, lastOperatorChart.aomOperator);
  }, 120);
});

function formatAlpha(alpha) {
  if (!Number.isFinite(alpha)) return "n/a";
  if (alpha >= .01 && alpha < 1000) return alpha.toLocaleString("en-US", { maximumFractionDigits: 4 });
  return alpha.toExponential(0).replace("e+", "e");
}

function describePreprocessingStep(step) {
  if (step.op === "Detrend") return `${Number(step.params[0]) === 2 ? "quadratic" : "linear"} baseline removed`;
  if (step.op === "StandardNormalVariate") return "standard normal variate (SNV)";
  if (step.op === "GaussianFilter") return `Gaussian smoothing, σ = ${formatAlpha(Number(step.params[0]))}`;
  if (step.op === "Derivative") return `${Number(step.params[0]) === 2 ? "second" : "first"} finite derivative`;
  if (step.op === "SavitzkyGolay") {
    const [window, polynomial, derivative = 0] = step.params;
    const action = derivative === 0 ? "smoothing" : derivative === 1 ? "first derivative" : "second derivative";
    return `SG window ${window}, polynomial degree ${polynomial}, ${action}`;
  }
  return step.op;
}

function describePipeline(selectedPipeline) {
  if (!selectedPipeline || selectedPipeline.steps.length === 0) return "No spectral pretreatment";
  return selectedPipeline.steps.map(describePreprocessingStep).join(" → ");
}

function componentLabel(count) {
  return `${count} PLS latent component${count === 1 ? "" : "s"}`;
}

function renderModelSetting(cell, setting) {
  cell.replaceChildren();
  const wrapper = document.createElement("div");
  wrapper.className = "model-setting";
  const title = document.createElement("strong");
  title.textContent = setting.title;
  const detail = document.createElement("span");
  detail.textContent = setting.detail;
  const selection = document.createElement("small");
  selection.textContent = setting.selection;
  wrapper.append(title, detail, selection);
  cell.append(wrapper);
}

function renderMethodResult(prefix, result, stats, setting) {
  renderModelSetting(byId(`${prefix}-selection`), setting);
  byId(`${prefix}-rmse`).textContent = formatMetric(stats.rmse);
  byId(`${prefix}-mae`).textContent = formatMetric(stats.mae);
  byId(`${prefix}-r2`).textContent = formatMetric(stats.r2);
  byId(`${prefix}-time`).textContent = formatTime(result.elapsed);
  byId(`${prefix}-workload`).textContent = result.searchLabel || `${result.candidateFits ?? 1} fit calls`;
}

function resetHpoScoreTable() {
  const body = byId("hpo-all-scores");
  body.replaceChildren();
  const row = document.createElement("tr");
  const cell = document.createElement("td");
  cell.colSpan = 6;
  cell.textContent = "Run the experiment to populate all candidate scores.";
  row.append(cell);
  body.append(row);
}

function appendScoreCell(row, value) {
  const cell = document.createElement("td");
  cell.textContent = value;
  row.append(cell);
}

function renderHpoScoreTable(pipelines, plsResults, ridgeResults, hpoPls, hpoRidge) {
  const body = byId("hpo-all-scores");
  body.replaceChildren();
  const plsById = new Map(plsResults.map((result) => [result.pipeline.id, result]));
  const ridgeById = new Map(ridgeResults.map((result) => [result.pipeline.id, result]));
  pipelines.forEach((selectedPipeline) => {
    const pls = plsById.get(selectedPipeline.id);
    const ridge = ridgeById.get(selectedPipeline.id);
    const plsWinner = selectedPipeline.id === hpoPls.operator.id;
    const ridgeWinner = selectedPipeline.id === hpoRidge.operator.id;
    const row = document.createElement("tr");
    row.dataset.pipeline = selectedPipeline.id;
    if (plsWinner) row.classList.add("is-pls-winner");
    if (ridgeWinner) row.classList.add("is-ridge-winner");
    const name = document.createElement("th");
    name.scope = "row";
    name.textContent = selectedPipeline.name;
    const description = document.createElement("small");
    description.textContent = describePipeline(selectedPipeline);
    name.append(description);
    row.append(name);
    appendScoreCell(row, pls ? String(pls.components) : "not stable");
    appendScoreCell(row, pls ? formatMetric(pls.cvRmse) : "—");
    appendScoreCell(row, ridge ? formatAlpha(ridge.alpha) : "not stable");
    appendScoreCell(row, ridge ? formatMetric(ridge.cvRmse) : "—");
    const selected = document.createElement("td");
    selected.className = "winner-badges";
    [[plsWinner, "PLS winner", "pls"], [ridgeWinner, "Ridge winner", "ridge"]].forEach(([winner, label, type]) => {
      if (!winner) return;
      const badge = document.createElement("span");
      badge.className = `score-winner ${type}`;
      badge.textContent = label;
      selected.append(badge);
    });
    if (!plsWinner && !ridgeWinner) selected.textContent = "—";
    row.append(selected);
    body.append(row);
  });
}

function routeComparison(rawStats, hpoStats, aomStats) {
  const routes = [
    { key: "raw", label: "Raw", stats: rawStats },
    { key: "hpo", label: "HPO", stats: hpoStats },
    { key: "aom", label: "AOM", stats: aomStats },
  ];
  const bestRmse = Math.min(...routes.map((route) => route.stats.rmse));
  return { routes, winners: routes.filter((route) => protocolScoresMatch(route.stats.rmse, bestRmse)) };
}

function winnerHeadline(comparison) {
  const labels = comparison.winners.map((route) => route.label).join(" & ");
  return comparison.winners.length === 1 ? `${labels} wins` : `${labels} tie`;
}

function comparisonValues(comparison) {
  return comparison.routes.map((route) => `${route.label} ${formatMetric(route.stats.rmse)}`).join(" · ");
}

function renderLocalConclusion(rawPlsStats, hpoPlsStats, aomPlsStats, rawRidgeStats, hpoRidgeStats, aomRidgeStats, hpoPls, selected) {
  const pls = routeComparison(rawPlsStats, hpoPlsStats, aomPlsStats);
  const ridge = routeComparison(rawRidgeStats, hpoRidgeStats, aomRidgeStats);
  const plsHeadline = winnerHeadline(pls);
  const ridgeHeadline = winnerHeadline(ridge);
  let title = "The best calibration route differs by model family in this run";
  if (plsHeadline === ridgeHeadline) {
    const sharedLabels = pls.winners.map((route) => route.label).join(" & ");
    title = pls.winners.length === 1
      ? `${sharedLabels} is best for both model families in this run`
      : `${sharedLabels} share the best result for both model families in this run`;
  }
  byId("local-conclusion-title").textContent = title;
  byId("local-conclusion-copy").textContent = `This conclusion compares all three routes on this held-out split only. HPO selected ${hpoPls.operator.name}; AOM selected ${selected.name}. The 32-dataset evidence remains in the paper summary below.`;
  byId("conclusion-pls").textContent = comparisonValues(pls);
  byId("conclusion-pls-detail").textContent = `${plsHeadline} on validation RMSE.`;
  byId("conclusion-ridge").textContent = comparisonValues(ridge);
  byId("conclusion-ridge-detail").textContent = `${ridgeHeadline} on validation RMSE.`;
}

function setComparisonVerdict(valueId, detailId, rawStats, hpoStats, aomStats, family) {
  const value = byId(valueId);
  const comparison = routeComparison(rawStats, hpoStats, aomStats);
  value.className = comparison.winners.length === 1 ? `verdict-${comparison.winners[0].key}` : "neutral";
  value.textContent = winnerHeadline(comparison);
  const winnerText = comparison.winners.length === 1
    ? `${comparison.winners[0].label} has the lowest held-out RMSE`
    : `${comparison.winners.map((route) => route.label).join(" and ")} share the lowest held-out RMSE`;
  byId(detailId).textContent = `${family}: ${winnerText} · ${comparisonValues(comparison)}.`;
  return comparison;
}

function fitAomPlsWithStableBudget(data, requestedBudget, foldCount, pipelines) {
  const budgets = [...new Set([requestedBudget, 20, 15, 10, 5, 3, 1])]
    .filter((value) => value <= requestedBudget && value >= 1)
    .sort((left, right) => right - left);
  let lastError = null;
  for (const budget of budgets) {
    try {
      const model = fitAomChain(
        matrix(data.trainX.data, data.trainRows, data.cols),
        matrix(data.trainY, data.trainRows, 1),
        nativeChainDescriptor(pipelines),
        { head: "pls", nFolds: foldCount, plsComponents: Array.from({ length: budget }, (_, index) => index + 1) },
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
  const searchProfile = selectedSearchProfile();
  document.documentElement.dataset.protocolParity = "checking";
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
    const profileComponentLimit = searchProfile.id === "quick" ? 5 : requestedComponents;
    const requestedComponentBudget = Math.max(1, Math.min(profileComponentLimit, currentData.cols, minFoldTrain - 1));
    const ridgeAlphas = searchProfile.id === "quick" ? [1e-4, 1, 1e4] : RIDGE_ALPHAS;
    const aomSelectorStarted = performance.now();
    const aomPlsFit = fitAomPlsWithStableBudget(
      currentData,
      requestedComponentBudget,
      foldCount,
      searchProfile.pipelines,
    );
    const aomSelectorElapsed = performance.now() - aomSelectorStarted;
    const componentBudget = aomPlsFit.budget;
    const rawPls = await fitCrossValidatedPls(currentData, componentBudget, foldCount, (fraction, component, total) => {
      setActivity({
        state: "running", progress: 26 + fraction, phase: "pls",
        title: "PLS · raw reference",
        detail: `Calibration CV: component ${component}/${total}, ${foldCount} folds.`,
      });
    });

    byId("run-note").textContent = `Step 2/6: ${searchProfile.label} PLS is screening ${searchProfile.pipelines.length} pipelines × ${componentBudget} component counts.`;
    setActivity({
      state: "running", progress: 27, phase: "pls",
      title: "PLS · preprocessing HPO",
      detail: `${searchProfile.pipelines.length} pipelines × ${componentBudget} component counts · same ${foldCount} folds · pooled out-of-fold RMSE…`,
    });
    await yieldToBrowser();
    const hpoPls = await fitPreprocessingHpoPls(currentData, componentBudget, foldCount, searchProfile.pipelines, (fraction, selectedPipeline, component, total) => {
      setActivity({
        state: "running", progress: 27 + fraction * 54, phase: "pls",
        title: "PLS · preprocessing HPO",
        detail: `${selectedPipeline.name} · component ${component}/${total} · shared ${foldCount}-fold plan.`,
      });
    });

    assertProtocolParity(
      hpoPls.rawCandidate
        && hpoPls.rawCandidate.components === rawPls.components
        && protocolScoresMatch(hpoPls.rawCandidate.cvRmse, rawPls.cvRmse),
      "raw PLS and the raw subset of PLS-HPO do not select the same component count and score.",
    );
    byId("run-note").textContent = `Step 3/6: native AOM-PLS is screening the same ${searchProfile.pipelines.length} chains up to ${componentBudget} components.`;
    setActivity({
      state: "running", progress: 84, phase: "aom-pls",
      title: "Running AOM-PLS",
      detail: `Native chain/component selection on the same calibration folds…`,
    });
    await yieldToBrowser();
    const aomPlsModel = aomPlsFit.model;
    const aomComponentAudit = { components: Math.round(aomPlsModel.selectedParameter), score: aomPlsModel.score };
    const aomPlsPredictions = predictModel(aomPlsModel, matrix(currentData.testX.data, currentData.testRows, currentData.cols)).data;
    const aomPls = {
      model: aomPlsModel,
      predictions: aomPlsPredictions,
      elapsed: aomSelectorElapsed,
      components: aomComponentAudit.components,
      candidateFits: searchProfile.pipelines.length * aomPlsFit.budget * foldCount + 1,
      searchLabel: `${searchProfile.pipelines.length} chains × ${aomPlsFit.budget} components`,
    };

    byId("run-note").textContent = `Step 4/6: selecting Ridge α on raw spectra, then screening preprocessing + α.`;
    setActivity({
      state: "running", progress: 87, phase: "ridge",
      title: "Ridge · raw reference",
      detail: `Cross-validating ${ridgeAlphas.length} logarithmic regularisation values…`,
    });
    await yieldToBrowser();
    const rawRidge = await fitCrossValidatedRidge(currentData, foldCount, ridgeAlphas, (fraction, alpha) => {
      setActivity({
        state: "running", progress: 87 + fraction, phase: "ridge",
        title: "Ridge · raw reference",
        detail: `Calibration CV: α ${formatAlpha(alpha)}, ${foldCount} folds.`,
      });
    });

    byId("run-note").textContent = `Step 5/6: ${searchProfile.label} Ridge is screening ${searchProfile.pipelines.length} pipelines × ${ridgeAlphas.length} α values.`;
    const hpoRidge = await fitPreprocessingHpoRidge(currentData, foldCount, ridgeAlphas, searchProfile.pipelines, (fraction, selectedPipeline, alpha, alphaIndex, alphaCount) => {
      setActivity({
        state: "running", progress: 88 + fraction * 9, phase: "ridge",
        title: "Ridge · preprocessing HPO",
        detail: `${selectedPipeline.name} · α ${alphaIndex}/${alphaCount} (${formatAlpha(alpha)}) · shared ${foldCount}-fold plan.`,
      });
    });
    assertProtocolParity(
      hpoRidge.rawCandidate
        && hpoRidge.rawCandidate.alpha === rawRidge.alpha
        && protocolScoresMatch(hpoRidge.rawCandidate.cvRmse, rawRidge.cvRmse),
      "raw Ridge and the raw subset of Ridge-HPO do not select the same α and score.",
    );
    byId("run-note").textContent = "Step 6/6: native AOM-Ridge is screening the same preprocessing chains and α grid.";
    setActivity({
      state: "running", progress: 97, phase: "aom-ridge",
      title: "Running AOM-Ridge",
      detail: `${searchProfile.pipelines.length} shared chains × ${ridgeAlphas.length} α values with ${foldCount}-fold calibration CV…`,
    });
    await yieldToBrowser();
    const aomRidgeStarted = performance.now();
    const aomRidgeModel = fitAomChain(
      matrix(currentData.trainX.data, currentData.trainRows, currentData.cols),
      matrix(currentData.trainY, currentData.trainRows, 1),
      nativeChainDescriptor(searchProfile.pipelines),
      { head: "ridge", nFolds: foldCount, ridgeLambdas: ridgeAlphas },
    );
    const aomRidge = {
      model: aomRidgeModel,
      predictions: predictModel(aomRidgeModel, matrix(currentData.testX.data, currentData.testRows, currentData.cols)).data,
      elapsed: performance.now() - aomRidgeStarted,
      alpha: aomRidgeModel.selectedParameter,
      cvRmse: aomRidgeModel.score,
      operator: searchProfile.pipelines[aomRidgeModel.selectedChain],
      candidateFits: searchProfile.pipelines.length * ridgeAlphas.length * foldCount + 1,
      searchLabel: `${searchProfile.pipelines.length} chains × ${ridgeAlphas.length} α`,
    };
    assertProtocolParity(
      nativeChainDescriptor(searchProfile.pipelines).chainOffsets.length === searchProfile.pipelines.length + 1,
      "the native AOM chain descriptor does not match the shared HPO/AOM bank.",
    );
    document.documentElement.dataset.protocolParity = "pass";
    if (serial !== comparisonSerial) return;

    setActivity({
      state: "running", progress: 99, phase: "results",
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
    const selected = searchProfile.pipelines[aomPlsModel.selectedChain] || searchProfile.pipelines[0];

    byId("pls-raw-card").textContent = "Raw spectrum";
    byId("pls-raw-card-detail").textContent = `${componentLabel(rawPls.components)} · ${foldCount}-fold calibration CV RMSE ${formatMetric(rawPls.cvRmse)}`;
    byId("pls-hpo-card").textContent = hpoPls.operator.name;
    byId("pls-hpo-card-detail").textContent = `${describePipeline(hpoPls.operator)} · ${componentLabel(hpoPls.components)} · ${foldCount}-fold calibration CV RMSE ${formatMetric(hpoPls.cvRmse)}`;
    byId("operator").textContent = selected.name;
    byId("operator-detail").textContent = `${describePipeline(selected)} · ${componentLabel(aomComponentAudit.components)} · ${foldCount}-fold calibration CV RMSE ${formatMetric(aomPlsModel.score)}`;
    byId("ridge-raw-card").textContent = "Raw spectrum";
    byId("ridge-raw-card-detail").textContent = `Ridge α = ${formatAlpha(rawRidge.alpha)} · ${foldCount}-fold calibration CV RMSE ${formatMetric(rawRidge.cvRmse)}`;
    byId("ridge-hpo-card").textContent = hpoRidge.operator.name;
    byId("ridge-hpo-card-detail").textContent = `${describePipeline(hpoRidge.operator)} · Ridge regularisation α = ${formatAlpha(hpoRidge.alpha)} · ${foldCount}-fold calibration CV RMSE ${formatMetric(hpoRidge.cvRmse)}`;
    byId("ridge-aom-card").textContent = aomRidge.operator.name;
    byId("ridge-aom-card-detail").textContent = `${describePipeline(aomRidge.operator)} · Ridge α = ${formatAlpha(aomRidge.alpha)} · ${foldCount}-fold calibration CV RMSE ${formatMetric(aomRidge.cvRmse)}`;
    renderMethodResult("pls-default", rawPls, rawPlsStats, {
      title: "Raw spectrum",
      detail: `${componentLabel(rawPls.components)} · no spectral pretreatment`,
      selection: `${foldCount}-fold calibration CV RMSE ${formatMetric(rawPls.cvRmse)}`,
    });
    renderMethodResult("pls-hpo", hpoPls, hpoPlsStats, {
      title: hpoPls.operator.name,
      detail: `${describePipeline(hpoPls.operator)} · ${componentLabel(hpoPls.components)}`,
      selection: `${foldCount}-fold calibration CV RMSE ${formatMetric(hpoPls.cvRmse)}`,
    });
    const aomBudgetNote = aomPlsFit.budget < requestedComponentBudget ? ` (shared stable limit; requested ${requestedComponentBudget})` : "";
    renderMethodResult("aom-pls", aomPls, aomPlsStats, {
      title: selected.name,
      detail: `${describePipeline(selected)} · ${componentLabel(aomComponentAudit.components)}${aomBudgetNote}`,
      selection: `${foldCount}-fold calibration CV RMSE ${formatMetric(aomPlsModel.score)}`,
    });
    renderMethodResult("ridge-default", rawRidge, rawRidgeStats, {
      title: "Raw spectrum",
      detail: `Ridge regularisation α = ${formatAlpha(rawRidge.alpha)} · no spectral pretreatment`,
      selection: `${foldCount}-fold calibration CV RMSE ${formatMetric(rawRidge.cvRmse)}`,
    });
    renderMethodResult("ridge-hpo", hpoRidge, hpoRidgeStats, {
      title: hpoRidge.operator.name,
      detail: `${describePipeline(hpoRidge.operator)} · Ridge regularisation α = ${formatAlpha(hpoRidge.alpha)}`,
      selection: `${foldCount}-fold calibration CV RMSE ${formatMetric(hpoRidge.cvRmse)}`,
    });
    renderMethodResult("aom-ridge", aomRidge, aomRidgeStats, {
      title: aomRidge.operator.name,
      detail: `${describePipeline(aomRidge.operator)} · Ridge regularisation α = ${formatAlpha(aomRidge.alpha)}`,
      selection: `${foldCount}-fold calibration CV RMSE ${formatMetric(aomRidge.cvRmse)}`,
    });

    const plsVerdict = setComparisonVerdict("rmse-delta", "delta-detail", rawPlsStats, hpoPlsStats, aomPlsStats, "PLS");
    const ridgeVerdict = setComparisonVerdict("ridge-rmse-delta", "ridge-delta-detail", rawRidgeStats, hpoRidgeStats, aomRidgeStats, "Ridge");
    byId("hpo-search-summary").textContent = `${searchProfile.label} · ${searchProfile.pipelines.length} pipelines · one shared fold plan`;
    byId("hpo-protocol-detail").textContent = `Raw, HPO and AOM share the same ${foldCount} contiguous folds and pooled out-of-fold RMSE. HPO and AOM also receive the exact same ${searchProfile.pipelines.length} preprocessing chains, PLS component grid and Ridge α grid. Parity audit passed: HPO's Raw spectrum candidate exactly matches the standalone Raw reference (${componentLabel(rawPls.components)}, CV RMSE ${formatMetric(rawPls.cvRmse)}). The ${currentData.testRows} validation rows stay untouched until final scoring.`;
    byId("hpo-pls-detail").textContent = `Screened ${searchProfile.pipelines.length} pipelines × components 1–${componentBudget}. Winner: ${hpoPls.operator.name}, ${hpoPls.components} components (CV RMSE ${formatMetric(hpoPls.cvRmse)}; ${hpoPls.candidateFits} fit calls).`;
    byId("hpo-ridge-detail").textContent = `Screened ${searchProfile.pipelines.length} pipelines × α {${ridgeAlphas.map(formatAlpha).join(", ")}}. Winner: ${hpoRidge.operator.name}, α ${formatAlpha(hpoRidge.alpha)} (CV RMSE ${formatMetric(hpoRidge.cvRmse)}; ${hpoRidge.candidateFits} fit calls).`;
    renderHpoScoreTable(searchProfile.pipelines, hpoPls.pipelineResults, hpoRidge.pipelineResults, hpoPls, hpoRidge);
    const namedResults = [
      { name: "raw PLS", stats: rawPlsStats }, { name: "PLS-HPO", stats: hpoPlsStats }, { name: "AOM-PLS", stats: aomPlsStats },
      { name: "raw Ridge", stats: rawRidgeStats }, { name: "Ridge-HPO", stats: hpoRidgeStats }, { name: "AOM-Ridge", stats: aomRidgeStats },
    ];
    const bestRmse = Math.min(...namedResults.map((item) => item.stats.rmse));
    const bestResults = namedResults.filter((item) => protocolScoresMatch(item.stats.rmse, bestRmse));
    const bestNames = bestResults.map((item) => item.name).join(bestResults.length > 2 ? ", " : " and ");
    const bestVerb = bestResults.length === 1 ? "has" : "share";
    byId("result-summary").textContent = `On these ${currentData.testRows} held-out rows, ${bestNames} ${bestVerb} the lowest RMSE (${formatMetric(bestRmse)}). This is one local result; the paper-context panel below reports the 32-dataset evidence.`;
    byId("pretreatment-hpo-name").textContent = hpoPls.operator.name;
    byId("pretreatment-hpo-setting").textContent = `${describePipeline(hpoPls.operator)} · ${componentLabel(hpoPls.components)} · ${foldCount}-fold calibration CV RMSE ${formatMetric(hpoPls.cvRmse)} · validation RMSE ${formatMetric(hpoPlsStats.rmse)}`;
    byId("pretreatment-aom-name").textContent = selected.name;
    byId("pretreatment-aom-setting").textContent = `${selected.detail} ${componentLabel(aomComponentAudit.components)} · ${foldCount}-fold calibration CV RMSE ${formatMetric(aomPlsModel.score)} · validation RMSE ${formatMetric(aomPlsStats.rmse)}`;
    byId("operator-preview-title").textContent = "The spectral views selected for PLS";
    const edgeNote = pipelinePreviewTrim(hpoPls.operator) > 0 || pipelinePreviewTrim(selected) > 0
      ? " Boundary transients are clipped only in this preview; fitting uses the complete transformed matrices."
      : "";
    byId("operator-explanation").textContent = `Each card compares the same representative raw spectrum (dashed) with the selected spectral view (solid). Each curve is standardized separately for shape comparison only; fitting uses complete transformed values. Exact settings, CV scores and validation scores are stated above.${edgeNote}`;
    renderLocalConclusion(rawPlsStats, hpoPlsStats, aomPlsStats, rawRidgeStats, hpoRidgeStats, aomRidgeStats, hpoPls, selected);
    byId("fairness-text").textContent = `${currentData.trainRows} calibration · ${currentData.testRows} held out · raw included · same ${foldCount} folds · pooled OOF RMSE · parity checks passed`;

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
    drawOperatorChart(currentData, hpoPls.operator, selected);
    byId("run-note").textContent = `Complete: ${currentData.meta.label}; all metrics use the untouched validation partition.`;
    byId("run-note").className = "form-status success";
    setActivity({
      state: "complete", progress: 100, phase: "results",
      title: "Comparison complete",
      detail: `Six routes complete · best local RMSE ${formatMetric(bestRmse)} (${bestNames}) · ${currentData.testRows} held-out rows.`,
    });

    if (new URLSearchParams(location.search).has("selftest")) {
      document.documentElement.dataset.selftest = parserSelfTest()
        && selectionContractSelfTest()
        && namedResults.every((item) => Number.isFinite(item.stats.rmse))
        && byId("rmse-chart").children.length > 10
        && byId("operator-chart").children.length > 15
        && byId("aom-pls-selection").textContent.includes("PLS latent component")
        && byId("hpo-all-scores").children.length === searchProfile.pipelines.length
        && byId("hpo-all-scores").querySelector('tr[data-pipeline="raw"]')?.cells[2].textContent === formatMetric(rawPls.cvRmse)
        && !byId("pls-hpo-card").textContent.includes("—")
        && byId("rmse-delta").textContent === winnerHeadline(plsVerdict)
        && byId("ridge-rmse-delta").textContent === winnerHeadline(ridgeVerdict)
        && ["pls-default", "pls-hpo", "aom-pls", "ridge-default", "ridge-hpo", "aom-ridge"]
          .every((prefix) => byId(`${prefix}-time`).textContent !== "—" && byId(`${prefix}-workload`).textContent !== "—")
        && document.documentElement.dataset.protocolParity === "pass"
        && byId("activity-progress").getAttribute("aria-valuenow") === "100"
        && byId("activity-progress-bar").style.width === "100%"
        && byId("ridge-prediction-chart").children.length > 10 ? "pass" : "fail";
      document.documentElement.dataset.selftestViewport = `${window.innerWidth}/${document.documentElement.scrollWidth}`;
    }
  } catch (error) {
    console.error(error);
    document.documentElement.dataset.protocolParity = "fail";
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
  setDatasetSourceMode("upload");
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

function selectionContractSelfTest() {
  const sharedPipelines = buildSharedPipelines();
  const descriptor = nativeChainDescriptor(sharedPipelines);
  const operatorIds = selectedOperators().map((operator) => operator.id);
  const identityControl = document.querySelector(`#operator-controls input[value="${IDENTITY_OPERATOR?.id}"]`);
  return sharedPipelines[0]?.id === "raw"
    && sharedPipelines.filter((item) => item.id === "raw").length === 1
    && operatorIds[0] === "raw"
    && operatorIds.filter((id) => id === "raw").length === 1
    && descriptor.chainOffsets.length === sharedPipelines.length + 1
    && identityControl?.checked
    && identityControl?.disabled;
}

async function initialise() {
  const query = new URLSearchParams(location.search);
  if (query.has("selftest") && query.get("selftest") !== "full") byId("search-depth").value = "quick";
  renderOperatorControls();
  setupCodeWorkbench();
  updateSearchDepthUi(false);
  resetResults();
  setActivity({ state: "loading", progress: 4, phase: "data", title: "Initialising the demonstration", detail: "Loading the bundled dataset catalogue…" });
  byId("run").addEventListener("click", runComparison);
  byId("load-upload").addEventListener("click", loadUploadedFiles);
  byId("source-upload").addEventListener("change", () => setDatasetSourceMode("upload", true));
  byId("source-bundled").addEventListener("change", () => setDatasetSourceMode("bundled", true));
  byId("components").addEventListener("change", markResultsStale);
  byId("folds").addEventListener("change", markResultsStale);
  byId("search-depth").addEventListener("change", () => updateSearchDepthUi(true));
  byId("preprocessing-order").addEventListener("change", () => updateSearchDepthUi(true));
  ["x-cal-file", "y-cal-file", "x-val-file", "y-val-file"].forEach((id) => byId(id).addEventListener("change", () => {
    setDatasetSourceMode("upload");
    updateUploadReadiness();
  }));
  setDatasetSourceMode("bundled");

  const manifestResponse = await fetch("datasets/manifest.json");
  if (!manifestResponse.ok) throw new Error(`Dataset manifest failed to load (${manifestResponse.status}).`);
  manifest = await manifestResponse.json();
  const requestedDataset = query.get("dataset");
  activeDatasetId = manifest.datasets.some((dataset) => dataset.id === requestedDataset)
    ? requestedDataset
    : manifest.datasets.find((dataset) => dataset.id === manifest.defaultDataset)?.id
      || manifest.datasets[0].id;
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
  if (runtimeReady && currentData && query.has("selftest")) await runComparison();
}

window.__AOM_DEMO__ = { parseXText, parseYText, validatePartitions, parserSelfTest, selectionContractSelfTest, selectedOperators, buildSharedPipelines, nativeChainDescriptor };

initialise().catch((error) => {
  console.error(error);
  byId("runtime-status").textContent = "Demo failed";
  byId("runtime-version").textContent = error.message;
  byId("runtime-dot").classList.replace("loading", "error");
  setActivity({ state: "error", progress: 0, phase: "data", title: "Demonstration could not start", detail: error.message });
  if (new URLSearchParams(location.search).has("selftest")) document.documentElement.dataset.selftest = "fail";
});
