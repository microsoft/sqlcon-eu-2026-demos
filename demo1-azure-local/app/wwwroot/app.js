const queueElement = document.querySelector("#transfer-queue");
const queueCountElement = document.querySelector("#queue-count");
const detailElement = document.querySelector("#transfer-detail");
const detailTitleElement = document.querySelector("#detail-title");
const priorityElement = document.querySelector("#priority");
const briefingElement = document.querySelector("#briefing-content");
const refreshButton = document.querySelector("#refresh");
const statusText = document.querySelector("#system-status");
const statusDot = document.querySelector("#status-dot");

let selectedTransferNumber = null;

const api = async (url, options) => {
  const response = await fetch(url, options);
  if (!response.ok) {
    const problem = await response.json().catch(() => null);
    throw new Error(problem?.detail || problem?.title || `Request failed (${response.status})`);
  }
  return response.json();
};

const element = (tag, className, text) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
};

const formatValue = (value, unit) => value == null ? "Not recorded" : `${value}${unit ? ` ${unit}` : ""}`;
const formatDate = (value) => new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));

function setConnection(status, text) {
  statusDot.className = status;
  statusText.textContent = text;
}

function showError(target, message) {
  target.replaceChildren();
  const state = element("div", "empty-state error-state");
  state.append(element("strong", null, "Unable to load data"), element("span", null, message));
  target.append(state);
}

async function loadQueue() {
  refreshButton.disabled = true;
  try {
    const transfers = await api("/api/transfers");
    queueCountElement.textContent = transfers.length;
    queueElement.replaceChildren();

    for (const transfer of transfers) {
      const button = element("button", `transfer-card${transfer.transferNumber === selectedTransferNumber ? " active" : ""}`);
      button.type = "button";
      button.dataset.transferNumber = transfer.transferNumber;

      const eta = element("div", "eta", transfer.etaMinutes);
      eta.append(element("span", null, "MIN"));
      const content = element("div");
      content.append(
        element("div", "transfer-name", `${transfer.givenName} ${transfer.familyName} · ${transfer.age}`),
        element("div", "transfer-meta", `${transfer.transportUnit} → ${transfer.destinationName}\n${transfer.chiefConcern} · Priority ${transfer.priorityCode}`),
        element("span", `severity${transfer.priorityCode === 1 ? " critical" : ""}`, transfer.priorityCode === 1 ? "Immediate review" : transfer.transferStatus)
      );
      button.append(eta, content);
      button.addEventListener("click", () => selectTransfer(transfer.transferNumber));
      queueElement.append(button);
    }

    setConnection("connected", "Regional systems connected");
    if (!selectedTransferNumber && transfers.length > 0) await selectTransfer(transfers[0].transferNumber);
  } catch (error) {
    setConnection("failed", "Database unavailable");
    showError(queueElement, error.message);
  } finally {
    refreshButton.disabled = false;
  }
}

async function selectTransfer(transferNumber) {
  selectedTransferNumber = transferNumber;
  document.querySelectorAll(".transfer-card").forEach(card => {
    card.classList.toggle("active", card.dataset.transferNumber === transferNumber);
  });
  briefingElement.replaceChildren(createEmpty("Briefing pending", "Generate a draft after reviewing the transfer packet."));
  detailElement.replaceChildren(createLoading("Loading regional records"));

  try {
    const detail = await api(`/api/transfers/${encodeURIComponent(transferNumber)}`);
    renderDetail(detail);
  } catch (error) {
    showError(detailElement, error.message);
  }
}

function createLoading(text) {
  const state = element("div", "empty-state");
  state.append(element("div", "spinner"), element("strong", null, text));
  return state;
}

function createEmpty(title, text) {
  const state = element("div", "empty-state");
  state.append(element("strong", null, title), element("span", null, text));
  return state;
}

