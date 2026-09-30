const scenarioButtons = [...document.querySelectorAll(".scenario")];
const graph = document.getElementById("graph");
const edges = document.getElementById("edges");
const log = document.getElementById("event-log");
const phoneContent = document.getElementById("phone-content");
const phoneNotice = document.getElementById("phone-notice");
const auditBox = document.getElementById("audit");
const phonePlaceholder = phoneContent.firstElementChild.cloneNode(true);

let stream = null;
let runSerial = 0;
let received = 0;
let total = 0;
let insightCount = 0;
let phoneAction = null;
let nodes = new Map();
let removalTimers = new Set();
let redrawFrame = 0;

function setStatus(label, type) {
  const element = document.getElementById("run-status");
  element.textContent = label;
  element.className = "status " + (type || "");
}

function setFocus(title, detail) {
  document.getElementById("focus-title").textContent = title;
  document.getElementById("focus-detail").textContent = detail;
}

function setRole(lane) {
  document.querySelectorAll(".role-card").forEach(card => {
    card.classList.toggle("active", card.dataset.role === lane);
  });
}

function updateProgress() {
  document.getElementById("progress-label").textContent =
    Math.min(received, total) + " / " + total;
  document.getElementById("progress-fill").style.width =
    total ? Math.min(100, received / total * 100) + "%" : "0%";
  document.getElementById("event-count").textContent =
    String(received).padStart(2, "0");
}

function updateActive() {
  const count = [...nodes.values()].filter(node => !node.classList.contains("done")).length;
  document.getElementById("active-label").textContent =
    count + " agents working";
}

function addLog(title, detail) {
  if (log.children.length === 1 && log.firstElementChild.textContent === "Waiting for the first event.") {
    log.replaceChildren();
  }
  const item = document.createElement("li");
  const strong = document.createElement("strong");
  strong.textContent = title;
  const body = document.createElement("span");
  body.textContent = detail;
  item.append(strong, body);
  log.prepend(item);
  while (log.children.length > 6) log.lastElementChild.remove();
}

function redrawSoon() {
  cancelAnimationFrame(redrawFrame);
  redrawFrame = requestAnimationFrame(drawEdges);
}

function drawEdges() {
  const bounds = graph.getBoundingClientRect();
  edges.setAttribute("viewBox", "0 0 " + graph.clientWidth + " " + graph.clientHeight);
  edges.replaceChildren();
  for (const target of nodes.values()) {
    if (target.classList.contains("leaving")) continue;
    const dependencies = (target.dataset.depends || "").split(",").filter(Boolean);
    for (const id of dependencies) {
      const origin = nodes.get(id);
      if (!origin || origin.classList.contains("leaving")) continue;
      const start = origin.getBoundingClientRect();
      const end = target.getBoundingClientRect();
      let pathData = "";
      if (end.left > start.right) {
        const x1 = start.right - bounds.left;
        const y1 = start.top + start.height / 2 - bounds.top;
        const x2 = end.left - bounds.left;
        const y2 = end.top + end.height / 2 - bounds.top;
        const bend = Math.max(18, (x2 - x1) * .44);
        pathData = "M " + x1 + " " + y1 + " C " +
          (x1 + bend) + " " + y1 + ", " + (x2 - bend) + " " + y2 +
          ", " + x2 + " " + y2;
      } else if (end.top > start.bottom) {
        const x1 = start.right - bounds.left - 10;
        const y1 = start.bottom - bounds.top;
        const x2 = end.right - bounds.left - 10;
        const y2 = end.top - bounds.top;
        pathData = "M " + x1 + " " + y1 + " C " +
          (x1 + 22) + " " + y1 + ", " + (x2 + 22) + " " + y2 +
          ", " + x2 + " " + y2;
      }
      if (!pathData) continue;
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("d", pathData);
      path.setAttribute("class", "edge" + (target.classList.contains("done") ? " done" : ""));
      edges.append(path);
    }
  }
}

