(() => {
  "use strict";
  const payload = JSON.parse(document.querySelector("#julia-data")?.textContent || "{}");
  const STORE_KEY = "julia:cookbook:v1";
  const defaultStore = () => ({ schema: 1, updatedAt: new Date().toISOString(), active: {}, events: [], variations: [], tombstones: [], preferences: {} });
  const loadStore = () => { try { return { ...defaultStore(), ...JSON.parse(localStorage.getItem(STORE_KEY) || "{}") }; } catch { return defaultStore(); } };
  let store = loadStore();
  const saveStore = () => { store.updatedAt = new Date().toISOString(); localStorage.setItem(STORE_KEY, JSON.stringify(store)); };
  const toast = message => { const el = document.querySelector("#toast"); el.textContent = message; el.classList.add("show"); clearTimeout(el._timer); el._timer = setTimeout(() => el.classList.remove("show"), 2400); };
  const uuid = () => crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const download = (name, content) => { const link = document.createElement("a"); link.href = URL.createObjectURL(new Blob([content], { type: "application/json" })); link.download = name; link.click(); setTimeout(() => URL.revokeObjectURL(link.href), 1000); };

  document.querySelector('[data-action="open-data"]')?.addEventListener("click", () => document.querySelector("#data-dialog").showModal());
  document.querySelector('[data-action="export-data"]')?.addEventListener("click", event => { event.preventDefault(); download(`julia-cookbook-${new Date().toISOString().slice(0,10)}.json`, JSON.stringify(store, null, 2)); toast("Cookbook data exported"); });
  document.querySelector('[data-action="import-data"]')?.addEventListener("change", async event => {
    try { const imported = JSON.parse(await event.target.files[0].text()); if (imported.schema !== 1 || !Array.isArray(imported.events)) throw new Error("Unsupported Julia data file"); store = imported; saveStore(); toast("Data imported"); setTimeout(() => location.reload(), 500); } catch (error) { toast(error.message); }
  });

  const fraction = value => {
    value = String(value || "").trim();
    if (!value) return null;
    const mixed = value.match(/^(\d+)\s+(\d+)\/(\d+)$/); if (mixed) return +mixed[1] + (+mixed[2] / +mixed[3]);
    const simple = value.match(/^(\d+)\/(\d+)$/); if (simple) return +simple[1] / +simple[2];
    const numeric = Number(value); return Number.isFinite(numeric) ? numeric : null;
  };
  const displayNumber = value => {
    const common = [[.125,"1/8"],[.25,"1/4"],[.333,"1/3"],[.5,"1/2"],[.667,"2/3"],[.75,"3/4"]];
    const whole = Math.floor(value + 1e-6), remainder = value - whole;
    const found = common.find(([number]) => Math.abs(remainder - number) < .025);
    if (found) return `${whole ? whole + " " : ""}${found[1]}`;
    return Number(value.toFixed(2)).toString();
  };
  const scaleQuantity = (raw, scale) => raw.split("+").map(term => {
    const match = term.trim().match(/^(.+?)(?:\s+([A-Za-z]+))?$/); if (!match) return term;
    const number = fraction(match[1]); return number === null ? term.trim() : `${displayNumber(number * scale)}${match[2] ? " " + match[2] : ""}`;
  }).join(" + ");

  function setupRecipe() {
    const recipe = payload.recipe; if (!recipe) return;
    const active = store.active[recipe.id];
    const renderHistory = () => {
      const entries = store.events.filter(event => event.recipeId === recipe.id).sort((a,b) => b.completedAt.localeCompare(a.completedAt));
      const target = document.querySelector("[data-cook-history]");
      target.innerHTML = entries.length ? entries.map(event => `<article class="history-entry"><div><time>${new Date(event.completedAt).toLocaleDateString()}</time><br><small>${event.scale}x recipe</small></div><div><div class="history-title"><span class="history-outcome">${escapeHtml({worked:"Worked well",change:"Would change",failed:"Did not work"}[event.outcome] || event.outcome)}</span><button class="history-delete" data-delete-event="${escapeHtml(event.id)}">Delete</button></div><p>${escapeHtml(event.summary || "No summary")}</p></div></article>`).join("") : '<p class="muted">No completed cooks on this device yet.</p>';
      target.querySelectorAll("[data-delete-event]").forEach(button => button.addEventListener("click", () => {
        if (!confirm("Delete this cooking experiment? This cannot be undone.")) return;
        const id = button.dataset.deleteEvent;
        store.events = store.events.filter(event => event.id !== id);
        store.tombstones = [...(store.tombstones || []).filter(item => item.id !== id), { id, deletedAt: new Date().toISOString() }];
        saveStore(); renderHistory(); toast("Experiment deleted");
      }));
    };
    renderHistory();
    let scale = active?.scale || 1;
    const scaleSelect = document.querySelector("[data-scale]"); scaleSelect.value = String(scale);
    const anchorInputs = [...document.querySelectorAll("[data-scale-anchor]")];
    const scaleSummary = document.querySelector("[data-scale-summary]");
    let unitSystem = store.preferences?.[recipe.id]?.units || payload.units || "international";
    if (!scaleSelect.querySelector(`option[value="${scale}"]`)) scaleSelect.value = "custom";
    const scaledAnchorValue = input => Number((Number(input.dataset.anchorOriginal) * scale).toFixed(3));
    anchorInputs.forEach(input => input.value = scaledAnchorValue(input));
    const updateScaleSummary = () => {
      const anchors = anchorInputs.map(input => `${input.value}${input.dataset.anchorUnit ? " " + input.dataset.anchorUnit : ""} ${input.dataset.anchorLabel}`).join(" · ");
      scaleSummary.textContent = `${anchors || (scale === 1 ? "Original" : `${Number(scale.toFixed(2))}x`)} · ${unitSystem === "imperial" ? "Imperial" : "International"}`;
    };
    updateScaleSummary();
    const displayTemperature = (quantity, sourceUnit) => {
      const value = Number(quantity), unit = sourceUnit.replace("°", "").toUpperCase();
      if (!Number.isFinite(value) || !["F", "C"].includes(unit)) return `${quantity}°${sourceUnit}`;
      const converted = unitSystem === "international" ? (unit === "F" ? (value - 32) * 5 / 9 : value) : (unit === "C" ? value * 9 / 5 + 32 : value);
      const rounded = Math.abs(converted - Math.round(converted)) < 0.05 ? Math.round(converted) : Number(converted.toFixed(1));
      return `${rounded}°${unitSystem === "international" ? "C" : "F"}`;
    };
    const applyUnits = () => {
      document.querySelectorAll('.annotation.parameter[data-name="temp"]').forEach(element => element.textContent = displayTemperature(element.dataset.quantity, element.dataset.unit));
      document.querySelectorAll("[data-unit-system]").forEach(button => { const active = button.dataset.unitSystem === unitSystem; button.classList.toggle("active", active); button.setAttribute("aria-pressed", String(active)); });
      updateScaleSummary();
    };
    document.querySelectorAll("[data-unit-system]").forEach(button => button.addEventListener("click", () => {
      unitSystem = button.dataset.unitSystem;
      store.preferences ||= {}; store.preferences[recipe.id] = { ...(store.preferences[recipe.id] || {}), units: unitSystem }; saveStore(); applyUnits();
    }));
    applyUnits();
    const applyScale = () => {
      document.querySelectorAll(".measure[data-quantity]").forEach(el => { const quantity = el.dataset.quantity, itemScale = el.dataset.scaleItem === "false" ? 1 : scale; el.textContent = quantity ? `${scaleQuantity(quantity, itemScale)}${el.dataset.unit ? " " + el.dataset.unit : ""}` : "as needed"; });
      document.querySelectorAll(".inline-measure[data-quantity]").forEach(el => { const itemScale = el.dataset.scaleItem === "false" ? 1 : scale; el.textContent = `${scaleQuantity(el.dataset.quantity, itemScale)}${el.dataset.unit ? " " + el.dataset.unit : ""}`; });
    };
    const ratioMeasures = () => document.querySelectorAll("[data-ratio]").forEach(el => { const base = fraction(el.dataset.baseQuantity), ratio = fraction(el.dataset.ratio); el.textContent = base !== null && ratio !== null ? `${displayNumber(base * ratio / 100 * scale)} ${el.dataset.baseUnit} (${ratio}%)` : `${el.dataset.ratio}%`; });
    applyScale(); ratioMeasures();
    const saveScale = () => { applyScale(); ratioMeasures(); updateScaleSummary(); if (store.active[recipe.id]) { store.active[recipe.id].scale = scale; saveStore(); } };
    const updateAnchors = source => anchorInputs.forEach(input => { if (input !== source) input.value = scaledAnchorValue(input); });
    scaleSelect.addEventListener("change", () => { if (scaleSelect.value === "custom") return; scale = Number(scaleSelect.value); updateAnchors(null); saveScale(); });
    anchorInputs.forEach(anchorInput => anchorInput.addEventListener("input", () => { const desired = Number(anchorInput.value), original = Number(anchorInput.dataset.anchorOriginal); if (!(desired > 0 && original > 0)) return; scale = desired / original; updateAnchors(anchorInput); scaleSelect.value = scaleSelect.querySelector(`option[value="${scale}"]`) ? String(scale) : "custom"; saveScale(); }));

    const progress = () => {
      const checked = document.querySelectorAll('[data-check="step"]:checked').length;
      document.querySelector("[data-progress]").value = checked;
      document.querySelector("[data-progress-text]").textContent = `${checked} of ${recipe.steps.length} steps`;
      document.querySelectorAll("[data-step]").forEach(step => step.classList.toggle("complete", step.querySelector('[data-check="step"]').checked));
      document.querySelectorAll('[data-check="ingredient"]').forEach(input => {
        const step = input.closest("[data-step]");
        const inline = step?.querySelector(`.instructions [data-ingredient-index="${input.dataset.ingredientIndex}"]`);
        inline?.classList.toggle("checked", input.checked); inline?.setAttribute("aria-checked", String(input.checked));
      });
    };
    const persistActive = () => {
      const session = store.active[recipe.id]; if (!session) { progress(); return; }
      session.scale = scale; session.checks = {}; session.notes = {}; session.actuals = {};
      document.querySelectorAll("[data-check]").forEach(input => session.checks[`${input.dataset.check}:${input.dataset.key}`] = input.checked);
      document.querySelectorAll("[data-step-note]").forEach(input => session.notes[input.dataset.stepNote] = input.value);
      document.querySelectorAll("[data-actual]").forEach(input => { if (input.value) session.actuals[input.dataset.actual] = Number(input.value); });
      checkRatios();
      saveStore(); progress();
    };
    const enterCook = session => {
      document.body.classList.add("cooking"); document.querySelector("[data-progress-wrap]").hidden = false;
      document.querySelectorAll("[data-check]").forEach(input => input.checked = !!session.checks?.[`${input.dataset.check}:${input.dataset.key}`]);
      document.querySelectorAll("[data-step-note]").forEach(input => input.value = session.notes?.[input.dataset.stepNote] || "");
      document.querySelectorAll("[data-actual]").forEach(input => input.value = session.actuals?.[input.dataset.actual] ?? "");
      progress();
    };
    if (active) enterCook(active);
    document.querySelector('[data-action="start-cook"]').addEventListener("click", () => {
      const session = store.active[recipe.id] || { id: uuid(), recipeId: recipe.id, recipeTitle: recipe.metadata.title, startedAt: new Date().toISOString(), scale, checks: {}, notes: {} };
      store.active[recipe.id] = session; saveStore(); enterCook(session); toast("Cook started"); document.querySelector("#step-1")?.scrollIntoView();
    });
    document.querySelectorAll("[data-check]").forEach(input => input.addEventListener("change", persistActive));
    document.querySelectorAll('.instructions [role="checkbox"][data-ingredient-index]').forEach(inline => {
      const toggle = () => {
        const input = inline.closest("[data-step]")?.querySelector(`[data-check="ingredient"][data-ingredient-index="${inline.dataset.ingredientIndex}"]`);
        if (!input) return; input.checked = !input.checked; input.dispatchEvent(new Event("change", { bubbles: true }));
      };
      inline.addEventListener("click", toggle);
      inline.addEventListener("keydown", event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); toggle(); } });
    });
    document.querySelectorAll("[data-step-note]").forEach(input => input.addEventListener("input", persistActive));
    document.querySelectorAll("[data-actual]").forEach(input => input.addEventListener("input", persistActive));
    document.querySelector('[data-action="finish-cook"]').addEventListener("click", () => document.querySelector("#finish-dialog").showModal());
    document.querySelector('[data-action="discard-cook"]').addEventListener("click", () => {
      if (!confirm("Discard this cook? Checks, actual quantities, and notes from this session will be deleted.")) return;
      delete store.active[recipe.id]; saveStore();
      document.querySelectorAll("[data-check]").forEach(input => input.checked = false);
      document.querySelectorAll("[data-step-note],[data-actual]").forEach(input => input.value = "");
      document.querySelectorAll("[data-ratio-warning]").forEach(element => element.textContent = "");
      document.querySelector("#finish-dialog").close(); document.body.classList.remove("cooking"); document.querySelector("[data-progress-wrap]").hidden = true; progress(); toast("Cook discarded");
    });
    document.querySelector("[data-finish-form]").addEventListener("submit", event => {
      event.preventDefault(); persistActive(); const form = new FormData(event.currentTarget); const session = store.active[recipe.id];
      store.events.push({ ...session, id: session.id, completedAt: new Date().toISOString(), outcome: form.get("outcome"), summary: form.get("summary"), schema: 1 });
      delete store.active[recipe.id]; saveStore(); renderHistory(); document.querySelector("#finish-dialog").close(); document.body.classList.remove("cooking"); document.querySelector("[data-progress-wrap]").hidden = true; toast("Cooking event saved");
    });
    document.querySelectorAll(".annotation.timer").forEach(timer => timer.addEventListener("click", () => startTimer(timer)));
    function checkRatios() {
      document.querySelectorAll("[data-expected-ratio]").forEach(input => {
        const base = [...document.querySelectorAll("[data-ingredient-name]")].find(candidate => candidate.dataset.ingredientName.toLowerCase() === input.dataset.ratioBase.toLowerCase());
        const warning = document.querySelector(`[data-ratio-warning="${input.dataset.actual}"]`), actual = Number(input.value), baseActual = Number(base?.value);
        if (!actual || !baseActual) { warning.textContent = ""; return; }
        const ratio = actual / baseActual * 100, expected = Number(input.dataset.expectedRatio);
        warning.textContent = Math.abs(ratio - expected) >= 1 ? `Actual ratio ${ratio.toFixed(1)}%; recipe ${expected}%` : "";
      });
    }
  }

  const unitSeconds = { second:1, seconds:1, sec:1, minute:60, minutes:60, min:60, hour:3600, hours:3600, hr:3600 };
  function startTimer(element) {
    const raw = element.dataset.quantity, amount = fraction(raw.includes("-") ? raw.split("-")[0] : raw), seconds = amount * (unitSeconds[element.dataset.unit.toLowerCase()] || 60);
    if (!Number.isFinite(seconds)) return toast("This timer duration needs a number");
    const original = element.textContent, ends = Date.now() + seconds * 1000; element.setAttribute("role", "timer");
    const tick = () => { const left = Math.max(0, Math.ceil((ends - Date.now()) / 1000)); const min = Math.floor(left / 60), sec = String(left % 60).padStart(2,"0"); element.textContent = `${min}:${sec}`; if (left) element._timer = setTimeout(tick, 1000); else { element.textContent = `${original} done`; toast("Timer complete"); } };
    if (element._timer) { clearTimeout(element._timer); element._timer = null; element.textContent = original; return; } tick(); toast("Timer started; tap again to cancel");
  }

  function setupIndex() {
    if (!payload.recipes) return;
    const search = document.querySelector("[data-search]");
    const filter = () => { const query = search.value.toLowerCase(), tag = new URLSearchParams(location.search).get("tag")?.toLowerCase(); let shown = 0; document.querySelectorAll(".recipe-card").forEach(card => { const visible = (!query || card.dataset.search.includes(query)) && (!tag || card.dataset.tags.toLowerCase().split(" ").includes(tag)); card.hidden = !visible; shown += visible; }); document.querySelector("[data-empty]").hidden = !!shown; };
    search.addEventListener("input", filter); filter();
    const selected = new Set(); const updateCount = () => document.querySelector("[data-selected-count]").textContent = selected.size;
    document.querySelectorAll("[data-meal-recipe]").forEach(input => input.addEventListener("change", () => { input.checked ? selected.add(input.dataset.mealRecipe) : selected.delete(input.dataset.mealRecipe); updateCount(); }));
    let view = "merged";
    const renderShopping = () => {
      const recipes = payload.recipes.filter(recipe => selected.has(recipe.id)), groups = new Map();
      recipes.forEach(recipe => recipe.steps.forEach(step => step.ingredients.forEach(item => {
        const key = view === "merged" ? `${item.name.toLowerCase()}|${JSON.stringify(item.attributes)}` : recipe.metadata.title;
        if (!groups.has(key)) groups.set(key, { title: view === "merged" ? item.name : recipe.metadata.title, items: [] });
        groups.get(key).items.push(view === "merged" ? `${item.quantity}${item.unit ? " " + item.unit : ""}`.trim() || "as needed" : `${item.quantity}${item.unit ? " " + item.unit : ""} ${item.name}`.trim());
      })));
      document.querySelector("[data-shopping-list]").innerHTML = groups.size ? [...groups.values()].map(group => `<section class="shopping-group"><h3>${escapeHtml(group.title)}</h3><ul>${group.items.map(item => `<li><label><input type="checkbox"> ${escapeHtml(item)}</label></li>`).join("")}</ul></section>`).join("") : '<p class="muted">Select recipes from the collection first.</p>';
    };
    document.querySelector('[data-action="open-shopping"]').addEventListener("click", () => { renderShopping(); document.querySelector("#shopping-dialog").showModal(); });
    document.querySelectorAll("[data-shopping-view]").forEach(button => button.addEventListener("click", event => { event.preventDefault(); view = button.dataset.shoppingView; document.querySelectorAll("[data-shopping-view]").forEach(item => item.classList.toggle("active", item === button)); renderShopping(); }));
    document.querySelector('[data-action="clear-shopping"]').addEventListener("click", event => { event.preventDefault(); selected.clear(); document.querySelectorAll("[data-meal-recipe]").forEach(input => input.checked = false); updateCount(); renderShopping(); });
    document.querySelector('[data-action="copy-shopping"]').addEventListener("click", async event => { event.preventDefault(); const text = [...document.querySelectorAll("[data-shopping-list] h3,[data-shopping-list] li")].map(el => el.tagName === "H3" ? `\n${el.textContent}` : `- ${el.textContent.trim()}`).join("\n"); await navigator.clipboard.writeText(text); toast("Shopping list copied"); });
  }
  const escapeHtml = value => String(value).replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[char]);

  async function setupDrive() {
    const clientId = payload.sync?.googleClientId, panel = document.querySelector("[data-sync-panel]"); if (!panel) return;
    if (!clientId) return;
    const status = panel.querySelector("[data-sync-status]"), connect = panel.querySelector('[data-action="google-connect"]'), sync = panel.querySelector('[data-action="google-sync"]');
    connect.hidden = false; status.textContent = "Connect Drive to back up this device's Julia data.";
    const script = document.createElement("script"); script.src = "https://accounts.google.com/gsi/client"; script.async = true; document.head.append(script); await new Promise((resolve, reject) => { script.onload = resolve; script.onerror = reject; });
    let token = null;
    const tokenClient = google.accounts.oauth2.initTokenClient({ client_id: clientId, scope: "https://www.googleapis.com/auth/drive.appdata", callback: response => { if (response.error) return toast("Google connection failed"); token = response.access_token; connect.hidden = true; sync.hidden = false; status.textContent = "Connected. Julia uses Drive's private application folder."; syncDrive(); } });
    connect.addEventListener("click", event => { event.preventDefault(); tokenClient.requestAccessToken({ prompt: "consent" }); });
    sync.addEventListener("click", event => { event.preventDefault(); syncDrive(); });
    async function api(url, options = {}) { const response = await fetch(url, { ...options, headers: { Authorization: `Bearer ${token}`, ...(options.headers || {}) } }); if (!response.ok) throw new Error(`Drive returned ${response.status}`); return response; }
    async function syncDrive() {
      if (!token) return; status.textContent = "Syncing...";
      try {
        const found = await (await api("https://www.googleapis.com/drive/v3/files?spaces=appDataFolder&q=name%3D'julia-cookbook-v1.json'&fields=files(id,name,modifiedTime)")).json();
        if (found.files.length) {
          const remote = await (await api(`https://www.googleapis.com/drive/v3/files/${found.files[0].id}?alt=media`)).json();
          store.tombstones = mergeById(store.tombstones || [], remote.tombstones || []);
          const deleted = new Set(store.tombstones.map(item => item.id));
          store.events = mergeById(store.events, remote.events || []).filter(event => !deleted.has(event.id)); store.variations = mergeById(store.variations, remote.variations || []); store.active = { ...(remote.active || {}), ...store.active }; saveStore();
          await upload(found.files[0].id);
        } else await create();
        status.textContent = `Synced ${store.events.length} cooking events.`; toast("Google Drive sync complete");
      } catch (error) { status.textContent = error.message; toast("Drive sync failed"); }
    }
    const mergeById = (local, remote) => [...new Map([...remote, ...local].map(item => [item.id, item])).values()];
    async function create() { const boundary = `julia_${Date.now()}`, metadata = JSON.stringify({ name: "julia-cookbook-v1.json", parents: ["appDataFolder"] }); const body = `--${boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n${metadata}\r\n--${boundary}\r\nContent-Type: application/json\r\n\r\n${JSON.stringify(store)}\r\n--${boundary}--`; await api("https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart", { method:"POST", headers:{"Content-Type":`multipart/related; boundary=${boundary}`}, body }); }
    async function upload(id) { await api(`https://www.googleapis.com/upload/drive/v3/files/${id}?uploadType=media`, { method:"PATCH", headers:{"Content-Type":"application/json"}, body:JSON.stringify(store) }); }
  }
  setupRecipe(); setupIndex(); setupDrive().catch(() => {});
  if ("serviceWorker" in navigator && location.protocol.startsWith("http")) navigator.serviceWorker.register(`${document.documentElement.dataset.page === "recipe" ? "../" : ""}sw.js`).catch(() => {});
})();
