const ENDPOINTS = ["herg", "dili", "ames"];
const RING_CIRCUMFERENCE = 2 * Math.PI * 54;

const EXAMPLES = [
  { name: "Aspirin", note: "analgesic", smiles: "CC(=O)Oc1ccccc1C(=O)O" },
  { name: "Caffeine", note: "xanthine", smiles: "Cn1cnc2c1c(=O)n(C)c(=O)n2C" },
  { name: "Paracetamol", note: "analgesic", smiles: "CC(=O)Nc1ccc(O)cc1" },
  { name: "Terfenadine", note: "hERG blocker", smiles: "CC(C)(C)c1ccc(cc1)C(O)CCCN2CCC(CC2)C(O)(c3ccccc3)c4ccccc4" },
  { name: "Astemizole", note: "hERG blocker", smiles: "COc1ccc(cc1)CCN2CCC(CC2)Nc3ncnc4ccccc34" },
  { name: "Imatinib", note: "kinase inhibitor", smiles: "Cc1ccc(NC(=O)c2ccc(CN3CCN(C)CC3)cc2)cc1Nc4nccc(n4)c5cccnc5" },
  { name: "Ibuprofen", note: "NSAID", smiles: "CC(C)Cc1ccc(cc1)C(C)C(=O)O" },
  { name: "Sildenafil", note: "PDE5 inhibitor", smiles: "CCCC1NN(C)C(=O)c2[nH]c(cc12)c3ccc(cc3)S(=O)(=O)N4CCN(C)CC4" },
];

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

const ui = {
  smiles: $("#smiles"),
  predict: $("#predict"),
  surprise: $("#surprise"),
  examples: $("#examples"),
  structure: $("#structure"),
  structureEmpty: $("#structure-empty"),
  structureStatus: $("#structure-status"),
  inputError: $("#input-error"),
  resultStatus: $("#result-status"),
  batchSmiles: $("#batch-smiles"),
  batchRun: $("#batch-run"),
  batchCount: $("#batch-count"),
  batchStatus: $("#batch-status"),
  batchBody: $("#batch-body"),
  batchEmpty: $("#batch-empty"),
  toast: $("#toast"),
};

let structureTimer = null;
let structureRequest = null;
let structureUrl = null;
let metadata = null;
let predicting = false;
let toastTimer = null;

function clamp(value, low = 0, high = 1) {
  return Math.min(high, Math.max(low, value));
}

function formatProbability(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  const percent = clamp(Number(value)) * 100;
  return `${percent.toFixed(percent < 10 ? 2 : 1)}%`;
}

function formatTemperature(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(2) : "—";
}

function formatAuc(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(3) : "—";
}

function showToast(message, error = false) {
  ui.toast.textContent = message;
  ui.toast.classList.toggle("error", error);
  ui.toast.classList.add("visible");
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => ui.toast.classList.remove("visible"), 3600);
}

function setInputError(message = "") {
  ui.inputError.textContent = message;
  ui.inputError.classList.toggle("visible", Boolean(message));
}

function setResultStatus(text, mode = "idle") {
  ui.resultStatus.textContent = text;
  ui.resultStatus.className = `status-${mode}`;
}

function setLoading(loading) {
  predicting = loading;
  ui.predict.disabled = loading;
  ui.predict.querySelector("span").textContent = loading ? "Reading…" : "Predict";
  $$(".result-card").forEach((card) => card.classList.toggle("is-loading", loading));
  if (loading) setResultStatus("building ensemble · cpu", "busy");
}

function renderExamples() {
  EXAMPLES.forEach((example, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "chip";
    button.title = example.smiles;
    const name = document.createElement("span");
    name.textContent = example.name;
    const formula = document.createElement("span");
    formula.className = "chip-formula";
    formula.textContent = example.note;
    button.append(name, formula);
    button.addEventListener("click", () => {
      ui.smiles.value = example.smiles;
      setInputError();
      scheduleStructure(example.smiles);
      ui.smiles.focus();
      runPrediction({ silent: true });
    });
    ui.examples.append(button);
  });
}

function setStructureValid(valid, message) {
  ui.structureStatus.textContent = message;
  ui.structureStatus.classList.toggle("valid", valid);
  ui.structureStatus.classList.toggle("invalid", !valid);
}

