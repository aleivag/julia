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

  function setupTheme() {
    const root = document.documentElement;
    const allowed = new Set(["auto", "nordic", "night", "editorial"]);
    const media = matchMedia("(prefers-color-scheme: dark)");
    const select = document.querySelector("[data-theme-select]");
    let theme = store.preferences?.theme || root.dataset.themeDefault || "auto";
    if (!allowed.has(theme)) theme = "auto";
    const apply = () => {
      const effective = theme === "auto" ? (media.matches ? "night" : "nordic") : theme;
      root.dataset.theme = theme;
      root.dataset.themeEffective = effective;
      root.style.colorScheme = effective === "night" ? "dark" : "light";
      const meta = document.querySelector('meta[name="theme-color"]');
      if (meta) meta.content = effective === "night" ? "#151816" : effective === "editorial" ? "#f6f0e5" : "#f5f7f8";
      if (select) select.value = theme;
    };
    select?.addEventListener("change", () => {
      theme = allowed.has(select.value) ? select.value : "auto";
      store.preferences ||= {}; store.preferences.theme = theme; saveStore(); apply();
    });
    media.addEventListener?.("change", () => { if (theme === "auto") apply(); });
    apply();
  }

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
  const decimal = (value, places = 2) => Number(value.toFixed(places)).toString();
  const normalizedUnit = unit => String(unit || "").trim().toLowerCase().replace(/\.$/, "");
  const convertedMeasure = (value, unit, system) => {
    const normalized = normalizedUnit(unit);
    if (!Number.isFinite(value)) return null;
    if (system === "international") {
      if (["oz", "ounce", "ounces"].includes(normalized)) return `${decimal(value * 28.3495, value * 28.3495 >= 10 ? 0 : 1)} g`;
      if (["lb", "lbs", "pound", "pounds"].includes(normalized)) {
        const grams = value * 453.592;
        return grams >= 1000 ? `${decimal(grams / 1000)} kg` : `${decimal(grams, 0)} g`;
      }
      if (["tsp", "teaspoon", "teaspoons"].includes(normalized)) return `${decimal(value * 5, 1)} ml`;
      if (["tbsp", "tablespoon", "tablespoons"].includes(normalized)) return `${decimal(value * 15, 1)} ml`;
      if (["cup", "cups"].includes(normalized)) return `${decimal(value * 240, 0)} ml`;
      if (["fl oz", "fluid ounce", "fluid ounces"].includes(normalized)) return `${decimal(value * 30, 0)} ml`;
      if (["qt", "quart", "quarts"].includes(normalized)) return `${decimal(value * .946353)} L`;
      if (["gal", "gallon", "gallons"].includes(normalized)) return `${decimal(value * 3.78541)} L`;
    } else {
      if (["g", "gram", "grams"].includes(normalized)) {
        const ounces = value / 28.3495;
        return ounces >= 16 ? `${decimal(ounces / 16)} lb` : `${decimal(ounces)} oz`;
      }
      if (["kg", "kilogram", "kilograms"].includes(normalized)) return `${decimal(value * 2.20462)} lb`;
      if (["ml", "milliliter", "milliliters", "millilitre", "millilitres"].includes(normalized)) return `${decimal(value / 30)} fl oz`;
      if (["l", "liter", "liters", "litre", "litres"].includes(normalized)) return `${decimal(value / .946353)} qt`;
      if (["cm", "centimeter", "centimeters", "centimetre", "centimetres"].includes(normalized)) return `${decimal(value / 2.54)} in`;
    }
    if (system === "international" && ["in", "inch", "inches"].includes(normalized)) return `${decimal(value * 2.54)} cm`;
    return null;
  };
  const temperatureMeasure = (value, unit, system) => {
    const source = String(unit || "").replace("°", "").toUpperCase();
    if (!Number.isFinite(value) || !["F", "C"].includes(source)) return null;
    const converted = system === "international" ? (source === "F" ? (value - 32) * 5 / 9 : value) : (source === "C" ? value * 9 / 5 + 32 : value);
    const rounded = Math.abs(converted - Math.round(converted)) < .05 ? Math.round(converted) : Number(converted.toFixed(1));
    return `${rounded}°${system === "international" ? "C" : "F"}`;
  };
  const smartRange = (raw, render) => {
    const range = String(raw || "").trim().match(/^(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)$/);
    if (range) return `${render(Number(range[1]))}–${render(Number(range[2]))}`;
    const value = fraction(raw);
    return value === null ? null : render(value);
  };
  const scaleQuantity = (raw, scale) => raw.split("+").map(term => {
    const match = term.trim().match(/^(.+?)(?:\s+([A-Za-z]+))?$/); if (!match) return term;
    const number = fraction(match[1]); return number === null ? term.trim() : `${displayNumber(number * scale)}${match[2] ? " " + match[2] : ""}`;
  }).join(" + ");

  function setupRecipe() {
    const recipe = payload.recipe; if (!recipe) return;
    const recipeKey = recipe.storageId || recipe.id;
    if (recipe.variant) {
      store.preferences ||= {}; store.preferences[recipe.parentId || recipe.id] ||= {};
      store.preferences[recipe.parentId || recipe.id].variant = recipe.variant; saveStore();
    }
    const active = store.active[recipeKey];
    const renderHistory = () => {
      const entries = store.events.filter(event => event.recipeId === recipeKey).sort((a,b) => b.completedAt.localeCompare(a.completedAt));
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
    const compoundYield = document.querySelector("[data-compound-yield]");
    const yieldCount = compoundYield?.querySelector("[data-yield-count]");
    const yieldEach = compoundYield?.querySelector("[data-yield-each]");
    const yieldTotal = compoundYield?.querySelector("[data-yield-total]");
    const bakersFormula = document.querySelector("[data-bakers-formula]");
    const formulaFlour = bakersFormula?.querySelector("[data-formula-flour]");
    const formulaHydration = bakersFormula?.querySelector("[data-formula-hydration]");
    const formulaTotal = bakersFormula?.querySelector("[data-formula-total]");
    const formulaResult = bakersFormula?.querySelector("[data-formula-result]");
    if (active?.yieldCount && yieldCount) yieldCount.value = active.yieldCount;
    if (active?.yieldEach && yieldEach) yieldEach.value = active.yieldEach;
    if (bakersFormula) {
      formulaFlour.value = Number((Number(bakersFormula.dataset.originalFlour) * scale).toFixed(2));
      formulaHydration.value = String(active?.hydration || store.preferences?.[recipeKey]?.hydration || bakersFormula.dataset.originalHydration);
    }
    const scaleSummary = document.querySelector("[data-scale-summary]");
    let unitSystem = store.preferences?.[recipeKey]?.units || payload.units || "international";
    if (!scaleSelect.querySelector(`option[value="${scale}"]`)) scaleSelect.value = "custom";
    const scaledAnchorValue = input => Number((Number(input.dataset.anchorOriginal) * scale).toFixed(3));
    anchorInputs.forEach(input => input.value = scaledAnchorValue(input));
    const updateScaleSummary = () => {
      const anchors = anchorInputs.map(input => `${input.value}${input.dataset.anchorUnit ? " " + input.dataset.anchorUnit : ""} ${input.dataset.anchorLabel}`).join(" · ");
      const compound = compoundYield ? `${yieldCount.value} × ${yieldEach.value} ${compoundYield.dataset.eachUnit}` : "";
      const formula = bakersFormula ? `${formulaFlour.value} ${bakersFormula.dataset.flourUnit} flour · ${formulaHydration.value}% hydration` : "";
      scaleSummary.textContent = `${[compound, formula].filter(Boolean).join(" · ") || anchors || (scale === 1 ? "Original" : `${Number(scale.toFixed(2))}x`)} · ${unitSystem === "imperial" ? "Imperial" : "International"}`;
    };
    updateScaleSummary();
    const displayTemperature = (quantity, sourceUnit) => {
      return smartRange(quantity, value => temperatureMeasure(value, sourceUnit, unitSystem)) || `${quantity}°${sourceUnit}`;
    };
    const displayMeasure = (quantity, unit, itemScale = 1) => {
      const numeric = fraction(quantity);
      const converted = numeric === null ? null : convertedMeasure(numeric * itemScale, unit, unitSystem);
      return converted || `${scaleQuantity(quantity, itemScale)}${unit ? " " + unit : ""}`;
    };
    const applyUnits = () => {
      document.querySelectorAll('.annotation.parameter[data-name="temp"]').forEach(element => element.textContent = displayTemperature(element.dataset.quantity, element.dataset.unit));
      document.querySelectorAll("[data-unit-system]").forEach(button => { const active = button.dataset.unitSystem === unitSystem; button.classList.toggle("active", active); button.setAttribute("aria-pressed", String(active)); });
      updateScaleSummary();
    };
    document.querySelectorAll("[data-unit-system]").forEach(button => button.addEventListener("click", () => {
      unitSystem = button.dataset.unitSystem;
      store.preferences ||= {}; store.preferences[recipeKey] = { ...(store.preferences[recipeKey] || {}), units: unitSystem }; saveStore(); applyUnits(); applyScale(); ratioMeasures();
    }));
    applyUnits();
    const countScale = () => compoundYield ? Number(yieldCount.value) / Number(compoundYield.dataset.originalCount) : scale;
    const formulaFactor = () => bakersFormula ? 1 + Number(formulaHydration.value) / 100 + Number(bakersFormula.dataset.otherRatio) / 100 : 0;
    const renderFormula = () => {
      if (!bakersFormula) return;
      const total = Number(formulaFlour.value) * formulaFactor();
      const target = Number(yieldCount.value) * Number(yieldEach.value);
      const difference = total - target;
      formulaTotal.textContent = displayNumber(total);
      formulaResult.textContent = Math.abs(difference) < .05 ? "No extra dough" : difference > 0 ? `${displayNumber(difference)} ${compoundYield.dataset.eachUnit} extra` : `${displayNumber(Math.abs(difference))} ${compoundYield.dataset.eachUnit} short`;
    };
    const applyScale = () => {
      document.querySelectorAll(".measure[data-quantity]").forEach(el => { const quantity = el.dataset.quantity, itemScale = el.dataset.scaleMode === "count" ? countScale() : el.dataset.scaleItem === "false" ? 1 : scale; el.textContent = quantity ? displayMeasure(quantity, el.dataset.unit, itemScale) : "as needed"; });
      document.querySelectorAll(".inline-measure[data-quantity]").forEach(el => { const itemScale = el.dataset.scaleMode === "count" ? countScale() : el.dataset.scaleItem === "false" ? 1 : scale; el.textContent = displayMeasure(el.dataset.quantity, el.dataset.unit, itemScale); });
      if (yieldTotal) yieldTotal.textContent = displayNumber(Number(yieldCount.value) * Number(yieldEach.value));
      renderFormula();
    };
    const ratioMeasures = () => document.querySelectorAll("[data-ratio]").forEach(el => {
      if (el.dataset.ratioOptions && formulaHydration) el.dataset.ratio = formulaHydration.value;
      const base = fraction(el.dataset.baseQuantity), ratio = fraction(el.dataset.ratio);
      const text = base !== null && ratio !== null ? `${displayMeasure(String(base * ratio / 100), el.dataset.baseUnit, scale)} (${ratio}%)` : `${el.dataset.ratio}%`;
      el.textContent = text;
      const row = el.closest("li"), index = row?.querySelector("[data-ingredient-index]")?.dataset.ingredientIndex;
      const scope = el.closest("[data-choice-panel]") || el.closest("[data-step]");
      if (index !== undefined) scope?.querySelector(`.instructions .annotation.ingredient[data-ingredient-index="${index}"] .inline-measure`)?.replaceChildren(text);
    });
    applyScale(); ratioMeasures();
    const saveScale = () => { applyScale(); ratioMeasures(); updateScaleSummary(); if (bakersFormula) { store.preferences ||= {}; store.preferences[recipeKey] = { ...(store.preferences[recipeKey] || {}), hydration: Number(formulaHydration.value) }; } if (store.active[recipeKey]) { store.active[recipeKey].scale = scale; if (compoundYield) { store.active[recipeKey].yieldCount = Number(yieldCount.value); store.active[recipeKey].yieldEach = Number(yieldEach.value); } if (bakersFormula) store.active[recipeKey].hydration = Number(formulaHydration.value); } saveStore(); };
    const updateAnchors = source => anchorInputs.forEach(input => { if (input !== source) input.value = scaledAnchorValue(input); });
    const formulaFromTarget = () => {
      const target = Number(yieldCount.value) * Number(yieldEach.value);
      formulaFlour.value = Number((target / formulaFactor()).toFixed(2));
      scale = Number(formulaFlour.value) / Number(bakersFormula.dataset.originalFlour);
    };
    const formulaFromFlour = () => {
      scale = Number(formulaFlour.value) / Number(bakersFormula.dataset.originalFlour);
      const available = Number(formulaFlour.value) * formulaFactor();
      yieldCount.value = Math.max(1, Math.floor((available + .0001) / Number(yieldEach.value)));
    };
    scaleSelect.addEventListener("change", () => { if (scaleSelect.value === "custom") return; const selectedScale = Number(scaleSelect.value); if (compoundYield) { yieldCount.value = Number(compoundYield.dataset.originalCount) * selectedScale; yieldEach.value = compoundYield.dataset.originalEach; } if (bakersFormula) formulaFromTarget(); else scale = selectedScale; updateAnchors(null); saveScale(); });
    anchorInputs.forEach(anchorInput => anchorInput.addEventListener("input", () => { const desired = Number(anchorInput.value), original = Number(anchorInput.dataset.anchorOriginal); if (!(desired > 0 && original > 0)) return; scale = desired / original; updateAnchors(anchorInput); scaleSelect.value = scaleSelect.querySelector(`option[value="${scale}"]`) ? String(scale) : "custom"; saveScale(); }));
    [yieldCount, yieldEach].filter(Boolean).forEach(input => input.addEventListener("input", () => {
      const total = Number(yieldCount.value) * Number(yieldEach.value);
      const original = Number(compoundYield.dataset.originalCount) * Number(compoundYield.dataset.originalEach);
      if (!(total > 0 && original > 0)) return;
      if (bakersFormula) formulaFromTarget(); else scale = total / original;
      scaleSelect.value = "custom"; saveScale();
    }));
    formulaFlour?.addEventListener("input", () => { if (!(Number(formulaFlour.value) > 0)) return; formulaFromFlour(); scaleSelect.value = "custom"; saveScale(); });
    formulaHydration?.addEventListener("change", () => { formulaFromFlour(); scaleSelect.value = "custom"; saveScale(); });

    document.querySelectorAll("[data-choice-step]").forEach(choiceStep => {
      const choice = choiceStep.dataset.choiceStep;
      const saved = store.preferences?.[recipeKey]?.choices?.[choice];
      const select = option => {
        choiceStep.querySelectorAll("[data-choice-panel]").forEach(panel => { panel.hidden = panel.dataset.choicePanel !== option; });
        choiceStep.querySelectorAll("[data-choice-select]").forEach(input => { input.checked = input.value === option; });
      };
      select(saved || choiceStep.dataset.choiceDefault);
      choiceStep.querySelectorAll("[data-choice-select]").forEach(input => input.addEventListener("change", () => {
        if (!input.checked) return;
        store.preferences ||= {}; store.preferences[recipeKey] ||= {}; store.preferences[recipeKey].choices ||= {};
        store.preferences[recipeKey].choices[choice] = input.value; saveStore(); select(input.value);
      }));
    });

    const progress = () => {
      const rootSteps = document.querySelectorAll("[data-step]");
      const checked = document.querySelectorAll('[data-check="step"]:checked').length;
      document.querySelector("[data-progress]").value = checked;
      document.querySelector("[data-progress-text]").textContent = `${checked} of ${rootSteps.length} steps`;
      document.querySelectorAll("[data-step]").forEach(step => step.classList.toggle("complete", step.querySelector('[data-check="step"]').checked));
      document.querySelectorAll("[data-embedded-step]").forEach(step => step.classList.toggle("complete", step.querySelector('[data-step-completion]').checked));
      document.querySelectorAll("[data-dependency-node]").forEach(step => step.classList.toggle("complete", step.querySelector(':scope > summary [data-step-completion]').checked));
      document.querySelectorAll('[data-check="ingredient"]').forEach(input => {
        const step = input.closest("[data-step]");
        const inline = step?.querySelector(`.instructions [data-ingredient-index="${input.dataset.ingredientIndex}"]`);
        inline?.classList.toggle("checked", input.checked); inline?.setAttribute("aria-checked", String(input.checked));
      });
      document.querySelectorAll('[data-check="input"]').forEach(input => {
        const step = input.closest("[data-step]");
        const inline = step?.querySelector(`.instructions [data-input-index="${input.dataset.inputIndex}"]`);
        inline?.classList.toggle("checked", input.checked); inline?.setAttribute("aria-checked", String(input.checked));
      });
      document.querySelectorAll('[data-embedded-check]').forEach(input => {
        const inline = document.querySelector(`[data-embedded-toggle="${CSS.escape(input.dataset.embeddedCheck)}"]`);
        inline?.classList.toggle("checked", input.checked); inline?.setAttribute("aria-checked", String(input.checked));
      });
    };
    const persistActive = () => {
      const session = store.active[recipeKey]; if (!session) { progress(); return; }
      session.scale = scale; session.checks = {}; session.notes = {}; session.actuals = {};
      if (compoundYield) { session.yieldCount = Number(yieldCount.value); session.yieldEach = Number(yieldEach.value); }
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
    const prepInputs = [...document.querySelectorAll("[data-prep-ingredient]")];
    const prepState = store.preferences?.[recipeKey]?.ingredientPrep || {};
    const savePrep = prep => {
      store.preferences ||= {}; store.preferences[recipeKey] ||= {}; store.preferences[recipeKey].ingredientPrep ||= {};
      store.preferences[recipeKey].ingredientPrep[prep.dataset.prepIngredient] = prep.checked;
    };
    prepInputs.forEach(prep => {
      prep.checked = !!prepState[prep.dataset.prepIngredient];
      prep.addEventListener("change", () => {
        prepInputs.filter(other => other.dataset.prepIngredient === prep.dataset.prepIngredient).forEach(other => { other.checked = prep.checked; });
        savePrep(prep); saveStore();
      });
    });
    progress();
    document.querySelector('[data-action="start-cook"]').addEventListener("click", () => {
      const session = store.active[recipeKey] || { id: uuid(), recipeId: recipeKey, recipeTitle: recipe.variantTitle ? `${recipe.metadata.title} — ${recipe.variantTitle}` : recipe.metadata.title, startedAt: new Date().toISOString(), scale, checks: {}, notes: {} };
      store.active[recipeKey] = session; saveStore(); enterCook(session); toast("Cook started"); document.querySelector("#step-1")?.scrollIntoView();
    });
    document.querySelectorAll("[data-check]").forEach(input => input.addEventListener("change", persistActive));
    const syncDependencyAncestors = source => {
      let node = source.closest("[data-dependency-node]");
      if (node?.querySelector(':scope > summary [data-step-completion]') === source) node = node.parentElement.closest("[data-dependency-node]");
      while (node) {
        const parent = node.querySelector(':scope > summary [data-step-completion]');
        const children = [...node.querySelectorAll(':scope > .dependency-children [data-step-completion]')];
        parent.checked = children.length > 0 && children.every(child => child.checked);
        node = node.parentElement.closest("[data-dependency-node]");
      }
    };
    document.querySelectorAll("[data-step-completion]").forEach(input => {
      input.addEventListener("click", event => event.stopPropagation());
      input.addEventListener("change", () => {
        const node = input.closest("[data-dependency-node]");
        if (node?.querySelector(':scope > summary [data-step-completion]') === input) {
          node.querySelectorAll(':scope > .dependency-children [data-step-completion]').forEach(child => { child.checked = input.checked; });
        }
        syncDependencyAncestors(input); persistActive();
      });
    });
    document.querySelectorAll(".dependency-step-summary label,.dependency-step-summary a").forEach(control => control.addEventListener("click", event => event.stopPropagation()));
    document.querySelectorAll('.instructions [role="checkbox"][data-ingredient-index]').forEach(inline => {
      const toggle = () => {
        const input = inline.closest("[data-step]")?.querySelector(`[data-check="ingredient"][data-ingredient-index="${inline.dataset.ingredientIndex}"]`);
        if (!input) return; input.checked = !input.checked; input.dispatchEvent(new Event("change", { bubbles: true }));
      };
      inline.addEventListener("click", toggle);
      inline.addEventListener("keydown", event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); toggle(); } });
    });
    document.querySelectorAll('.instructions [role="checkbox"][data-input-index]').forEach(inline => {
      const toggle = () => {
        const input = inline.closest("[data-step]")?.querySelector(`[data-check="input"][data-input-index="${inline.dataset.inputIndex}"]`);
        if (!input) return; input.checked = !input.checked; input.dispatchEvent(new Event("change", { bubbles: true }));
      };
      inline.addEventListener("click", toggle);
      inline.addEventListener("keydown", event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); toggle(); } });
    });
    document.querySelectorAll('[role="checkbox"][data-embedded-toggle]').forEach(inline => {
      const toggle = () => {
        const input = document.querySelector(`[data-embedded-check="${CSS.escape(inline.dataset.embeddedToggle)}"]`);
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
      delete store.active[recipeKey]; saveStore();
      document.querySelectorAll("[data-check]").forEach(input => input.checked = false);
      document.querySelectorAll("[data-step-note],[data-actual]").forEach(input => input.value = "");
      document.querySelectorAll("[data-ratio-warning]").forEach(element => element.textContent = "");
      document.querySelector("#finish-dialog").close(); document.body.classList.remove("cooking"); document.querySelector("[data-progress-wrap]").hidden = true; progress(); toast("Cook discarded");
    });
    document.querySelector("[data-finish-form]").addEventListener("submit", event => {
      event.preventDefault(); persistActive(); const form = new FormData(event.currentTarget); const session = store.active[recipeKey];
      store.events.push({ ...session, id: session.id, completedAt: new Date().toISOString(), outcome: form.get("outcome"), summary: form.get("summary"), schema: 1 });
      delete store.active[recipeKey]; saveStore(); renderHistory(); document.querySelector("#finish-dialog").close(); document.body.classList.remove("cooking"); document.querySelector("[data-progress-wrap]").hidden = true; toast("Cooking event saved");
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

  function setupGuide() {
    const guide = payload.guide; if (!guide) return;
    const preferenceKey = `guide:${guide.id}`;
    let unitSystem = store.preferences?.[preferenceKey]?.units || payload.units || "international";
    const render = () => {
      document.querySelectorAll(".annotation.parameter").forEach(element => {
        const name = element.dataset.name, quantity = element.dataset.quantity, unit = element.dataset.unit;
        if (name === "temp") {
          element.textContent = smartRange(quantity, value => temperatureMeasure(value, unit, unitSystem)) || `${quantity}°${unit}`;
        } else if (["weight", "thickness"].includes(name)) {
          element.textContent = smartRange(quantity, value => convertedMeasure(value, unit, unitSystem) || `${decimal(value)} ${unit}`) || `${quantity} ${unit}`;
        } else {
          element.textContent = `${quantity}${unit ? " " + unit : ""}`;
        }
      });
      document.querySelectorAll("[data-guide-unit]").forEach(button => {
        const active = button.dataset.guideUnit === unitSystem;
        button.classList.toggle("active", active); button.setAttribute("aria-pressed", String(active));
      });
    };
    document.querySelectorAll("[data-guide-unit]").forEach(button => button.addEventListener("click", () => {
      unitSystem = button.dataset.guideUnit;
      store.preferences ||= {}; store.preferences[preferenceKey] = { ...(store.preferences[preferenceKey] || {}), units: unitSystem }; saveStore(); render();
    }));
    render();
  }

  function setupFeastShopping() {
    const feast = payload.feastShopping; if (!feast?.id) return;
    store.preferences ||= {}; store.preferences.feastShopping ||= {};
    const checked = store.preferences.feastShopping[feast.id] || {};
    document.querySelectorAll("[data-feast-shopping-item]").forEach(input => {
      input.checked = !!checked[input.dataset.feastShoppingItem];
      input.addEventListener("change", () => {
        checked[input.dataset.feastShoppingItem] = input.checked;
        store.preferences.feastShopping[feast.id] = checked;
        saveStore();
      });
    });
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
    const normalizeSearch = value => String(value).normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
    const search = document.querySelector("[data-search]");
    if (!search) return;
    search.value = new URLSearchParams(location.search).get("q") || "";
    const filter = () => { const query = normalizeSearch(search.value), rawTag = new URLSearchParams(location.search).get("tag"), tag = rawTag ? normalizeSearch(rawTag) : null; let shown = 0; document.querySelectorAll(".recipe-card").forEach(card => { const visible = (!query || normalizeSearch(card.dataset.search).includes(query)) && (!tag || normalizeSearch(card.dataset.tags).split(" ").includes(tag)); card.hidden = !visible; shown += visible; }); document.querySelector("[data-empty]").hidden = !!shown; };
    search.addEventListener("input", filter); filter();
    const shoppingButton = document.querySelector('[data-action="open-shopping"]');
    if (!payload.recipes || !shoppingButton) return;
    payload.recipes.forEach(recipe => {
      const selectedVariant = store.preferences?.[recipe.id]?.variant;
      const variant = recipe.variants?.find(item => item.id === selectedVariant);
      const link = document.querySelector(`[data-recipe-link="${CSS.escape(recipe.id)}"]`);
      if (link && variant && !variant.default) link.href = `recipes/${recipe.id}--${variant.id}.html`;
    });
    const selected = new Set(); const updateCount = () => document.querySelector("[data-selected-count]").textContent = selected.size;
    document.querySelectorAll("[data-meal-recipe]").forEach(input => input.addEventListener("change", () => { input.checked ? selected.add(input.dataset.mealRecipe) : selected.delete(input.dataset.mealRecipe); updateCount(); }));
    let view = "merged";
    const renderShopping = () => {
      const recipes = payload.recipes.filter(recipe => selected.has(recipe.id)), groups = new Map();
      recipes.forEach(recipe => (recipe.shoppingIngredients || recipe.steps.flatMap(step => step.ingredients)).filter(item => {
        if (item.variant && item.variant !== (store.preferences?.[recipe.id]?.variant || recipe.defaultVariant)) return false;
        if (!item.choice) return true;
        const selected = store.preferences?.[recipe.id]?.choices?.[item.choice];
        return selected ? item.option === selected : item.default;
      }).forEach(item => {
        const source = item.sourceTitle || recipe.metadata.title;
        const key = view === "merged" ? `${item.name.toLowerCase()}|${JSON.stringify(item.attributes)}` : source;
        if (!groups.has(key)) groups.set(key, { title: view === "merged" ? item.name : source, items: [] });
        groups.get(key).items.push(view === "merged" ? `${item.quantity}${item.unit ? " " + item.unit : ""}`.trim() || "as needed" : `${item.quantity}${item.unit ? " " + item.unit : ""} ${item.name}`.trim());
      }));
      document.querySelector("[data-shopping-list]").innerHTML = groups.size ? [...groups.values()].map(group => `<section class="shopping-group"><h3>${escapeHtml(group.title)}</h3><ul>${group.items.map(item => `<li><label><input type="checkbox"> ${escapeHtml(item)}</label></li>`).join("")}</ul></section>`).join("") : '<p class="muted">Select recipes from the collection first.</p>';
    };
    shoppingButton.addEventListener("click", () => { renderShopping(); document.querySelector("#shopping-dialog").showModal(); });
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
  setupTheme(); setupRecipe(); setupGuide(); setupFeastShopping(); setupIndex(); setupDrive().catch(() => {});
  if ("serviceWorker" in navigator && location.protocol.startsWith("http")) {
    const page = document.documentElement.dataset.page;
    const prefix = page === "feast-shopping" ? "../../" : ["recipe","guide"].includes(page) ? "../" : "";
    navigator.serviceWorker.register(`${prefix}sw.js`).catch(() => {});
  }
})();