function renderDetail(detail) {
  const transfer = detail.transfer;
  detailTitleElement.textContent = transfer.encounterNumber;
  priorityElement.textContent = `P${transfer.priorityCode}`;
  detailElement.replaceChildren();

  const patientRow = element("div", "patient-row");
  const patient = element("div");
  patient.append(
    element("div", "patient-name", `${transfer.givenName} ${transfer.familyName}`),
    element("div", "patient-meta", `${transfer.age} years · MRN ${transfer.regionalRecordNumber}`)
  );
  const arrival = element("div", "arrival");
  arrival.append(
    element("strong", null, `ETA ${transfer.etaMinutes} minutes`),
    element("span", null, `${transfer.destinationName}${transfer.destinationBay ? ` · ${transfer.destinationBay}` : ""}`)
  );
  patientRow.append(patient, arrival);

  const vitals = element("div", "vitals");
  for (const observation of detail.observations) {
    const card = element("div", `vital${observation.isAlert ? " alert" : ""}`);
    card.append(
      element("span", null, observation.name),
      element("strong", null, formatValue(observation.textValue ?? observation.numericValue, observation.textValue ? null : observation.unit))
    );
    vitals.append(card);
  }

  const narrativeSection = element("section");
  narrativeSection.append(element("h3", null, "Paramedic narrative"));
  const narrative = detail.narratives[0];
  narrativeSection.append(element("p", "narrative", narrative?.text || "No field narrative received."));

  const signalSection = element("section");
  signalSection.append(element("h3", null, "Extracted signals"));
  const signals = element("div", "signals");
  for (const signal of detail.signals) {
    const chip = element("span", "signal");
    chip.append(element("strong", null, signal.type), document.createTextNode(signal.value));
    signals.append(chip);
  }
  if (detail.signals.length === 0) signals.append(element("span", "patient-meta", "Signals are extracted when a briefing is generated."));
  signalSection.append(signals);

  const facts = element("div", "facts");
  facts.append(
    createFact("Active allergies", detail.allergies.map(item => `${item.name}${item.reaction ? ` (${item.reaction})` : ""}`).join(" · ") || "None recorded"),
    createFact("Active medications", detail.medications.map(item => item.name).join(" · ") || "None recorded"),
    createFact("Recent encounter", detail.recentEncounters[0] ? `${detail.recentEncounters[0].type} · ${formatDate(detail.recentEncounters[0].startedAt)}` : "None recorded"),
    createFact("Transfer status", `${transfer.transferStatus}${transfer.receivingTeamNotifiedAt ? " · Receiving team notified" : ""}`)
  );

  const actions = element("div", "action-row");
  actions.append(element("span", "source-count", "Seven regional source groups available for grounding"));
  const generate = element("button", "primary", "Generate receiving briefing");
  generate.type = "button";
  generate.addEventListener("click", () => generateBriefing(generate));
  actions.append(generate);

  detailElement.append(patientRow, vitals, narrativeSection, signalSection, facts, actions);
}

function createFact(label, value) {
  const fact = element("div", "fact");
  fact.append(element("span", null, label), document.createTextNode(value));
  return fact;
}

async function generateBriefing(button) {
  button.disabled = true;
  button.textContent = "Generating…";
  briefingElement.replaceChildren(createLoading("Grounding records and running ReceivingBriefing 1.0"));
  try {
    const briefing = await api(`/api/transfers/${encodeURIComponent(selectedTransferNumber)}/briefings`, { method: "POST" });
    renderBriefing(briefing);
    button.textContent = "Regenerate briefing";
  } catch (error) {
    showError(briefingElement, error.message);
    button.textContent = "Try again";
  } finally {
    button.disabled = false;
  }
}

function renderBriefing(briefing) {
  briefingElement.replaceChildren();
  const banner = element("div", "ai-banner");
  banner.append(element("strong", null, "AI-generated draft · Clinician review required"));
  briefingElement.append(banner, element("p", "summary", briefing.summary));

  const keyContext = briefing.items.filter(item => item.sectionName === "KeyContext");
  const confirm = briefing.items.filter(item => item.sectionName === "ConfirmOnArrival");
  briefingElement.append(createBriefSection("Key context", keyContext), createBriefSection("Confirm on arrival", confirm, "confirm"));

  const provenance = element("div", "provenance");
  provenance.append(element("p", null, `Briefing ${briefing.briefingId} · ${briefing.modelId} · ${briefing.durationMs.toLocaleString()} ms · ${briefing.reviewStatus}`));
  const sourceList = element("div", "source-list");
  for (const source of briefing.sources) sourceList.append(element("span", null, source.type));
  provenance.append(sourceList);
  briefingElement.append(provenance);
}

function createBriefSection(title, items, modifier = "") {
  const section = element("section", `brief-section ${modifier}`.trim());
  section.append(element("h3", null, title));
  const list = element("ul");
  for (const item of items) list.append(element("li", null, item.text));
  section.append(list);
  return section;
}

refreshButton.addEventListener("click", loadQueue);
loadQueue();