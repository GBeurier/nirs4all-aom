import {
  abiVersion,
  fitAom,
  fitPls,
  loadModule,
  predictModel,
  predictPls,
  version,
} from "./n4m/index.js";

const operatorNames = [
  "Identity",
  "Polynomial detrending",
  "Savitzky–Golay smoothing",
  "Savitzky–Golay derivative",
  "Finite difference",
];

const byId = (id) => document.getElementById(id);

function mulberry32(seed) {
  return () => {
    let z = seed += 0x6d2b79f5;
    z = Math.imul(z ^ (z >>> 15), z | 1);
    z ^= z + Math.imul(z ^ (z >>> 7), z | 61);
    return ((z ^ (z >>> 14)) >>> 0) / 4294967296;
  };
}

function normal(random) {
  const u = Math.max(random(), Number.EPSILON);
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * random());
}

function gaussian(x, center, width) {
  const z = (x - center) / width;
  return Math.exp(-0.5 * z * z);
}

function syntheticNir(noise) {
  const rows = 84;
  const cols = 120;
  const trainRows = 64;
  const random = mulberry32(260513587);
  const X = new Float64Array(rows * cols);
  const y = new Float64Array(rows);

  for (let i = 0; i < rows; i += 1) {
    const chemistry = normal(random);
    const moisture = normal(random);
    const slope = 0.12 * normal(random);
    const offset = 0.08 * normal(random);
    y[i] = 2.4 + 1.35 * chemistry - 0.32 * moisture + noise * normal(random);
    for (let j = 0; j < cols; j += 1) {
      const wavelength = j / (cols - 1);
      const broadBand = (0.50 + 0.22 * chemistry) * gaussian(wavelength, 0.42, 0.060);
      const narrowBand = (0.28 - 0.10 * moisture) * gaussian(wavelength, 0.69, 0.035);
      const shoulder = 0.14 * chemistry * gaussian(wavelength, 0.78, 0.075);
      X[i * cols + j] = 0.62 + offset + slope * (wavelength - 0.5)
        + broadBand + narrowBand + shoulder + noise * normal(random);
    }
  }

  const split = (data, start, count) => {
    const out = new Float64Array(count * cols);
    out.set(data.subarray(start * cols, (start + count) * cols));
    return out;
  };
  return {
    cols,
    trainX: split(X, 0, trainRows),
    trainY: y.slice(0, trainRows),
    testX: split(X, trainRows, rows - trainRows),
    testY: y.slice(trainRows),
    trainRows,
    testRows: rows - trainRows,
  };
}

function metrics(actual, predicted) {
  const mean = actual.reduce((sum, value) => sum + value, 0) / actual.length;
  let squaredError = 0;
  let total = 0;
  for (let i = 0; i < actual.length; i += 1) {
    squaredError += (actual[i] - predicted[i]) ** 2;
    total += (actual[i] - mean) ** 2;
  }
  return {
    rmse: Math.sqrt(squaredError / actual.length),
    r2: 1 - squaredError / total,
  };
}

function svgElement(name, attributes = {}) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", name);
  Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, value));
  return node;
}

