// Injected into every recorded page: a visible cursor and a highlight ring on each click.
(() => {
  if (window.__demoCursor) return;
  window.__demoCursor = true;
  const css = `
    #__cur { position: fixed; left: 0; top: 0; width: 26px; height: 26px; z-index: 2147483647; pointer-events: none;
             transform: translate(-3px, -2px); transition: transform 0.08s; filter: drop-shadow(0 2px 3px rgba(0,0,0,.35)); }
    #__cur.down { transform: translate(-3px, -2px) scale(0.88); }
    .__ring { position: fixed; width: 18px; height: 18px; margin: -9px 0 0 -9px; border-radius: 50%; z-index: 2147483646;
              pointer-events: none; border: 3px solid #2f9c80; background: rgba(47,156,128,.18);
              animation: __ring .65s ease-out forwards; }
    @keyframes __ring { to { width: 64px; height: 64px; margin: -32px 0 0 -32px; opacity: 0; } }`;
  const svg = `<svg viewBox="0 0 24 24" width="26" height="26"><path d="M3 2l7.5 19 2.6-7.6L21 10.8z" fill="#111" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>`;
  function mount() {
    const style = document.createElement("style");
    style.textContent = css;
    document.head.appendChild(style);
    const cur = document.createElement("div");
    cur.id = "__cur";
    cur.innerHTML = svg;
    const pos = window.__curPos || { x: -100, y: -100 };
    cur.style.left = pos.x + "px";
    cur.style.top = pos.y + "px";
    document.body.appendChild(cur);
    document.addEventListener("mousemove", (e) => {
      cur.style.left = e.clientX + "px";
      cur.style.top = e.clientY + "px";
    }, true);
    document.addEventListener("mousedown", (e) => {
      cur.classList.add("down");
      const ring = document.createElement("div");
      ring.className = "__ring";
      ring.style.left = e.clientX + "px";
      ring.style.top = e.clientY + "px";
      document.body.appendChild(ring);
      setTimeout(() => ring.remove(), 700);
    }, true);
    document.addEventListener("mouseup", () => cur.classList.remove("down"), true);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount);
  else mount();
})();
