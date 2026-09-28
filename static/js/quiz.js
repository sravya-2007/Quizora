const form = document.getElementById("quiz-form");
const cards = document.querySelectorAll(".qcard");
const prev = document.getElementById("prev-btn"), next = document.getElementById("next-btn");
const finish = document.getElementById("finish-btn"), bar = document.getElementById("progress-bar");
const cur = document.getElementById("q-current"), timer = document.getElementById("timer");
let i = 0, left = parseInt(form.dataset.seconds, 10), submitted = false;

function show() {
  cards.forEach((c, n) => c.hidden = n !== i);
  cur.textContent = i + 1;
  bar.style.width = ((i + 1) / cards.length * 100) + "%";
  prev.disabled = i === 0;
  next.hidden = i === cards.length - 1;
  finish.hidden = i !== cards.length - 1;
}
function submitQuiz() {
  if (submitted) return;
  submitted = true;
  finish.disabled = true;
  form.submit();
}
function tick() {
  const m = String(Math.floor(left / 60)).padStart(2, "0"), s = String(left % 60).padStart(2, "0");
  timer.textContent = m + ":" + s;
  if (left <= 0) { clearInterval(t); submitQuiz(); }
  left--;
}
prev.onclick = () => { if (i > 0) { i--; show(); } };
next.onclick = () => { if (i < cards.length - 1) { i++; show(); } };
form.addEventListener("submit", e => { if (submitted) e.preventDefault(); submitted = true; });
show(); tick();
const t = setInterval(tick, 1000);
