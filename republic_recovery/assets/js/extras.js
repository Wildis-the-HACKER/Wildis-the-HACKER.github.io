(() => {
  "use strict";
  const body = document.body;
  const ratButton = document.getElementById("rat-toggle");
  const mutationButton = document.getElementById("mutation-toggle");
  const customButton = document.getElementById("custom-toggle");
  const status = document.getElementById("extras-status");
  const overlay = document.getElementById("royal-overlay");
  let rat = false, mutation = false, custom = false, pointer = null;

  function removePointer() {
    if (pointer) pointer.remove();
    pointer = null;
    body.classList.remove("rr-rat-mode","rr-custom-mode");
  }
  function createPointer(kind) {
    removePointer();
    if (kind === "rat") {
      pointer=document.createElement("div"); pointer.className="rr-rat-pointer";
      pointer.textContent="🐀"; pointer.setAttribute("aria-hidden","true");
      body.append(pointer); body.classList.add("rr-rat-mode");
    } else if (kind === "custom") {
      pointer=document.createElement("div"); pointer.className="rr-custom-pointer";
      pointer.setAttribute("aria-hidden","true"); body.append(pointer); body.classList.add("rr-custom-mode");
    }
  }
  document.addEventListener("pointermove",event => {
    if (pointer) { pointer.style.left=`${event.clientX}px`; pointer.style.top=`${event.clientY}px`; }
  });
  function sync() {
    ratButton.setAttribute("aria-pressed",String(rat));
    mutationButton.setAttribute("aria-pressed",String(mutation));
    customButton.setAttribute("aria-pressed",String(custom));
    ratButton.textContent=rat?"Disable Rat Cursor":"Enable Rat Cursor";
    mutationButton.textContent=mutation?"Restore My Mouse":"Mutate My Mouse";
    customButton.textContent=custom?"Disable Custom Cursor":"Enable Custom Cursor";
    body.classList.toggle("rr-mutation-mode",mutation);
    if (rat) createPointer("rat"); else if (custom) createPointer("custom"); else removePointer();
    const active=[];
    if (rat) active.push("Rat Cursor");
    if (mutation) active.push("Mouse Mutation");
    if (custom) active.push("Custom Cursor");
    status.textContent=active.length ? `Active: ${active.join(", ")}.` : "All effects are off.";
  }
  ratButton.addEventListener("click",()=>{ rat=!rat; if(rat) custom=false; sync(); });
  customButton.addEventListener("click",()=>{ custom=!custom; if(custom) rat=false; sync(); });
  mutationButton.addEventListener("click",()=>{ mutation=!mutation; sync(); });
  document.getElementById("reset-effects").addEventListener("click",()=>{ rat=false; mutation=false; custom=false; sync(); });
  document.getElementById("royal-emergency").addEventListener("click",()=>{ overlay.classList.remove("rr-hidden"); document.getElementById("dismiss-royal").focus(); });
  document.getElementById("dismiss-royal").addEventListener("click",()=>overlay.classList.add("rr-hidden"));
  overlay.addEventListener("click",event=>{ if(event.target===overlay) overlay.classList.add("rr-hidden"); });
  document.addEventListener("keydown",event=>{ if(event.key==="Escape") overlay.classList.add("rr-hidden"); });
  sync();
})();
