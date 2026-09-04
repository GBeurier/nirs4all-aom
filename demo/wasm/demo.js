import {
  abiVersion,
  fitAom,
  fitAomRidge,
  fitModel,
  fitPls,
  loadModule,
  ppCreate,
  ppDestroy,
  ppTransform,
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

const pipeline = (id, name, short, steps = []) => ({ id, name, short, steps });
const sg = (window, polyorder, deriv = 0) => ({ op: "SavitzkyGolay", params: [window, polyorder, deriv, 1, 0] });
const HPO_PIPELINES = [
  pipeline("raw", "Raw spectrum", "raw X"),
  pipeline("detrend-1", "Linear detrending", "detrend d1", [{ op: "Detrend", params: [1] }]),
  pipeline("detrend-2", "Quadratic detrending", "detrend d2", [{ op: "Detrend", params: [2] }]),
  pipeline("snv", "Standard normal variate", "SNV", [{ op: "StandardNormalVariate", params: [] }]),
  pipeline("gaussian-05", "Gaussian smoothing σ0.5", "Gaussian σ0.5", [{ op: "GaussianFilter", params: [.5] }]),
  pipeline("gaussian-1", "Gaussian smoothing σ1", "Gaussian σ1", [{ op: "GaussianFilter", params: [1] }]),
  pipeline("gaussian-2", "Gaussian smoothing σ2", "Gaussian σ2", [{ op: "GaussianFilter", params: [2] }]),
  pipeline("gaussian-4", "Gaussian smoothing σ4", "Gaussian σ4", [{ op: "GaussianFilter", params: [4] }]),
  pipeline("sg-s5", "Savitzky–Golay smoothing 5", "SG 5/2 d0", [sg(5, 2)]),
  pipeline("sg-s7", "Savitzky–Golay smoothing 7", "SG 7/2 d0", [sg(7, 2)]),
  pipeline("sg-s11", "Savitzky–Golay smoothing 11", "SG 11/2 d0", [sg(11, 2)]),
  pipeline("sg-s15", "Savitzky–Golay smoothing 15", "SG 15/3 d0", [sg(15, 3)]),
  pipeline("sg-d1-5", "Savitzky–Golay derivative 5", "SG 5/2 d1", [sg(5, 2, 1)]),
  pipeline("sg-d1-7", "Savitzky–Golay derivative 7", "SG 7/2 d1", [sg(7, 2, 1)]),
  pipeline("sg-d1-11", "Savitzky–Golay derivative 11", "SG 11/2 d1", [sg(11, 2, 1)]),
  pipeline("sg-d1-15", "Savitzky–Golay derivative 15", "SG 15/3 d1", [sg(15, 3, 1)]),
  pipeline("sg-d2-7", "Savitzky–Golay second derivative 7", "SG 7/3 d2", [sg(7, 3, 2)]),
  pipeline("sg-d2-11", "Savitzky–Golay second derivative 11", "SG 11/3 d2", [sg(11, 3, 2)]),
  pipeline("sg-d2-15", "Savitzky–Golay second derivative 15", "SG 15/3 d2", [sg(15, 3, 2)]),
  pipeline("diff-1", "First finite derivative", "difference d1", [{ op: "Derivative", params: [1] }]),
  pipeline("diff-2", "Second finite derivative", "difference d2", [{ op: "Derivative", params: [2] }]),
  pipeline("snv-sg-s5", "SNV then SG smoothing 5", "SNV → SG 5/2", [{ op: "StandardNormalVariate", params: [] }, sg(5, 2)]),
  pipeline("snv-sg-s11", "SNV then SG smoothing 11", "SNV → SG 11/2", [{ op: "StandardNormalVariate", params: [] }, sg(11, 2)]),
  pipeline("snv-sg-d1-7", "SNV then SG derivative 7", "SNV → SG 7/2 d1", [{ op: "StandardNormalVariate", params: [] }, sg(7, 2, 1)]),
  pipeline("snv-sg-d1-11", "SNV then SG derivative 11", "SNV → SG 11/2 d1", [{ op: "StandardNormalVariate", params: [] }, sg(11, 2, 1)]),
  pipeline("d1-sg-s5", "Linear detrending then SG smoothing 5", "detrend → SG 5/2", [{ op: "Detrend", params: [1] }, sg(5, 2)]),
  pipeline("d1-sg-s11", "Linear detrending then SG smoothing 11", "detrend → SG 11/2", [{ op: "Detrend", params: [1] }, sg(11, 2)]),
  pipeline("d1-sg-d1-7", "Linear detrending then SG derivative 7", "detrend → SG 7/2 d1", [{ op: "Detrend", params: [1] }, sg(7, 2, 1)]),
  pipeline("d1-sg-d1-11", "Linear detrending then SG derivative 11", "detrend → SG 11/2 d1", [{ op: "Detrend", params: [1] }, sg(11, 2, 1)]),
  pipeline("gaussian-1-snv", "Gaussian σ1 then SNV", "Gaussian σ1 → SNV", [{ op: "GaussianFilter", params: [1] }, { op: "StandardNormalVariate", params: [] }]),
  pipeline("gaussian-2-snv", "Gaussian σ2 then SNV", "Gaussian σ2 → SNV", [{ op: "GaussianFilter", params: [2] }, { op: "StandardNormalVariate", params: [] }]),
  pipeline("sg-s5-snv", "SG smoothing 5 then SNV", "SG 5/2 → SNV", [sg(5, 2), { op: "StandardNormalVariate", params: [] }]),
  pipeline("sg-s11-snv", "SG smoothing 11 then SNV", "SG 11/2 → SNV", [sg(11, 2), { op: "StandardNormalVariate", params: [] }]),
];

const QUICK_PIPELINE_IDS = new Set(["raw", "detrend-1", "sg-s5", "sg-d1-5", "diff-1"]);
const RAW_PIPELINE = HPO_PIPELINES.find((item) => item.id === "raw");
const IDENTITY_OPERATOR = OPERATORS.find((item) => item.kind === 0);

function withMandatoryRaw(pipelines) {
  if (!RAW_PIPELINE) throw new Error("The raw HPO baseline is missing from the pipeline catalogue.");
  return [RAW_PIPELINE, ...pipelines.filter((item) => item.id !== RAW_PIPELINE.id)];
}

const SEARCH_PROFILES = {
  quick: { id: "quick", label: "Quick check", pipelines: withMandatoryRaw(HPO_PIPELINES.filter((item) => QUICK_PIPELINE_IDS.has(item.id))), repeats: 1 },
  full: { id: "full", label: "Full HPO", pipelines: withMandatoryRaw(HPO_PIPELINES), repeats: 3 },
};

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
  document.querySelectorAll("#search-depth, #components, #folds")
    .forEach((control) => { control.disabled = locked; });
  document.querySelectorAll("#operator-controls input")
    .forEach((control) => { control.disabled = locked || Number(control.value) === IDENTITY_OPERATOR.kind; });
  syncSourceControls();
}

