(() => {
  "use strict";
  const monthLabel = document.getElementById("month-label");
  const grid = document.getElementById("calendar-grid");
  const list = document.getElementById("event-list");
  const status = document.getElementById("calendar-status");
  const monthNames = ["January","February","March","April","May","June","July","August","September","October","November","December"];
  let view = new Date();
  view = new Date(view.getFullYear(), view.getMonth(), 1);
  let events = [];

  function parseEvents(source) {
    const records = source.split(/\r?\n\s*\r?\n/).map(s => s.trim()).filter(Boolean);
    const parsed = [];
    for (const record of records) {
      const fields = {};
      for (const line of record.split(/\r?\n/)) {
        const match = line.match(/^\s*(Date|Event|Time|Link)\s*:\s*(.*?)\s*$/i);
        if (match) fields[match[1].toLowerCase()] = match[2];
      }
      if (!fields.date || !fields.event) continue;
      const date = new Date(`${fields.date}T12:00:00`);
      if (Number.isNaN(date.getTime())) continue;
      let url = "";
      try {
        const candidate = new URL(fields.link || "");
        if (candidate.protocol === "https:" || candidate.protocol === "http:") url = candidate.href;
      } catch (_) {}
      parsed.push({ date, title: fields.event, time: fields.time || "Time not specified", url });
    }
    return parsed.sort((a,b) => a.date - b.date || a.title.localeCompare(b.title));
  }

  function sameDay(a,b) {
    return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
  }

  function render() {
    monthLabel.textContent = `${monthNames[view.getMonth()]} ${view.getFullYear()}`;
    grid.replaceChildren();
    const first = new Date(view.getFullYear(), view.getMonth(), 1);
    const startOffset = first.getDay();
    const daysInMonth = new Date(view.getFullYear(), view.getMonth() + 1, 0).getDate();
    const headers = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];
    headers.forEach(name => {
      const h = document.createElement("div");
      h.className = "rr-card"; h.style.padding = "8px"; h.style.textAlign = "center";
      h.textContent = name; grid.append(h);
    });
    for (let i=0; i<startOffset; i++) {
      const blank = document.createElement("div"); blank.setAttribute("aria-hidden","true"); grid.append(blank);
    }
    for (let day=1; day<=daysInMonth; day++) {
      const date = new Date(view.getFullYear(), view.getMonth(), day);
      const dayEvents = events.filter(e => sameDay(e.date,date));
      const cell = document.createElement("div");
      cell.className = "rr-card"; cell.style.minHeight = "76px"; cell.style.padding = "9px";
      const number = document.createElement("strong"); number.textContent = day; cell.append(number);
      if (dayEvents.length) {
        const marker = document.createElement("div"); marker.style.color = "var(--rr-green)";
        marker.style.fontSize = ".78rem"; marker.style.marginTop = "7px";
        marker.textContent = `${dayEvents.length} event${dayEvents.length === 1 ? "" : "s"}`;
        cell.append(marker);
        cell.title = dayEvents.map(e => e.title).join(" · ");
      }
      grid.append(cell);
    }
    const monthEvents = events.filter(e => e.date.getFullYear() === view.getFullYear() && e.date.getMonth() === view.getMonth());
    list.replaceChildren();
    if (!monthEvents.length) {
      const p = document.createElement("p");
      p.textContent = events.length ? "No events are listed for this month." : "No event records were found. Add entries to data/events.txt to populate the calendar.";
      list.append(p);
    } else {
      monthEvents.forEach(event => {
        const row = document.createElement("article"); row.className = "rr-card"; row.style.marginBottom = "9px";
        const heading = document.createElement("h3");
        heading.textContent = `${monthNames[event.date.getMonth()]} ${event.date.getDate()}: ${event.title}`;
        const detail = document.createElement("p"); detail.textContent = event.time;
        row.append(heading, detail);
        if (event.url) {
          const link = document.createElement("a"); link.href = event.url; link.target = "_blank";
          link.rel = "noopener noreferrer"; link.textContent = "Open event";
          row.append(link);
        }
        list.append(row);
      });
    }
  }

  document.getElementById("previous-month").addEventListener("click", () => {
    view = new Date(view.getFullYear(), view.getMonth()-1, 1); render();
  });
  document.getElementById("next-month").addEventListener("click", () => {
    view = new Date(view.getFullYear(), view.getMonth()+1, 1); render();
  });

  fetch("../data/events.txt")
    .then(response => { if (!response.ok) throw new Error(`HTTP ${response.status}`); return response.text(); })
    .then(source => {
      events = parseEvents(source);
      status.textContent = `${events.length} event record${events.length === 1 ? "" : "s"} loaded.`;
      render();
    })
    .catch(error => {
      status.textContent = "Could not load event data. Make sure data/events.txt is committed to the repository.";
      list.textContent = error.message;
      render();
    });
})();
