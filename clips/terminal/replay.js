// Types the prompt at a human pace, then reveals the output lines one by one.
function replay({ prompt, lines, typeMs = 28, lineMs = 260, startDelay = 700 }) {
  const body = document.getElementById("body");
  const user = document.createElement("span");
  user.className = "user";
  const caret = document.createElement("span");
  caret.className = "caret";
  body.innerHTML = '<span class="prompt">&gt; </span>';
  body.appendChild(user);
  body.appendChild(caret);
  let i = 0;
  setTimeout(function type() {
    if (i < prompt.length) {
      user.textContent += prompt[i++];
      setTimeout(type, prompt[i - 1] === " " ? typeMs * 0.6 : typeMs);
      return;
    }
    caret.remove();
    let j = 0;
    setTimeout(function show() {
      if (j < lines.length) {
        const [cls, text] = lines[j++];
        const div = document.createElement("div");
        div.className = cls;
        div.textContent = text || " ";
        body.appendChild(div);
        setTimeout(show, cls === "gap" ? lineMs / 2 : lineMs);
        return;
      }
      document.body.dataset.done = "1";
    }, 600);
  }, startDelay);
}
