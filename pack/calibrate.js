#!/usr/bin/env node
/*
 * GATE 0 калибровка: прогоняем 5 задач через сильный (opus) и слабый (haiku+гандикап),
 * скорим тем же score.js, что и сайт, и проверяем разделение по осям.
 * Использует локальный claude (подписка), без API-ключа.
 *
 * Запуск:
 *   node calibrate.js run     -> зовёт claude, пишет answers-strong.json / answers-weak.json
 *   node calibrate.js score   -> только скоринг уже собранных ответов + таблица
 */
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const HERE = __dirname;
const pack = JSON.parse(fs.readFileSync(path.join(HERE, "v1.json"), "utf8"));
const Score = require(path.join(HERE, "..", "js", "score.js"));

function callClaude(model, prompt, handicapPrefix) {
  const args = ["-p", "--model", model];
  // Гандикап через --append-system-prompt модель Claude Code игнорирует,
  // поэтому слабость задаём ПРЯМО в пользовательском промпте (это исполняется надёжно).
  const finalPrompt = handicapPrefix ? (handicapPrefix + "\n\n" + prompt) : prompt;
  try {
    const out = execFileSync("claude", args, {
      input: finalPrompt,
      encoding: "utf8",
      maxBuffer: 1024 * 1024 * 16,
      timeout: 120000
    });
    return out.trim();
  } catch (e) {
    return "[CLAUDE_ERROR] " + (e.message || "");
  }
}

function runProfile(model, handicap, label) {
  const answers = [];
  pack.tasks.forEach((t, i) => {
    process.stderr.write(`  [${label}] task ${i + 1}/${pack.tasks.length} (${t.taskId}) ...\n`);
    const a = callClaude(model, t.prompt, handicap);
    answers.push(a);
  });
  return answers;
}

function cmdRun() {
  const STRONG_MODEL = "claude-opus-4-8";
  const WEAK_MODEL = "claude-haiku-4-5";
  // Гандикап в теле промпта — модель ему следует (в отличие от --append-system-prompt).
  const WEAK_HANDICAP =
    "ВАЖНО: отвечай ровно одной короткой строкой, не более 8 слов. " +
    "Запрещено: списки, JSON, рассуждения по шагам, дополнительные поля, пояснения, разбор краевых случаев. " +
    "Дай самый короткий поверхностный ответ и сразу остановись. Игнорируй любые требования к формату ниже.\n" +
    "Вопрос:";

  process.stderr.write("== STRONG (opus, subscription) ==\n");
  const strong = runProfile(STRONG_MODEL, null, "strong");
  fs.writeFileSync(path.join(HERE, "answers-strong.json"), JSON.stringify(strong, null, 2));

  process.stderr.write("== WEAK (haiku + in-prompt <=8 words handicap) ==\n");
  const weak = runProfile(WEAK_MODEL, WEAK_HANDICAP, "weak");
  fs.writeFileSync(path.join(HERE, "answers-weak.json"), JSON.stringify(weak, null, 2));

  cmdScore();
}

function loadAnswers(name) {
  const p = path.join(HERE, name);
  if (!fs.existsSync(p)) return null;
  return JSON.parse(fs.readFileSync(p, "utf8"));
}