function startAgent(event) {
  const list = document.querySelector('.lane[data-lane="' + event.lane + '"] .node-list');
  if (!list) return;
  const card = document.createElement("article");
  card.className = "agent-node";
  card.dataset.id = event.id;
  card.dataset.lane = event.lane;
  card.dataset.depends = event.depends.join(",");
  const type = document.createElement("span");
  type.className = "node-type";
  type.textContent = {
    super: "SUPER AGENT", boss: "BOSS AGENT",
    worker: "WORKER AGENT", supervisor: "SUPERVISOR"
  }[event.lane];
  const name = document.createElement("strong");
  name.className = "node-name";
  name.textContent = event.name;
  const task = document.createElement("span");
  task.className = "node-task";
  task.textContent = event.task;
  const dot = document.createElement("span");
  dot.className = "node-indicator";
  dot.setAttribute("aria-hidden", "true");
  card.append(type, name, task, dot);
  list.append(card);
  nodes.set(event.id, card);
  document.getElementById("graph-empty").classList.add("hidden");
  requestAnimationFrame(() => {
    card.classList.add("visible");
    redrawSoon();
  });
  setRole(event.lane);
  setFocus(event.name + " is working", event.task);
  addLog(event.name + " started", event.task);
  updateActive();
}

function finishAgent(event) {
  const card = nodes.get(event.id);
  if (!card || card.classList.contains("done")) return;
  card.classList.add("done");
  card.querySelector(".node-task").textContent = event.result;
  setRole(card.dataset.lane);
  setFocus(card.querySelector(".node-name").textContent + " is complete", event.result);
  addLog(card.querySelector(".node-name").textContent + " finished", event.result);
  updateActive();
  redrawSoon();

  const holdTimer = setTimeout(() => {
    card.classList.add("leaving");
    redrawSoon();
    const fadeTimer = setTimeout(() => {
      card.remove();
      nodes.delete(event.id);
      removalTimers.delete(fadeTimer);
      redrawSoon();
    }, 700);
    removalTimers.add(fadeTimer);
    removalTimers.delete(holdTimer);
  }, 1700);
  removalTimers.add(holdTimer);
}

function addInsight(event) {
  const list = document.getElementById("insight-list");
  list.querySelector(".insight-empty")?.remove();
  const card = document.createElement("article");
  card.className = "insight-card";
  const source = document.createElement("span");
  source.textContent = event.source;
  const title = document.createElement("strong");
  title.textContent = event.title;
  const detail = document.createElement("p");
  detail.textContent = event.detail;
  card.append(source, title, detail);
  list.append(card);
  insightCount++;
  document.getElementById("insight-count").textContent = insightCount + " items";
  setFocus(event.title, event.detail);
  addLog("Decision · " + event.title, event.detail);
}

function setPhoneScene(scene) {
  document.getElementById("phone-scene").textContent = scene;
  const match = scene.match(/\b\d{1,2}:\d{2}\b/);
  if (match) document.getElementById("phone-clock").textContent = match[0];
}

function clearPhoneNotice() {
  phoneNotice.hidden = true;
  phoneNotice.replaceChildren();
}

function phonePrompt(event) {
  phoneAction = event.action_id;
  setPhoneScene(event.scene);
  clearPhoneNotice();
  const card = document.createElement("div");
  card.className = "phone-card";
  const kicker = document.createElement("span");
  kicker.className = "phone-card-kicker";
  kicker.textContent = "A reminder from Relay";
  const title = document.createElement("h4");
  title.textContent = event.title;
  const body = document.createElement("p");
  body.textContent = event.body;
  const button = document.createElement("button");
  button.className = "phone-action";
  button.type = "button";
  button.textContent = event.button;
  button.setAttribute("aria-label", "Automatic simulated tap: " + event.button);
  const hint = document.createElement("span");
  hint.className = "phone-action-hint";
  hint.textContent = "Simulated user tap coming up";
  card.append(kicker, title, body, button, hint);
  phoneContent.replaceChildren(card);
  setFocus("Phone prompt · " + event.title, event.body);
  addLog("Phone prompt shown", event.title);
}

function phoneTap(event) {
  if (phoneAction !== event.action_id) return;
  const button = phoneContent.querySelector(".phone-action");
  if (!button) return;
  const actionText = button.textContent;
  button.classList.add("tapped");
  button.textContent = "✓ Tapped";
  const hint = phoneContent.querySelector(".phone-action-hint");
  if (hint) hint.textContent = "Simulated user confirmed";
  setRole(null);
  setFocus("Simulated user tapped the phone", actionText);
  addLog("User tap", actionText);
}

