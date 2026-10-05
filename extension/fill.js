// Job Copilot form helper: fills an employer's application form from your kit.
// Runs only when you click "Fill this page" in the extension. It never submits:
// it never calls form.submit()/requestSubmit() and never clicks a button. The only
// clicks are on a radio option or a dropdown option, to choose an answer.
(() => {
  if (window.__jobCopilotFill) return;

  const GREEN = "2px solid #2e7d32";
  const AMBER = "2px solid #f9a825";
  // Voluntary self-identification and anti-bot fields are never touched.
  const NEVER = /gender|race|ethnic|hispanic|latino|veteran|disabilit|pronoun|sexual orientation|captcha/i;

  // Canonical kit keys, matched against a field's label (lower case), first match wins.
  const RULES = [
    ["first_name", /\b(first|given) name\b/],
    ["last_name", /\b(last|family) name\b|\bsurname\b/],
    ["full_name", /^(your )?(full |legal )?name\b/],
    ["email", /e-?mail/],
    ["phone", /phone|mobile/],
    ["linkedin", /linkedin/],
    ["github", /github/],
    ["portfolio", /portfolio|personal (web)?site|^website/],
    ["current_company", /current (company|employer)|^company\b|^org(anization)?\b/],
    ["current_title", /current (job )?(title|role|position)|^job title/],
    ["school", /\b(school|university|college|institution)\b/],
    ["degree", /\bdegree\b/],
    ["authorized_to_work", /authori[sz]ed to work|eligible to work|right to work|legally (able|permitted) to work/],
    ["needs_sponsorship", /sponsor/],
    ["location", /^(current )?(location|city)\b|where are you (based|located)|^address/],
  ];

  // Most specific question container first: closest() with one combined selector would
  // stop at a radio option's own <li> instead of the question around it.
  const CONTAINERS = [".application-question", "fieldset", "[role='radiogroup']", "[role='group']",
                      "[class*='question']", ".field", ".form-group", "li"];
  const LABELS = ["legend", ".application-label", "label", ".text", "[class*='label']"];

  const norm = (s) => (s || "").replace(/[*✱]/g, "").replace(/\s+/g, " ").trim().toLowerCase();
  const words = (s) => new Set(norm(s).split(/[^a-z0-9]+/).filter((w) => w.length > 2));
  const firstLine = (s) => (s || "").trim().split(/\r?\n/)[0];

  function containerOf(el) {
    for (const selector of CONTAINERS) {
      const box = el.closest(selector);
      if (box) return box;
    }
    return null;
  }

  function questionText(box) {
    for (const selector of LABELS) {
      const lab = box.querySelector(selector);
      if (lab && lab.innerText.trim()) return firstLine(lab.innerText);
    }
    return "";
  }

  function labelOf(el) {
    if (el.getAttribute("aria-label")) return el.getAttribute("aria-label");
    const by = el.getAttribute("aria-labelledby");
    if (by) {
      const text = by.split(" ").map((id) => document.getElementById(id)?.innerText || "").join(" ");
      if (text.trim()) return text;
    }
    if (el.id) {
      const lab = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
      if (lab && lab.innerText.trim()) return lab.innerText;
    }
    const box = containerOf(el);
    if (box && questionText(box)) return questionText(box);
    return el.placeholder || el.name || "";
  }

  function answerFor(label, kit) {
    const text = norm(label);
    if (!text || NEVER.test(text) || /preferred name|nickname/.test(text)) return null;
    for (const [key, pattern] of RULES) {
      if (pattern.test(text)) return kit.fields[key] || null;
    }
    // A question you answered before: most of its words match.
    const asked = words(text);
    let best = null;
    let bestScore = 0;
    for (const { question, answer } of kit.answers || []) {
      const known = words(question);
      if (!known.size || !asked.size) continue;
      let shared = 0;
      known.forEach((w) => { if (asked.has(w)) shared += 1; });
      const score = shared / Math.max(known.size, asked.size);
      if (score > bestScore) { best = answer; bestScore = score; }
    }
    return bestScore >= 0.6 ? best : null;
  }

  function setText(el, value) {
    const proto = el.tagName === "TEXTAREA" ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto, "value").set.call(el, value); // works with React-controlled inputs
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    el.dispatchEvent(new Event("blur", { bubbles: true }));
  }

  const same = (a, b) => norm(a) === norm(b) || (norm(b).length <= 3 && norm(a).startsWith(norm(b)));

  function chooseSelect(el, value) {
    const option = [...el.options].find((o) => o.value && (same(o.text, value) || same(o.value, value)));
    if (!option) return false;
    el.value = option.value;
    el.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  }

  function chooseRadio(radios, value) {
    const pick = radios.find((r) => same(r.value, value) || same(r.closest("label")?.innerText, value));
    if (!pick) return false;
    pick.click(); // choosing an answer, not submitting
    return true;
  }

  async function chooseCombo(el, value) {
    el.focus();
    setText(el, value);
    el.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }));
    await new Promise((r) => setTimeout(r, 300));
    const options = [...document.querySelectorAll("[role='option'], .select__option")];
    const pick = options.find((o) => same(o.innerText, value));
    if (!pick) { setText(el, ""); return false; }
    pick.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    pick.click(); // choosing an answer, not submitting
    return true;
  }

  const visible = (el) => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
  const outline = (el, ok) => { (el.type === "file" ? el.parentElement || el : el).style.outline = ok ? GREEN : AMBER; };

  window.__jobCopilotFill = async (kit) => {
    const filled = [];
    const left = [];
    const groups = new Map();
    const fields = [...document.querySelectorAll("input, textarea, select")]
      .filter((el) => !["hidden", "submit", "button", "reset", "image"].includes(el.type) && !el.disabled);

    for (const el of fields) {
      if (el.type === "radio" || el.type === "checkbox") {
        if (!groups.has(el.name)) groups.set(el.name, []);
        groups.get(el.name).push(el);
        continue;
      }
      const label = labelOf(el);
      if (el.type === "file") {
        if (/resume|cv/i.test(`${label} ${el.id} ${el.name}`)) { outline(el, false); left.push("Resume (attach your tailored resume)"); }
        continue;
      }
      if (NEVER.test(label) || /captcha/i.test(`${el.id} ${el.name}`)) continue;
      if (!visible(el) && el.getAttribute("role") !== "combobox") continue;
      if (el.value && el.value.trim()) continue; // never overwrite what's there
      const required = el.required || el.getAttribute("aria-required") === "true" || /[*✱]\s*$/.test(label.trim());
      const value = answerFor(label, kit);
      let ok = false;
      if (value) {
        if (el.tagName === "SELECT") ok = chooseSelect(el, value);
        else if (el.getAttribute("role") === "combobox") ok = await chooseCombo(el, value);
        else { setText(el, value); ok = true; }
      }
      if (ok) { outline(el, true); filled.push(norm(label)); }
      else if (required) { outline(el, false); left.push(firstLine(label).slice(0, 80)); }
    }

    for (const [, radios] of groups) {
      if (radios.some((r) => r.checked)) continue;
      const box = containerOf(radios[0]);
      const question = (box && questionText(box)) || radios[0].name;
      if (NEVER.test(question)) continue;
      const value = answerFor(question, kit);
      const ok = value ? chooseRadio(radios, value) : false;
      (box || radios[0]).style.outline = ok ? GREEN : AMBER;
      (ok ? filled : left).push(firstLine(question).slice(0, 80));
    }

    showPanel(filled.length, left);
    return { filled: filled.length, left };
  };

  function showPanel(count, left) {
    document.getElementById("job-copilot-panel")?.remove();
    const panel = document.createElement("div");
    panel.id = "job-copilot-panel";
    panel.setAttribute("role", "status");
    panel.style.cssText = "position:fixed;right:16px;bottom:16px;z-index:2147483647;max-width:340px;background:#fff;" +
      "color:#1b1f24;border:1px solid #c9d1d9;border-radius:6px;padding:12px 14px;font:14px/1.4 system-ui,sans-serif;" +
      "box-shadow:0 4px 16px rgba(0,0,0,.15)";
    const title = document.createElement("strong");
    title.textContent = `Job Copilot filled ${count} field${count === 1 ? "" : "s"}. Nothing was submitted.`;
    const note = document.createElement("p");
    note.style.margin = "6px 0";
    note.textContent = left.length
      ? `Left for you (amber): ${left.slice(0, 6).join("; ")}${left.length > 6 ? "…" : ""}. Check every field, then submit yourself.`
      : "Check every field, then submit on this page yourself.";
    const close = document.createElement("button");
    close.type = "button";
    close.textContent = "Close";
    close.addEventListener("click", () => panel.remove());
    panel.append(title, note, close);
    document.body.appendChild(panel);
  }
})();
