// Small progressive enhancements. Every page also works without JavaScript.

// 1. Submit a form as soon as a select or checkbox marked data-autosubmit changes.
document.addEventListener("change", (event) => {
  const el = event.target.closest("[data-autosubmit]");
  if (el && el.form) el.form.requestSubmit();
});

// 2. Feedback buttons on course suggestions: save without reloading the page.
document.addEventListener("submit", async (event) => {
  const form = event.target.closest("form.js-feedback");
  if (!form || !event.submitter) return;
  event.preventDefault();
  const data = new FormData(form);
  data.set("response", event.submitter.value);
  try {
    const res = await fetch(form.action, { method: "POST", body: data, headers: { "X-Requested-With": "fetch" } });
    if (!res.ok) throw new Error(res.statusText);
    const { response } = await res.json();
    form.querySelectorAll("button[data-value]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.value === response)));
  } catch {
    form.submit();
  }
});

// 3. Skill search with aliases (My skills page).
(function skillCombobox() {
  const input = document.getElementById("skill-search");
  const list = document.getElementById("skill-options");
  const hidden = document.getElementById("skill-id");
  const dataEl = document.getElementById("skill-data");
  if (!input || !list || !hidden || !dataEl) return;

  const skills = JSON.parse(dataEl.textContent);
  let options = [];
  let active = -1;

  const score = (s, q) => {
    const name = s.name.toLowerCase();
    if (name.startsWith(q)) return 0;
    if (s.aliases.some((a) => a.toLowerCase() === q)) return 0.5;
    if (name.includes(q)) return 1;
    if (s.aliases.some((a) => a.toLowerCase().startsWith(q))) return 1.5;
    if (s.aliases.some((a) => a.toLowerCase().includes(q))) return 2;
    return null;
  };

  function search() {
    const q = input.value.trim().toLowerCase();
    hidden.value = "";
    if (!q) return close();
    options = skills
      .map((s) => [score(s, q), s])
      .filter(([sc]) => sc !== null)
      .sort((a, b) => a[0] - b[0] || a[1].name.localeCompare(b[1].name))
      .slice(0, 8)
      .map(([, s]) => ({ type: "skill", ...s }));
    if (!options.some((o) => o.name.toLowerCase() === q)) options.push({ type: "propose", name: input.value.trim() });
    active = 0;
    draw();
  }

  function draw() {
    list.replaceChildren(...options.map((o, i) => {
      const li = document.createElement("li");
      li.id = `skill-opt-${i}`;
      li.setAttribute("role", "option");
      li.setAttribute("aria-selected", String(i === active));
      li.dataset.index = i;
      if (o.type === "skill") {
        const name = document.createElement("span");
        name.textContent = o.name;
        const fam = document.createElement("span");
        fam.className = "fam";
        fam.textContent = o.family;
        li.append(name, fam);
      } else {
        li.className = "propose";
        li.textContent = `Propose “${o.name}” as a new skill`;
      }
      return li;
    }));
    list.hidden = options.length === 0;
    input.setAttribute("aria-expanded", String(!list.hidden));
    if (active >= 0) {
      input.setAttribute("aria-activedescendant", `skill-opt-${active}`);
      document.getElementById(`skill-opt-${active}`)?.scrollIntoView({ block: "nearest" });
    }
  }

  function close() {
    options = [];
    list.hidden = true;
    input.setAttribute("aria-expanded", "false");
    input.removeAttribute("aria-activedescendant");
  }

  function choose(i) {
    const o = options[i];
    if (!o) return;
    if (o.type === "propose") {
      const url = new URL(input.dataset.proposeUrl, window.location.origin);
      url.searchParams.set("name", o.name);
      window.location.href = url.toString();
      return;
    }
    input.value = o.name;
    hidden.value = o.id;
    close();
    input.form.requestSubmit();
  }

  input.addEventListener("input", search);
  input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); if (!options.length) search(); else { active = (active + 1) % options.length; draw(); } }
    else if (e.key === "ArrowUp") { e.preventDefault(); if (options.length) { active = (active - 1 + options.length) % options.length; draw(); } }
    else if (e.key === "Enter") { if (options.length && active >= 0) { e.preventDefault(); choose(active); } }
    else if (e.key === "Escape") { close(); }
  });
  list.addEventListener("mousedown", (e) => {
    const li = e.target.closest("li[data-index]");
    if (li) { e.preventDefault(); choose(Number(li.dataset.index)); }
  });
  input.addEventListener("blur", () => setTimeout(close, 150));
})();

// 4. Close open dropdown menus on an outside click or Escape.
document.addEventListener("click", (event) => {
  document.querySelectorAll("details[data-dropdown][open]").forEach((menu) => {
    if (!menu.contains(event.target)) menu.removeAttribute("open");
  });
});
document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  document.querySelectorAll("details[data-dropdown][open]").forEach((menu) => {
    menu.removeAttribute("open");
    menu.querySelector("summary")?.focus();
  });
});