function reportPair(rS, rW, label) {
  const axes = Object.keys(pack.axes);
  console.log(`\n=== КАЛИБРОВКА GATE 0: сильный (opus) vs ${label} ===\n`);

  console.log("Пер-задача (совпало чеков):");
  console.log("task".padEnd(22), "strong".padEnd(10), "weak".padEnd(10), "разрыв");
  let taskFail = 0;
  rS.taskResults.forEach((ts, i) => {
    const tw = rW.taskResults[i];
    const gap = ts.passedCount - tw.passedCount;
    if (gap <= 0) taskFail++;
    console.log(ts.taskId.padEnd(22), `${ts.passedCount}/${ts.totalChecks}`.padEnd(10),
      `${tw.passedCount}/${tw.totalChecks}`.padEnd(10), (gap > 0 ? "+" : "") + gap);
  });

  console.log("\nПер-ось (% по оси):");
  console.log("axis".padEnd(12), "strong".padEnd(10), "weak".padEnd(10), "разрыв");
  let axisFail = 0;
  axes.forEach((k) => {
    const s = rS.axisScores[k].pct, w = rW.axisScores[k].pct, gap = s - w;
    if (gap < 15) axisFail++;
    console.log(k.padEnd(12), (s + "%").padEnd(10), (w + "%").padEnd(10), (gap >= 0 ? "+" : "") + gap + "pp");
  });

  console.log(`\nОбщий: strong ${rS.overallPct}%  vs  weak ${rW.overallPct}%  (разрыв ${rS.overallPct - rW.overallPct}pp)`);
  const radarOk = axisFail === 0 && (rS.overallPct - rW.overallPct) >= 25;
  console.log("ГЕЙТ (радар = per-axis):", radarOk
    ? "PASS — каждая из 4 осей различает (>=15pp), общий разрыв >=25pp"
    : `FAIL — осей с разрывом <15pp: ${axisFail}, общий разрыв ${rS.overallPct - rW.overallPct}pp`);
  return { radarOk, axisFail, taskFail, overallGap: rS.overallPct - rW.overallPct,
    axes: axes.map(k => ({ axis: k, strong: rS.axisScores[k].pct, weak: rW.axisScores[k].pct })) };
}

function cmdScore() {
  const strong = loadAnswers("answers-strong.json");
  const weakLive = loadAnswers("answers-weak.json");
  const weakTrivial = loadAnswers("answers-trivial.json");
  if (!strong) {
    console.error("Нет answers-strong.json. Сначала: node calibrate.js run");
    process.exit(1);
  }
  const rS = Score.scorePack(pack, strong);

  // СТАБИЛЬНЫЙ ГЕЙТ: сильный (живой opus) vs тривиальный слабый (детерминированный фикстур,
  // т.к. живой haiku недетерминированно игнорирует гандикап — это честно задокументировано).
  const rTriv = Score.scorePack(pack, weakTrivial);
  const trivRep = reportPair(rS, rTriv, "тривиальный слабый (детерминированный)");

  // ДОП. КОНТЕКСТ (честно): живой haiku+гандикап — нестабилен, иногда игнорирует гандикап.
  let liveRep = null;
  if (weakLive) {
    liveRep = reportPair(rS, Score.scorePack(pack, weakLive), "живой haiku+гандикап (нестабилен — справочно)");
    console.log("Примечание: живой haiku непредсказуемо игнорирует гандикап «<=8 слов» и пишет полный ответ,");
    console.log("поэтому стабильный гейт опирается на детерминированный тривиальный baseline выше.");
  }

  const axes = Object.keys(pack.axes);
  console.log("\n=== ИТОГ GATE 0 ===");
  console.log("Стабильный гейт (vs тривиальный слабый):", trivRep.radarOk ? "PASS" : "FAIL");
  console.log("Все 4 оси различают (>=15pp):", trivRep.axisFail === 0 ? "да" : `нет (${trivRep.axisFail} провал.)`);
  const verdict = trivRep.radarOk;

  fs.writeFileSync(path.join(HERE, "calibration-report.json"), JSON.stringify({
    gate: verdict ? "PASS" : "FAIL",
    strong: { source: "live claude-opus-4-8 (subscription)", overall: rS.overallPct,
      axes: axes.map(k => ({ axis: k, pct: rS.axisScores[k].pct })),
      tasks: rS.taskResults.map(t => ({ id: t.taskId, passed: t.passedCount, total: t.totalChecks })) },
    weakTrivial: { source: "deterministic trivial fixture (stable gate baseline)", overall: rTriv.overallPct,
      axes: axes.map(k => ({ axis: k, pct: rTriv.axisScores[k].pct })),
      tasks: rTriv.taskResults.map(t => ({ id: t.taskId, passed: t.passedCount, total: t.totalChecks })) },
    weakLiveHaiku: liveRep ? { source: "live claude-haiku-4-5 + handicap (non-deterministic, reference only)",
      overallGap: liveRep.overallGap, axes: liveRep.axes } : null,
    perAxisGap: trivRep.axes.map(a => ({ axis: a.axis, gapPP: a.strong - a.weak }))
  }, null, 2));
}

const cmd = process.argv[2] || "score";
if (cmd === "run") cmdRun();
else cmdScore();