function scheduleStructure(smiles) {
  window.clearTimeout(structureTimer);
  structureTimer = window.setTimeout(() => loadStructure(smiles), 420);
}

async function loadStructure(smiles) {
  const value = smiles.trim();
  if (structureRequest) structureRequest.abort();
  if (!value) {
    setStructureValid(false, "empty");
    ui.structure.hidden = true;
    ui.structureEmpty.hidden = false;
    return;
  }

  setStructureValid(false, "sketching…");
  structureRequest = new AbortController();
  const params = new URLSearchParams({ smiles: value, size: "420" });
  try {
    const response = await fetch(`/molecule.png?${params}`, {
      signal: structureRequest.signal,
    });
    if (!response.ok) throw new Error("invalid structure");
    const blob = await response.blob();
    if (structureUrl) URL.revokeObjectURL(structureUrl);
    structureUrl = URL.createObjectURL(blob);
    ui.structure.src = structureUrl;
    ui.structure.hidden = false;
    ui.structureEmpty.hidden = true;
    setStructureValid(true, "valid smiles");
  } catch (error) {
    if (error.name === "AbortError") return;
    ui.structure.hidden = true;
    ui.structureEmpty.hidden = false;
    setStructureValid(false, "invalid smiles");
  }
}

function applyMetadata() {
  if (!metadata) return;
  ENDPOINTS.forEach((endpoint) => {
    const info = metadata.endpoints[endpoint];
    if (!info) return;
    const card = $(`.result-card[data-endpoint="${endpoint}"]`);
    if (!card) return;
    $('[data-role="temp"]', card).textContent = formatTemperature(info.temperature);
    $('[data-role="auc"]', card).textContent = formatAuc(info.test_auc);
  });
}

