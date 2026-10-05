// Popup: keeps the kit on this computer only (chrome.storage.local) and fills on request.
const $ = (id) => document.getElementById(id);
// Application forms that company career sites embed from another address. Reaching inside them
// needs a permission for that address, asked for only when you click "Allow" (decision 030).
const EMBEDDED_FORMS = chrome.runtime.getManifest().optional_host_permissions;
const embeddedFrom = (src) => EMBEDDED_FORMS.some((pattern) => matchesHostPattern(pattern, src)); // match.js
const say = (text) => { $("status").textContent = text; };

function parseKit(text) {
  const kit = JSON.parse(text);
  if (kit.jobCopilotKit !== 1 || typeof kit.fields !== "object") throw new Error("not a Job Copilot helper code");
  return kit;
}

async function showSaved() {
  const { kit } = await chrome.storage.local.get("kit");
  $("who").textContent = kit
    ? `Kit saved for ${kit.fields.first_name || kit.fields.full_name || "you"} (${Object.keys(kit.fields).length} answers).`
    : "No kit saved yet.";
  return kit;
}

$("save").addEventListener("click", async () => {
  try {
    const kit = parseKit($("code").value.trim());
    await chrome.storage.local.set({ kit });
    $("code").value = "";
    await $("allow").addEventListener("click", async () => {
  // Called straight from the click, as Chrome requires for a permission request.
  const granted = await chrome.permissions.request({ origins: EMBEDDED_FORMS });
  $("allow-box").hidden = granted;
  say(granted ? "Allowed. Click Fill this page again." : "Not allowed. You can still fill the form yourself.");
});

showSaved();
    say("Saved.");
  } catch (error) {
    say(`That code didn't work: ${error.message}.`);
  }
});

$("forget").addEventListener("click", async () => {
  await chrome.storage.local.remove("kit");
  await showSaved();
  say("Your kit was removed from this browser.");
});

$("fill").addEventListener("click", async () => {
  const kit = await showSaved();
  if (!kit) { say("Save your kit first."); return; }
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  try {
    const [{ result: frames }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id }, func: () => [...document.querySelectorAll("iframe[src]")].map((f) => f.src),
    });
    const embedded = (frames || []).filter(embeddedFrom);
    const allowed = await chrome.permissions.contains({ origins: EMBEDDED_FORMS });
    $("allow-box").hidden = !(embedded.length && !allowed);
    await chrome.scripting.executeScript({ target: { tabId: tab.id, allFrames: true }, files: ["fill.js"] });
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id, allFrames: true },
      func: (k) => (window.__jobCopilotFill ? window.__jobCopilotFill(k) : { filled: 0, left: [] }),
      args: [kit],
    });
    const filled = results.reduce((n, r) => n + ((r.result && r.result.filled) || 0), 0);
    say(`Filled ${filled} field${filled === 1 ? "" : "s"}. Nothing was submitted.` +
      (embedded.length && !allowed ? " The application form is embedded from another site: allow it below, then click Fill again." : ""));
  } catch (error) {
    say(`Couldn't fill this page: ${error.message}`);
  }
});

showSaved();