function makePhoneItem(item) {
  const row = document.createElement("div");
  row.className = "phone-item";
  row.dataset.itemId = item.id;
  const box = document.createElement("span");
  box.className = "phone-checkbox";
  box.setAttribute("aria-hidden", "true");
  const text = document.createElement("div");
  const title = document.createElement("strong");
  title.textContent = item.label;
  const detail = document.createElement("small");
  detail.textContent = item.detail;
  text.append(title, detail);
  row.append(box, text);
  return row;
}

function updatePhoneCount() {
  const current = [...phoneContent.querySelectorAll(".phone-item:not(.unavailable)")];
  const checked = current.filter(item => item.classList.contains("checked")).length;
  const counter = phoneContent.querySelector(".phone-count");
  if (counter) counter.textContent = "Checked " + checked + " / " + current.length;
}

function phoneChecklist(event) {
  phoneAction = null;
  setPhoneScene(event.scene);
  clearPhoneNotice();
  const container = document.createElement("div");
  const head = document.createElement("div");
  head.className = "phone-checklist-head";
  const title = document.createElement("h4");
  title.textContent = event.title;
  const body = document.createElement("p");
  body.textContent = event.body;
  const count = document.createElement("span");
  count.className = "phone-count";
  head.append(title, body, count);
  const items = document.createElement("div");
  items.className = "phone-items";
  event.items.forEach(item => items.append(makePhoneItem(item)));
  container.append(head, items);
  phoneContent.replaceChildren(container);
  updatePhoneCount();
  setRole("worker");
  setFocus("Phone checklist · " + event.title, event.body);
  addLog("Phone checklist generated", event.title + ", " + event.items.length + " items");
}

function phoneCheck(event) {
  const row = [...phoneContent.querySelectorAll(".phone-item")]
    .find(item => item.dataset.itemId === event.item_id);
  if (!row || row.classList.contains("checked")) return;
  row.classList.add("checked", "just-checked");
  row.querySelector(".phone-checkbox").textContent = "✓";
  updatePhoneCount();
  row.scrollIntoView({ block: "nearest", behavior: "smooth" });
  const timer = setTimeout(() => {
    row.classList.remove("just-checked");
    removalTimers.delete(timer);
  }, 450);
  removalTimers.add(timer);
  const label = row.querySelector("strong").textContent;
  setRole(null);
  setFocus("Simulated user checked an item", label);
  addLog("Checklist item checked", label);
}

function phoneReplace(event) {
  const old = [...phoneContent.querySelectorAll(".phone-item")]
    .find(item => item.dataset.itemId === event.old_id);
  if (!old) return;
  old.classList.add("unavailable");
  old.querySelector(".phone-checkbox").textContent = "×";
  const list = phoneContent.querySelector(".phone-items");
  const fresh = makePhoneItem({
    id: event.new_id, label: event.label, detail: event.detail
  });
  list.append(fresh);
  updatePhoneCount();
  fresh.scrollIntoView({ block: "nearest", behavior: "smooth" });
  setFocus("Checklist updated", event.label + " replaces the unavailable item.");
  addLog("Checklist item replaced", event.label + " replaces the unavailable item.");
}

function showPhoneNotice(title, body) {
  phoneNotice.hidden = false;
  const strong = document.createElement("strong");
  strong.textContent = title;
  const text = document.createElement("span");
  text.textContent = body;
  phoneNotice.replaceChildren(strong, text);
}

function showAudit(event) {
  const passed = event.status === "passed";
  const count = event.checked + " / " + event.total;
  const missing = event.missing.length ? "Missing: " + event.missing.join(", ") : "All simulated confirmations are complete.";
  auditBox.className = "audit " + event.status;
  auditBox.querySelector("b").textContent = "Supervisor · " + event.title + " · " + count;
  auditBox.querySelector("span").textContent = missing;
  showPhoneNotice(
    passed ? "Supervisor passed · " + count : "Supervisor needs more · " + count,
    missing
  );
  setRole("supervisor");
  setFocus("Supervisor checks phone completion state", event.title + ": " + missing);
  addLog(passed ? "Supervisor check passed" : "Supervisor sent it back", event.title + " · " + count + "; " + missing);
}