function drawChart(actual, aom, pls) {
  const svg = byId("prediction-chart");
  svg.replaceChildren();
  const width = 720;
  const height = 390;
  const margin = { left: 62, right: 28, top: 24, bottom: 54 };
  const values = [...actual, ...aom, ...pls];
  const rawMin = Math.min(...values);
  const rawMax = Math.max(...values);
  const pad = Math.max((rawMax - rawMin) * 0.08, 0.05);
  const min = rawMin - pad;
  const max = rawMax + pad;
  const x = (value) => margin.left + (value - min) / (max - min) * (width - margin.left - margin.right);
  const y = (value) => height - margin.bottom - (value - min) / (max - min) * (height - margin.top - margin.bottom);

  for (let i = 0; i <= 4; i += 1) {
    const value = min + i * (max - min) / 4;
    const gx = x(value);
    const gy = y(value);
    svg.append(svgElement("line", { x1: gx, y1: margin.top, x2: gx, y2: height - margin.bottom, class: "grid" }));
    svg.append(svgElement("line", { x1: margin.left, y1: gy, x2: width - margin.right, y2: gy, class: "grid" }));
    const tx = svgElement("text", { x: gx, y: height - margin.bottom + 25, class: "tick", "text-anchor": "middle" });
    tx.textContent = value.toFixed(1);
    svg.append(tx);
    const ty = svgElement("text", { x: margin.left - 13, y: gy + 4, class: "tick", "text-anchor": "end" });
    ty.textContent = value.toFixed(1);
    svg.append(ty);
  }
  svg.append(svgElement("line", { x1: x(min), y1: y(min), x2: x(max), y2: y(max), class: "diagonal" }));

  const addPoints = (predicted, className) => {
    predicted.forEach((value, i) => svg.append(svgElement("circle", {
      cx: x(actual[i]), cy: y(value), r: 5.2, class: className,
    })));
  };
  addPoints(pls, "point pls");
  addPoints(aom, "point aom");

  const xLabel = svgElement("text", { x: (margin.left + width - margin.right) / 2, y: height - 12, class: "axis-label", "text-anchor": "middle" });
  xLabel.textContent = "Measured response";
  svg.append(xLabel);
  const yLabel = svgElement("text", { x: 17, y: height / 2, class: "axis-label", transform: `rotate(-90 17 ${height / 2})`, "text-anchor": "middle" });
  yLabel.textContent = "Predicted response";
  svg.append(yLabel);

  [["AOM-PLS", "legend-aom"], ["Plain PLS", "legend-pls"]].forEach(([label, className], index) => {
    const cx = width - 155;
    const cy = 42 + index * 24;
    svg.append(svgElement("circle", { cx, cy, r: 5, class: className }));
    const text = svgElement("text", { x: cx + 13, y: cy + 4, class: "legend" });
    text.textContent = label;
    svg.append(text);
  });
}

async function runDemo() {
  const button = byId("run");
  button.disabled = true;
  button.textContent = "Fitting…";
  byId("run-note").textContent = "Screening the strict-linear bank inside WASM…";
  await Promise.resolve();

  try {
    const noise = Number(byId("noise").value);
    const components = Number(byId("components").value);
    const folds = Number(byId("folds").value);
    const data = syntheticNir(noise);
    const trainX = { data: data.trainX, rows: data.trainRows, cols: data.cols };
    const trainY = { data: data.trainY, rows: data.trainRows, cols: 1 };
    const testX = { data: data.testX, rows: data.testRows, cols: data.cols };

    const started = performance.now();
    const aomModel = fitAom(trainX, trainY, components, folds, 0);
    const aomPred = predictModel(aomModel, testX).data;
    const elapsed = performance.now() - started;
    const plsModel = fitPls(trainX, trainY, components);
    const plsPred = predictPls(plsModel, testX).data;
    const aomStats = metrics(data.testY, aomPred);
    const plsStats = metrics(data.testY, plsPred);

    const operator = operatorNames[aomModel.selectedOperator] ?? `Bank entry ${aomModel.selectedOperator}`;
    byId("operator").textContent = operator;
    byId("operator-index").textContent = `global bank index ${aomModel.selectedOperator} · CV score ${aomModel.score.toFixed(4)}`;
    byId("aom-rmse").textContent = aomStats.rmse.toFixed(4);
    byId("aom-r2").textContent = `R² ${aomStats.r2.toFixed(3)} on ${data.testRows} held-out rows`;
    byId("pls-rmse").textContent = plsStats.rmse.toFixed(4);
    byId("fit-time").textContent = elapsed < 0.1 ? "<0.1 ms" : `${elapsed.toFixed(1)} ms`;
    byId("run-note").textContent = `${data.trainRows} training spectra × ${data.cols} wavelengths; raw-spectrum prediction.`;
    drawChart(data.testY, aomPred, plsPred);
  } catch (error) {
    console.error(error);
    byId("run-note").textContent = `Fit failed: ${error.message}`;
  } finally {
    button.disabled = false;
    button.textContent = "Run AOM-PLS";
  }
}

byId("noise").addEventListener("input", (event) => {
  byId("noise-value").textContent = Number(event.target.value).toFixed(3);
});
byId("run").addEventListener("click", runDemo);

try {
  await loadModule();
  const abi = abiVersion().join(".");
  byId("runtime-status").textContent = "WebAssembly ready";
  byId("runtime-version").textContent = `n4m ${version()} · ABI ${abi}`;
  byId("runtime-dot").classList.replace("loading", "ready");
  byId("run").disabled = false;
  await runDemo();
} catch (error) {
  console.error(error);
  byId("runtime-status").textContent = "WebAssembly failed to load";
  byId("runtime-version").textContent = location.protocol === "file:"
    ? "Serve this directory over HTTP; browsers block WASM from file:// URLs."
    : error.message;
  byId("runtime-dot").classList.replace("loading", "error");
}
