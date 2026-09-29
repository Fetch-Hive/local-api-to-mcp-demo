(() => {
  "use strict";

  const POLL_INTERVAL_MS = 2000;
  const HIGHLIGHT_MS = readHighlightMs();

  const PRIORITY_LABELS = { low: "Low", medium: "Medium", high: "High" };
  const STATUS_LABELS = {
    open: "Open",
    in_progress: "In progress",
    resolved: "Resolved",
  };

  const els = {
    loading: document.querySelector("#loading"),
    error: document.querySelector("#error"),
    empty: document.querySelector("#empty"),
    tableWrap: document.querySelector("#table-wrap"),
    rows: document.querySelector("#issue-rows"),
    live: document.querySelector("#live"),
    counts: {
      total: document.querySelector("#count-total"),
      open: document.querySelector("#count-open"),
      in_progress: document.querySelector("#count-in-progress"),
      resolved: document.querySelector("#count-resolved"),
    },
  };

  let knownIds = new Set();
  let loaded = false;
  let inFlight = false;

  function readHighlightMs() {
    const raw = getComputedStyle(document.documentElement)
      .getPropertyValue("--highlight-ms")
      .trim();
    const value = Number.parseFloat(raw);
    return Number.isFinite(value) ? value : 2800;
  }

  function formatTime(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(date);
  }

  function setBadge(span, kind, value) {
    const labels = kind === "priority" ? PRIORITY_LABELS : STATUS_LABELS;
    span.className = `badge ${kind}-${value}`;
    span.dataset.kind = kind;
    span.textContent = labels[value] || value;
  }

  function badge(kind, value) {
    const span = document.createElement("span");
    setBadge(span, kind, value);
    return span;
  }

  function buildRow(issue, isNew) {
    const row = document.createElement("tr");
    row.dataset.id = String(issue.id);
    if (isNew) {
      row.classList.add("is-new");
      window.setTimeout(() => row.classList.remove("is-new"), HIGHLIGHT_MS);
    }

    const titleCell = document.createElement("td");
    const titleText = document.createElement("span");
    titleText.className = "title-text";
    titleText.textContent = issue.title;
    const flag = document.createElement("span");
    flag.className = "new-flag";
    flag.textContent = "New";
    titleCell.append(titleText, flag);

    const priorityCell = document.createElement("td");
    priorityCell.append(badge("priority", issue.priority));
    const statusCell = document.createElement("td");
    statusCell.append(badge("status", issue.status));

    const timeCell = document.createElement("td");
    timeCell.className = "created";
    const time = document.createElement("time");
    time.dateTime = issue.created_at;
    time.textContent = formatTime(issue.created_at);
    timeCell.append(time);

    row.append(titleCell, priorityCell, statusCell, timeCell);
    return row;
  }

  function updateRow(row, issue) {
    row.querySelector(".title-text").textContent = issue.title;
    setBadge(row.children[1].querySelector(".badge"), "priority", issue.priority);
    setBadge(row.children[2].querySelector(".badge"), "status", issue.status);
    const time = row.querySelector("time");
    time.dateTime = issue.created_at;
    time.textContent = formatTime(issue.created_at);
  }

  function sync(issues) {
    const fresh = [];
    if (loaded) {
      for (const issue of issues) {
        if (!knownIds.has(issue.id)) fresh.push(issue);
      }
    }

    const existing = new Map(
      [...els.rows.querySelectorAll("tr")].map((row) => [row.dataset.id, row]),
    );
    const nextIds = new Set(issues.map((issue) => String(issue.id)));
    for (const [id, row] of existing) {
      if (!nextIds.has(id)) row.remove();
    }

    issues.forEach((issue, index) => {
      const id = String(issue.id);
      let row = existing.get(id);
      const isNew = fresh.some((item) => item.id === issue.id);
      if (!row) {
        row = buildRow(issue, isNew);
      } else {
        updateRow(row, issue);
      }
      const anchor = els.rows.children[index] || null;
      if (anchor !== row) els.rows.insertBefore(row, anchor);
    });

    knownIds = new Set(issues.map((issue) => issue.id));
    loaded = true;

    const counts = { total: issues.length, open: 0, in_progress: 0, resolved: 0 };
    for (const issue of issues) {
      if (issue.status in counts) counts[issue.status] += 1;
    }
    els.counts.total.textContent = String(counts.total);
    els.counts.open.textContent = String(counts.open);
    els.counts.in_progress.textContent = String(counts.in_progress);
    els.counts.resolved.textContent = String(counts.resolved);

    const isEmpty = issues.length === 0;
    els.empty.hidden = !isEmpty;
    els.tableWrap.hidden = isEmpty;
    els.loading.hidden = true;
    els.error.hidden = true;

    if (fresh.length === 1) {
      els.live.textContent = `New issue: ${fresh[0].title}`;
    } else if (fresh.length > 1) {
      els.live.textContent = `${fresh.length} new issues`;
    }
  }

  async function refresh() {
    if (inFlight) return;
    inFlight = true;
    try {
      const response = await fetch("/api/issues", {
        headers: { Accept: "application/json" },
        cache: "no-store",
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const issues = await response.json();
      if (!Array.isArray(issues)) throw new Error("Expected a list of issues.");
      sync(issues);
    } catch (_error) {
      els.loading.hidden = true;
      els.error.hidden = false;
      if (!loaded) {
        els.tableWrap.hidden = true;
        els.empty.hidden = true;
      }
    } finally {
      inFlight = false;
    }
  }

  refresh();
  window.setInterval(refresh, POLL_INTERVAL_MS);
})();