function phoneEnd(event) {
  phoneAction = null;
  setPhoneScene(event.scene);
  clearPhoneNotice();
  const card = document.createElement("div");
  card.className = "phone-card";
  const kicker = document.createElement("span");
  kicker.className = "phone-card-kicker";
  kicker.textContent = "Today's result";
  const title = document.createElement("h4");
  title.textContent = event.title;
  const body = document.createElement("p");
  body.textContent = event.body;
  const lines = document.createElement("div");
  lines.className = "phone-finish-lines";
  event.lines.forEach(line => {
    const item = document.createElement("span");
    item.textContent = line;
    lines.append(item);
  });
  card.append(kicker, title, body, lines);
  phoneContent.replaceChildren(card);
  setFocus(event.title, event.body);
  addLog("Phone result shown", event.title);
}

function handleEvent(event) {
  if (event.kind !== "workflow_start" && event.kind !== "workflow_complete") {
    received++;
    updateProgress();
  }
  switch (event.kind) {
    case "workflow_start":
      total = event.total;
      updateProgress();
      document.getElementById("demo-heading").textContent = event.title;
      document.getElementById("demo-subtitle").textContent = event.subtitle;
      setFocus("Super Agent receives the goal", event.subtitle);
      addLog("Goal received", event.subtitle);
      break;
    case "agent_start": startAgent(event); break;
    case "agent_done": finishAgent(event); break;
    case "insight": addInsight(event); break;
    case "handoff":
      setFocus(event.title, event.detail);
      addLog(event.title, event.detail);
      break;
    case "phone_prompt": phonePrompt(event); break;
    case "phone_tap": phoneTap(event); break;
    case "phone_checklist": phoneChecklist(event); break;
    case "phone_check": phoneCheck(event); break;
    case "phone_replace": phoneReplace(event); break;
    case "phone_notice":
      showPhoneNotice(event.title, event.body);
      setFocus(event.title, event.body);
      addLog(event.title, event.body);
      break;
    case "audit": showAudit(event); break;
    case "phone_end": phoneEnd(event); break;
    case "workflow_complete":
      document.getElementById("progress-fill").style.width = "100%";
      setStatus("Complete", "done");
      setRole(null);
      addLog("Workflow complete", event.summary);
      stream?.close();
      stream = null;
      break;
  }
}

function reset() {
  stream?.close();
  stream = null;
  removalTimers.forEach(clearTimeout);
  removalTimers.clear();
  nodes.clear();
  document.querySelectorAll(".node-list").forEach(list => list.replaceChildren());
  edges.replaceChildren();
  document.getElementById("graph-empty").classList.add("hidden");
  received = 0;
  total = 0;
  insightCount = 0;
  phoneAction = null;
  updateProgress();
  updateActive();
  setRole(null);
  log.replaceChildren();
  document.getElementById("insight-list").replaceChildren();
  document.getElementById("insight-count").textContent = "0 items";
  auditBox.className = "audit idle";
  auditBox.querySelector("b").textContent = "Supervisor has not checked yet";
  auditBox.querySelector("span").textContent = "It will read simulated taps and checklist states from the phone.";
  document.getElementById("phone-clock").textContent = "12:40";
  setPhoneScene("Starting");
  clearPhoneNotice();
  phoneContent.replaceChildren(phonePlaceholder.cloneNode(true));
  setFocus("Starting the demo", "Agents and phone will begin updating together.");
}

function runWorkflow(id) {
  reset();
  runSerial++;
  const thisRun = runSerial;
  scenarioButtons.forEach(button => {
    button.classList.toggle("selected", button.dataset.workflow === id);
  });
  setStatus("Running", "running");
  stream = new EventSource("/api/workflows/" + encodeURIComponent(id) + "/stream");
  stream.addEventListener("workflow", message => {
    if (thisRun !== runSerial) return;
    try {
      handleEvent(JSON.parse(message.data));
    } catch (error) {
      console.error("Invalid workflow event", error);
    }
  });
  stream.onerror = () => {
    if (thisRun !== runSerial || !stream) return;
    stream.close();
    stream = null;
    setStatus("Connection lost", "error");
    setFocus("Event stream interrupted", "Check that FastAPI is running, then select the scenario again.");
  };
}

scenarioButtons.forEach(button => {
  button.addEventListener("click", () => runWorkflow(button.dataset.workflow));
});
window.addEventListener("resize", redrawSoon);
new ResizeObserver(redrawSoon).observe(graph);