function selectedSearchProfile() {
  return SEARCH_PROFILES[byId("search-depth").value] || SEARCH_PROFILES.full;
}

function updateSearchDepthUi(markStale = true) {
  const profile = selectedSearchProfile();
  const full = profile.id === "full";
  byId("search-depth-note").textContent = full
    ? `Broad library: ${profile.pipelines.length} pipelines with ${profile.repeats} repeated fold layouts; typically 20–45 seconds on bundled examples (device dependent).`
    : `${profile.pipelines.length} representative pipelines with one fold layout for a fast interface check.`;
  byId("hpo-scope").textContent = full
    ? "The full search covers raw spectra, SNV, two detrending orders, several Gaussian and Savitzky–Golay smoothers, first/second derivatives and selected two-step chains. Repeated deterministic fold layouts are averaged before the winner is refitted."
    : "The quick check screens raw spectra, linear detrending, one Savitzky–Golay smoother, one Savitzky–Golay derivative and one finite derivative. It is useful for checking files, not for an exhaustive comparison.";
  byId("run-search-summary").textContent = full ? "full repeated local HPO" : "quick local check";
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
    .map((input) => OPERATORS.find((operator) => operator.kind === Number(input.value)))
    .filter(Boolean);
  if (!IDENTITY_OPERATOR) throw new Error("The AOM identity baseline is missing from the operator catalogue.");
  return [IDENTITY_OPERATOR, ...selected.filter((operator) => operator.kind !== IDENTITY_OPERATOR.kind)];
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
    input.disabled = operator.kind === IDENTITY_OPERATOR.kind;
    const name = document.createElement("span");
    name.textContent = operator.name;
    const detail = document.createElement("small");
    detail.textContent = operator.kind === IDENTITY_OPERATOR.kind ? `${operator.short} · required baseline` : operator.short;
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

function contiguousFolds(rows, count, offset = 0) {
  const folds = Array.from({ length: count }, () => []);
  for (let position = 0; position < rows; position += 1) {
    const row = (position + offset) % rows;
    folds[Math.floor(position * count / rows)].push(row);
  }
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

async function scorePlsCandidates(data, maxComponents, foldCount, foldOffset = 0, onProgress) {
  let elapsed = 0;
  const folds = contiguousFolds(data.trainRows, foldCount, foldOffset);
  const allRows = Array.from({ length: data.trainRows }, (_, index) => index);
  const maxAllowed = Math.max(1, Math.min(maxComponents, data.cols, ...folds.map((held) => data.trainRows - held.length - 1)));
  const candidates = [];
  const totalUnits = maxAllowed * folds.length;
  let completedUnits = 0;
  let candidateFits = 0;
  for (let components = 1; components <= maxAllowed; components += 1) {
    const oof = new Float64Array(data.trainRows);
    let validCandidate = true;
    for (let foldIndex = 0; foldIndex < folds.length; foldIndex += 1) {
      const heldRows = folds[foldIndex];
      const held = new Set(heldRows);
      const fitRows = allRows.filter((row) => !held.has(row));
      const xFit = selectRows(data.trainX.data, fitRows, data.cols);
      const yFit = selectRows(data.trainY, fitRows, 1);
      const xHeld = selectRows(data.trainX.data, heldRows, data.cols);
      const fitStarted = performance.now();
      try {
        const model = fitPls(matrix(xFit, fitRows.length, data.cols), matrix(yFit, fitRows.length, 1), components);
        const predictions = predictPls(model, matrix(xHeld, heldRows.length, data.cols)).data;
        candidateFits += 1;
        elapsed += performance.now() - fitStarted;
        heldRows.forEach((row, index) => { oof[row] = predictions[index]; });
      } catch (error) {
        elapsed += performance.now() - fitStarted;
        validCandidate = false;
      }
      completedUnits += 1;
      if (!validCandidate) {
        completedUnits += folds.length - foldIndex - 1;
        break;
      }
      onProgress?.(completedUnits / totalUnits, components, maxAllowed);
    }
    if (validCandidate) candidates.push({ components, rmse: metrics(data.trainY, oof).rmse });
    onProgress?.(completedUnits / totalUnits, components, maxAllowed);
    await yieldToBrowser();
  }
  if (candidates.length === 0) throw new Error("No numerically stable PLS component count was found.");
  return { candidates, elapsed, maxAllowed, candidateFits };
}

async function fitCrossValidatedPls(data, maxComponents, foldCount, onProgress) {
  const scored = await scorePlsCandidates(data, maxComponents, foldCount, 0, onProgress);
  const candidates = [...scored.candidates];
  candidates.sort((left, right) => left.rmse - right.rmse || left.components - right.components);
  const selected = candidates[0];
  const finalFitStarted = performance.now();
  const model = fitPls(matrix(data.trainX.data, data.trainRows, data.cols), matrix(data.trainY, data.trainRows, 1), selected.components);
  const predictions = predictPls(model, matrix(data.testX.data, data.testRows, data.cols)).data;
  onProgress?.(1, selected.components, scored.maxAllowed);
  return {
    model,
    predictions,
    components: selected.components,
    cvRmse: selected.rmse,
    elapsed: scored.elapsed + performance.now() - finalFitStarted,
    maxAllowed: scored.maxAllowed,
    candidateFits: scored.candidateFits + 1,
  };
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

function transformedDataset(data, selectedPipeline) {
  if (selectedPipeline.steps.length === 0) return data;
  return {
    ...data,
    trainX: matrix(transformWithPipeline(data.trainX.data, data.trainRows, data.cols, selectedPipeline), data.trainRows, data.cols),
    testX: matrix(transformWithPipeline(data.testX.data, data.testRows, data.cols, selectedPipeline), data.testRows, data.cols),
  };
}

async function fitPreprocessingHpoPls(data, maxComponents, foldCount, pipelines, repeats, onProgress) {
  const candidates = [];
  let elapsed = 0;
  let candidateFits = 0;
  for (let pipelineIndex = 0; pipelineIndex < pipelines.length; pipelineIndex += 1) {
    const selectedPipeline = pipelines[pipelineIndex];
    const transformStarted = performance.now();
    try {
      const transformed = transformedDataset(data, selectedPipeline);
      elapsed += performance.now() - transformStarted;
      const aggregated = new Map();
      let maxAllowed = 1;
      for (let repeat = 0; repeat < repeats; repeat += 1) {
        const foldOffset = Math.round(repeat * data.trainRows / repeats) % data.trainRows;
        const scored = await scorePlsCandidates(transformed, maxComponents, foldCount, foldOffset, (fraction, component, total) => {
          const overall = (pipelineIndex * repeats + repeat + fraction) / (pipelines.length * repeats);
          onProgress?.(overall, selectedPipeline, component, total, repeat + 1, repeats);
        });
        elapsed += scored.elapsed;
        candidateFits += scored.candidateFits;
        maxAllowed = scored.maxAllowed;
        scored.candidates.forEach(({ components, rmse }) => {
          const aggregate = aggregated.get(components) || { sum: 0, count: 0 };
          aggregate.sum += rmse;
          aggregate.count += 1;
          aggregated.set(components, aggregate);
        });
      }
      aggregated.forEach((aggregate, components) => {
        if (aggregate.count === repeats) {
          candidates.push({ pipeline: selectedPipeline, pipelineIndex, components, cvRmse: aggregate.sum / aggregate.count, maxAllowed });
        }
      });
    } catch (error) {
      elapsed += performance.now() - transformStarted;
      onProgress?.((pipelineIndex + 1) / pipelines.length, selectedPipeline, maxComponents, maxComponents, repeats, repeats);
    }
  }
  if (candidates.length === 0) throw new Error("No numerically stable PLS preprocessing route was found.");
  candidates.sort((left, right) => left.cvRmse - right.cvRmse
    || left.components - right.components
    || left.pipelineIndex - right.pipelineIndex);
  const selected = candidates[0];
  const finalData = transformedDataset(data, selected.pipeline);
  const finalFitStarted = performance.now();
  const model = fitPls(matrix(finalData.trainX.data, finalData.trainRows, finalData.cols), matrix(finalData.trainY, finalData.trainRows, 1), selected.components);
  const predictions = predictPls(model, matrix(finalData.testX.data, finalData.testRows, finalData.cols)).data;
  elapsed += performance.now() - finalFitStarted;
  return { model, predictions, components: selected.components, cvRmse: selected.cvRmse, operator: selected.pipeline, elapsed, candidateFits: candidateFits + 1 };
}

async function scoreRidgeCandidates(data, foldCount, alphas, foldOffset = 0, onProgress) {
  let elapsed = 0;
  const folds = contiguousFolds(data.trainRows, foldCount, foldOffset);
  const allRows = Array.from({ length: data.trainRows }, (_, index) => index);
  const candidates = [];
  const totalUnits = alphas.length * folds.length;
  let completedUnits = 0;
  let candidateFits = 0;
  for (let alphaIndex = 0; alphaIndex < alphas.length; alphaIndex += 1) {
    const alpha = alphas[alphaIndex];
    const oof = new Float64Array(data.trainRows);
    let validCandidate = true;
    for (let foldIndex = 0; foldIndex < folds.length; foldIndex += 1) {
      const heldRows = folds[foldIndex];
      const held = new Set(heldRows);
      const fitRows = allRows.filter((row) => !held.has(row));
      const xFit = selectRows(data.trainX.data, fitRows, data.cols);
      const yFit = selectRows(data.trainY, fitRows, 1);
      const xHeld = selectRows(data.trainX.data, heldRows, data.cols);
      const fitStarted = performance.now();
      try {
        const model = fitModel("Ridge", matrix(xFit, fitRows.length, data.cols), matrix(yFit, fitRows.length, 1), 1, [alpha]);
        const predictions = predictModel(model, matrix(xHeld, heldRows.length, data.cols)).data;
        candidateFits += 1;
        elapsed += performance.now() - fitStarted;
        heldRows.forEach((row, index) => { oof[row] = predictions[index]; });
      } catch (error) {
        elapsed += performance.now() - fitStarted;
        validCandidate = false;
      }
      completedUnits += 1;
      if (!validCandidate) {
        completedUnits += folds.length - foldIndex - 1;
        break;
      }
      onProgress?.(completedUnits / totalUnits, alpha, alphaIndex + 1, alphas.length);
    }
    if (validCandidate) candidates.push({ alpha, rmse: metrics(data.trainY, oof).rmse });
    onProgress?.(completedUnits / totalUnits, alpha, alphaIndex + 1, alphas.length);
    await yieldToBrowser();
  }
  if (candidates.length === 0) throw new Error("No numerically stable Ridge regularisation value was found.");
  return { candidates, elapsed, candidateFits };
}

async function fitCrossValidatedRidge(data, foldCount, alphas, onProgress) {
  const scored = await scoreRidgeCandidates(data, foldCount, alphas, 0, onProgress);
  const candidates = [...scored.candidates];
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
  onProgress?.(1, selected.alpha, alphas.length, alphas.length);
  return { model, predictions, alpha: selected.alpha, cvRmse: selected.rmse, elapsed: scored.elapsed + performance.now() - finalFitStarted, candidateFits: scored.candidateFits + 1 };
}

async function fitPreprocessingHpoRidge(data, foldCount, alphas, pipelines, repeats, onProgress) {
  const candidates = [];
  let elapsed = 0;
  let candidateFits = 0;
  for (let pipelineIndex = 0; pipelineIndex < pipelines.length; pipelineIndex += 1) {
    const selectedPipeline = pipelines[pipelineIndex];
    const transformStarted = performance.now();
    try {
      const transformed = transformedDataset(data, selectedPipeline);
      elapsed += performance.now() - transformStarted;
      const aggregated = new Map();
      for (let repeat = 0; repeat < repeats; repeat += 1) {
        const foldOffset = Math.round(repeat * data.trainRows / repeats) % data.trainRows;
        const scored = await scoreRidgeCandidates(transformed, foldCount, alphas, foldOffset, (fraction, alpha, alphaIndex, alphaCount) => {
          const overall = (pipelineIndex * repeats + repeat + fraction) / (pipelines.length * repeats);
          onProgress?.(overall, selectedPipeline, alpha, alphaIndex, alphaCount, repeat + 1, repeats);
        });
        elapsed += scored.elapsed;
        candidateFits += scored.candidateFits;
        scored.candidates.forEach(({ alpha, rmse }) => {
          const aggregate = aggregated.get(alpha) || { sum: 0, count: 0 };
          aggregate.sum += rmse;
          aggregate.count += 1;
          aggregated.set(alpha, aggregate);
        });
      }
      aggregated.forEach((aggregate, alpha) => {
        if (aggregate.count === repeats) {
          candidates.push({ pipeline: selectedPipeline, pipelineIndex, alpha, cvRmse: aggregate.sum / aggregate.count });
        }
      });
    } catch (error) {
      elapsed += performance.now() - transformStarted;
      onProgress?.((pipelineIndex + 1) / pipelines.length, selectedPipeline, alphas.at(-1), alphas.length, alphas.length, repeats, repeats);
    }
  }
  if (candidates.length === 0) throw new Error("No numerically stable Ridge preprocessing route was found.");
  candidates.sort((left, right) => left.cvRmse - right.cvRmse
    || left.alpha - right.alpha
    || left.pipelineIndex - right.pipelineIndex);
  const selected = candidates[0];
  const finalData = transformedDataset(data, selected.pipeline);
  const finalFitStarted = performance.now();
  const model = fitModel("Ridge", matrix(finalData.trainX.data, finalData.trainRows, finalData.cols), matrix(finalData.trainY, finalData.trainRows, 1), 1, [selected.alpha]);
  const predictions = predictModel(model, matrix(finalData.testX.data, finalData.testRows, finalData.cols)).data;
  elapsed += performance.now() - finalFitStarted;
  return { model, predictions, alpha: selected.alpha, cvRmse: selected.cvRmse, operator: selected.pipeline, elapsed, candidateFits: candidateFits + 1 };
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
  const searchProfile = selectedSearchProfile();
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
        state: "running", progress: 26 + fraction, phase: "pls",
        title: "PLS · raw reference",
        detail: `Calibration CV: component ${component}/${total}, ${foldCount} folds.`,
      });
    });

    byId("run-note").textContent = `Step 2/6: ${searchProfile.label} PLS is screening ${searchProfile.pipelines.length} pipelines × ${componentBudget} component counts.`;
    setActivity({
      state: "running", progress: 27, phase: "pls",
      title: "PLS · preprocessing HPO",
      detail: `${searchProfile.pipelines.length} pipelines × ${componentBudget} component counts × ${searchProfile.repeats} fold layout${searchProfile.repeats > 1 ? "s" : ""}…`,
    });
    await yieldToBrowser();
    const hpoPls = await fitPreprocessingHpoPls(currentData, componentBudget, foldCount, searchProfile.pipelines, searchProfile.repeats, (fraction, selectedPipeline, component, total, repeat, repeats) => {
      setActivity({
        state: "running", progress: 27 + fraction * 56, phase: "pls",
        title: "PLS · preprocessing HPO",
        detail: `${selectedPipeline.name} · repeat ${repeat}/${repeats} · component ${component}/${total}.`,
      });
    });

    byId("run-note").textContent = `Step 3/6: native AOM-PLS is screening its ${operators.length}-operator strict-linear bank up to ${componentBudget} components.`;
    setActivity({
      state: "running", progress: 83, phase: "aom-pls",
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
      state: "running", progress: 85, phase: "ridge",
      title: "Ridge · raw reference",
      detail: `Cross-validating ${RIDGE_ALPHAS.length} logarithmic regularisation values…`,
    });
    await yieldToBrowser();
    const rawRidge = await fitCrossValidatedRidge(currentData, foldCount, RIDGE_ALPHAS, (fraction, alpha) => {
      setActivity({
        state: "running", progress: 85 + fraction, phase: "ridge",
        title: "Ridge · raw reference",
        detail: `Calibration CV: α ${formatAlpha(alpha)}, ${foldCount} folds.`,
      });
    });

    byId("run-note").textContent = `Step 5/6: ${searchProfile.label} Ridge is screening ${searchProfile.pipelines.length} pipelines × ${RIDGE_ALPHAS.length} α values.`;
    const hpoRidge = await fitPreprocessingHpoRidge(currentData, foldCount, RIDGE_ALPHAS, searchProfile.pipelines, searchProfile.repeats, (fraction, selectedPipeline, alpha, alphaIndex, alphaCount, repeat, repeats) => {
      setActivity({
        state: "running", progress: 86 + fraction * 11, phase: "ridge",
        title: "Ridge · preprocessing HPO",
        detail: `${selectedPipeline.name} · repeat ${repeat}/${repeats} · α ${alphaIndex}/${alphaCount} (${formatAlpha(alpha)}).`,
      });
    });

    byId("run-note").textContent = "Step 6/6: fitting the native compact AOM-Ridge simplex blender.";
    setActivity({
      state: "running", progress: 97, phase: "aom-ridge",
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
    byId("fairness-text").textContent = `${currentData.trainRows} calibration · ${currentData.testRows} held out · ${foldCount} folds · raw included · ${searchProfile.label}: ${searchProfile.pipelines.length} pipelines × ${searchProfile.repeats} layout${searchProfile.repeats > 1 ? "s" : ""}`;

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
        && selectionContractSelfTest()
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
  const profilesIncludeRaw = Object.values(SEARCH_PROFILES).every((profile) =>
    profile.pipelines[0]?.id === "raw"
    && profile.pipelines.filter((item) => item.id === "raw").length === 1);
  const operatorKinds = selectedOperators().map((operator) => operator.kind);
  const identityControl = document.querySelector(`#operator-controls input[value="${IDENTITY_OPERATOR?.kind}"]`);
  return profilesIncludeRaw
    && operatorKinds[0] === 0
    && operatorKinds.filter((kind) => kind === 0).length === 1
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
  if (runtimeReady && currentData && query.has("selftest")) await runComparison();
}

window.__AOM_DEMO__ = { parseXText, parseYText, validatePartitions, parserSelfTest, selectionContractSelfTest, selectedOperators };

initialise().catch((error) => {
  console.error(error);
  byId("runtime-status").textContent = "Demo failed";
  byId("runtime-version").textContent = error.message;
  byId("runtime-dot").classList.replace("loading", "error");
  setActivity({ state: "error", progress: 0, phase: "data", title: "Demonstration could not start", detail: error.message });
  if (new URLSearchParams(location.search).has("selftest")) document.documentElement.dataset.selftest = "fail";
});