async function fetchMetadata() {
  try {
    const response = await fetch("/metadata", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    metadata = await response.json();
    applyMetadata();
  } catch (error) {
    showToast("Could not load calibration metadata.", true);
  }
}

function renderCard(endpoint, row) {
  const card = $(`.result-card[data-endpoint="${endpoint}"]`);
  if (!card || !row) return;
  const raw = clamp(Number(row[`${endpoint}_raw_prob`]));
  const calibrated = clamp(Number(row[`${endpoint}_prob`]));
  const high = calibrated >= 0.5;

  const ringFill = $(".ring-fill", card);
  ringFill.style.strokeDashoffset = String(RING_CIRCUMFERENCE * (1 - calibrated));
  $('[data-role="prob"]', card).textContent = formatProbability(calibrated);
  $('[data-role="raw"]', card).textContent = formatProbability(raw);
  $('[data-role="cal"]', card).textContent = formatProbability(calibrated);
  $('[data-role="raw-bar"]', card).style.width = `${raw * 100}%`;
  $('[data-role="cal-bar"]', card).style.width = `${calibrated * 100}%`;

  const flag = $('[data-role="flag"]', card);
  flag.textContent = high ? "HIGH" : "LOW";
  flag.classList.toggle("high", high);
  flag.classList.toggle("low", !high);
  flag.title = high ? "Calibrated risk at or above 0.50" : "Calibrated risk below 0.50";

  card.classList.remove("is-ready");
  void card.offsetWidth;
  card.classList.add("is-ready");
}

async function runPrediction({ silent = false } = {}) {
  if (predicting) return;
  const smiles = ui.smiles.value.trim();
  setInputError();
  if (!smiles) {
    setInputError("Enter a SMILES string first.");
    ui.smiles.focus();
    return;
  }

  setLoading(true);
  const started = performance.now();
  try {
    const response = await fetch("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ smiles: [smiles] }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || "Prediction failed.");
    }
    const row = payload.predictions && payload.predictions[0];
    if (!row) throw new Error("No prediction returned.");
    ENDPOINTS.forEach((endpoint) => renderCard(endpoint, row));
    const seconds = ((performance.now() - started) / 1000).toFixed(1);
    setResultStatus(`calibrated · ${seconds}s`, "ready");
    if (!silent) showToast("Seed ensemble scored in the browser session.");
  } catch (error) {
    setResultStatus("check input", "error");
    setInputError(error.message || "Prediction failed.");
    if (!silent) showToast(error.message || "Prediction failed.", true);
  } finally {
    setLoading(false);
  }
}

function randomExample() {
  const current = ui.smiles.value.trim();
  const choices = EXAMPLES.filter((example) => example.smiles !== current);
  const example = choices[Math.floor(Math.random() * choices.length)];
  ui.smiles.value = example.smiles;
  setInputError();
  scheduleStructure(example.smiles);
  runPrediction({ silent: true });
  showToast(`${example.name} · ${example.note}`);
}

function updateBatchCount() {
  const lines = ui.batchSmiles.value.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  ui.batchCount.textContent = `${lines.length} / 50`;
  ui.batchCount.style.color = lines.length > 50 ? "var(--danger)" : "";
}

function makeCell(text, className = "") {
  const cell = document.createElement("td");
  cell.textContent = text;
  if (className) cell.className = className;
  return cell;
}

function renderBatch(predictions, invalid, originalLines) {
  ui.batchBody.replaceChildren();
  predictions.forEach((row) => {
    const tr = document.createElement("tr");
    tr.append(makeCell(row.smiles, "molecule"));
    ENDPOINTS.forEach((endpoint) => {
      const probability = clamp(Number(row[`${endpoint}_prob`]));
      tr.append(makeCell(formatProbability(probability), endpoint));
    });
    tr.title = row.smiles;
    ui.batchBody.append(tr);
  });
  invalid.forEach((row) => {
    const original = originalLines[row.row_index] || row.smiles || "(empty)";
    const tr = document.createElement("tr");
    tr.append(makeCell(original, "molecule"));
    const cell = makeCell("not a valid SMILES", "invalid");
    cell.colSpan = 3;
    tr.append(cell);
    tr.title = original;
    ui.batchBody.append(tr);
  });
  ui.batchEmpty.hidden = predictions.length + invalid.length > 0;
}

async function runBatch() {
  const originalLines = ui.batchSmiles.value.split(/\r?\n/).map((line) => line.trim());
  const lines = originalLines.filter(Boolean);
  if (!lines.length) {
    showToast("Add at least one SMILES string.", true);
    ui.batchSmiles.focus();
    return;
  }
  if (lines.length > 50) {
    showToast("Batch mode accepts up to 50 molecules.", true);
    return;
  }

  ui.batchRun.disabled = true;
  ui.batchRun.textContent = "Scoring…";
  ui.batchStatus.textContent = "building ensemble…";
  ui.batchStatus.className = "structure-status";
  try {
    const response = await fetch("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ smiles: lines }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.detail || "Batch prediction failed.");
    const predictions = payload.predictions || [];
    const invalid = payload.invalid || [];
    renderBatch(predictions, invalid, lines);
    ui.batchStatus.textContent = `${predictions.length} valid${invalid.length ? ` · ${invalid.length} invalid` : ""}`;
    ui.batchStatus.classList.add(invalid.length ? "invalid" : "valid");
  } catch (error) {
    ui.batchBody.replaceChildren();
    ui.batchEmpty.hidden = false;
    ui.batchStatus.textContent = "batch failed";
    ui.batchStatus.className = "structure-status invalid";
    showToast(error.message || "Batch prediction failed.", true);
  } finally {
    ui.batchRun.disabled = false;
    ui.batchRun.textContent = "Run batch";
  }
}

function bindEvents() {
  ui.predict.addEventListener("click", () => runPrediction());
  ui.surprise.addEventListener("click", randomExample);
  ui.batchRun.addEventListener("click", runBatch);
  ui.batchSmiles.addEventListener("input", updateBatchCount);

  let inputTimer = null;
  ui.smiles.addEventListener("input", () => {
    setInputError();
    window.clearTimeout(inputTimer);
    inputTimer = window.setTimeout(() => {
      if (structureRequest) structureRequest.abort();
      loadStructure(ui.smiles.value);
    }, 420);
  });

  ui.smiles.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      runPrediction();
    }
  });

  ui.structure.addEventListener("error", () => {
    ui.structure.hidden = true;
    ui.structureEmpty.hidden = false;
    setStructureValid(false, "render failed");
  });
}

async function init() {
  renderExamples();
  bindEvents();
  updateBatchCount();
  scheduleStructure(ui.smiles.value);
  await fetchMetadata();
  await runPrediction({ silent: true });
}

init();
