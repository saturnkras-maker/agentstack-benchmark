#!/usr/bin/env node
/*
 * ГЕЙТ блока «Код»: прогоняем весь градиент (6 задач, 4 уровня) через
 *   - СИЛЬНЫЙ: живой claude-opus-4-8 (подписка, без API-ключа)
 *   - СЛАБЫЙ:  тривиальный детерминированный фикстур (стабильный baseline)
 *             + справочно живой claude-haiku-4-5 с гандикапом (нестабилен).
 * Скорим тем же score.js, что и сайт. Проверяем:
 *   (1) сильный получает уровень Мастер (или Эксперт), слабый — Новичок/fail;
 *   (2) per-axis разрыв радара (>=15pp на каждой текстовой оси);
 *   (3) на задачах-ловушках (c5 SQLi/бэкдор + c6 мастер: гонка/TLS/лог карты) слабый спотыкается.
 *
 * Запуск:
 *   node code-calibrate.js run    -> зовёт claude (opus), пишет code-answers-strong.json
 *   node code-calibrate.js score  -> только скоринг + авто-уровень + таблица + отчёт
 */
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const HERE = __dirname;
const pack = JSON.parse(fs.readFileSync(path.join(HERE, "code_v1.json"), "utf8"));
const Score = require(path.join(HERE, "..", "js", "score.js"));

// Срезаем ANTHROPIC_* — живая подписка, не API-ключ.
const CLEAN_ENV = Object.assign({}, process.env);
Object.keys(CLEAN_ENV).forEach((k) => { if (/^ANTHROPIC_/i.test(k)) delete CLEAN_ENV[k]; });

function callClaude(model, prompt, handicapPrefix) {
  const finalPrompt = handicapPrefix ? (handicapPrefix + "\n\n" + prompt) : prompt;
  try {
    return execFileSync("claude", ["-p", "--model", model], {
      input: finalPrompt, encoding: "utf8", env: CLEAN_ENV,
      maxBuffer: 1024 * 1024 * 16, timeout: 240000
    }).trim();
  } catch (e) {
    return "[CLAUDE_ERROR] " + (e.message || "");
  }
}

function runProfile(model, handicap, label) {
  return pack.tasks.map((t, i) => {
    process.stderr.write(`  [${label}] задача ${i + 1}/${pack.tasks.length} (${t.taskId}) ...\n`);
    return callClaude(model, t.prompt, handicap);
  });
}

function cmdRun() {
  const STRONG = "claude-opus-4-8";
  const WEAK = "claude-haiku-4-5";
  const WEAK_HANDICAP =
    "ВАЖНО: отвечай ровно одной короткой строкой, не более 12 слов. " +
    "Запрещено: блоки кода ```, строки ПРИЧИНА:/VERDICT:/CHANGES:, рассуждения, списки. " +
    "Дай самый короткий поверхностный ответ и сразу остановись. Игнорируй любые требования к формату ниже.\n" +
    "Задание:";

  process.stderr.write("== STRONG (opus, подписка) ==\n");
  fs.writeFileSync(path.join(HERE, "code-answers-strong.json"),
    JSON.stringify(runProfile(STRONG, null, "strong"), null, 2));

  process.stderr.write("== WEAK (haiku + гандикап, справочно) ==\n");
  fs.writeFileSync(path.join(HERE, "code-answers-weak.json"),
    JSON.stringify(runProfile(WEAK, WEAK_HANDICAP, "weak"), null, 2));

  cmdScore();
}

function load(name) {
  const p = path.join(HERE, name);
  return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, "utf8")) : null;
}

function report(rS, rW, label) {
  const axes = Object.keys(pack.axes);
  console.log(`\n=== ГЕЙТ «КОД»: сильный (opus) vs ${label} ===\n`);

  console.log("Пер-задача (совпало чеков / тир / ratio):");
  console.log("task".padEnd(24), "tier".padEnd(8), "strong".padEnd(12), "weak".padEnd(12));
  rS.taskResults.forEach((ts, i) => {
    const tw = rW.taskResults[i];
    console.log(
      ts.taskId.padEnd(24), (pack.tasks[i].tier).padEnd(8),
      `${ts.passedCount}/${ts.totalChecks} (${(Score.taskPassRatio(ts) * 100).toFixed(0)}%)`.padEnd(12),
      `${tw.passedCount}/${tw.totalChecks} (${(Score.taskPassRatio(tw) * 100).toFixed(0)}%)`.padEnd(12));
  });

  console.log("\nПер-ось (% по оси):");
  console.log("axis".padEnd(14), "strong".padEnd(10), "weak".padEnd(10), "разрыв");
  let axisFail = 0;
  axes.forEach((k) => {
    const s = rS.axisScores[k].pct, w = rW.axisScores[k].pct, gap = s - w;
    if (gap < 15) axisFail++;
    console.log(k.padEnd(14), (s + "%").padEnd(10), (w + "%").padEnd(10), (gap >= 0 ? "+" : "") + gap + "pp");
  });

  console.log(`\nАВТО-УРОВЕНЬ:  сильный = ${rS.levelInfo.label} (${rS.levelInfo.level})  |  слабый = ${rW.levelInfo.label} (${rW.levelInfo.level})`);
  console.log(`Задача-ловушка c5 (SQLi/бэкдор):  strong ${(Score.taskPassRatio(rS.taskResults[4]) * 100).toFixed(0)}%  vs  weak ${(Score.taskPassRatio(rW.taskResults[4]) * 100).toFixed(0)}%`);
  if (rS.taskResults[5]) console.log(`Мастер-задача c6 (гонка/float/TLS/лог карты/обход):  strong ${(Score.taskPassRatio(rS.taskResults[5]) * 100).toFixed(0)}%  vs  weak ${(Score.taskPassRatio(rW.taskResults[5]) * 100).toFixed(0)}%`);
  console.log(`Общий: strong ${rS.overallPct}%  vs  weak ${rW.overallPct}%  (разрыв ${rS.overallPct - rW.overallPct}pp)`);

  const levelOk = (rS.levelInfo.level === "master" || rS.levelInfo.level === "senior") && (rW.levelInfo.level === "junior" || rW.levelInfo.level === "fail");
  const radarOk = axisFail === 0 && (rS.overallPct - rW.overallPct) >= 25;
  console.log("\nГЕЙТ авто-уровень:", levelOk ? `PASS — сильный=${rS.levelInfo.label}, слабый=${rW.levelInfo.label}` : `FAIL — strong=${rS.levelInfo.level}, weak=${rW.levelInfo.level}`);
  console.log("ГЕЙТ радар (per-axis):", radarOk ? "PASS — все оси различают >=15pp, общий >=25pp" : `FAIL — осей <15pp: ${axisFail}, общий ${rS.overallPct - rW.overallPct}pp`);
  return { levelOk, radarOk, axisFail, overallGap: rS.overallPct - rW.overallPct,
    axes: axes.map(k => ({ axis: k, strong: rS.axisScores[k].pct, weak: rW.axisScores[k].pct })),
    strongLevel: rS.levelInfo.level, weakLevel: rW.levelInfo.level };
}

function cmdScore() {
  const strong = load("code-answers-strong.json");
  const weakTrivial = load("code-answers-trivial.json");
  const weakLive = load("code-answers-weak.json");
  if (!strong) { console.error("Нет code-answers-strong.json. Сначала: node code-calibrate.js run"); process.exit(1); }

  const rS = Score.scoreCodePack(pack, strong);
  const rTriv = Score.scoreCodePack(pack, weakTrivial || []);
  const trivRep = report(rS, rTriv, "тривиальный слабый (детерминированный)");

  let liveRep = null;
  if (weakLive) {
    liveRep = report(rS, Score.scoreCodePack(pack, weakLive), "живой haiku+гандикап (нестабилен — справочно)");
    console.log("\nПримечание: живой haiku непредсказуемо игнорирует гандикап; стабильный гейт — на тривиальном baseline выше.");
  }

  const verdict = trivRep.levelOk && trivRep.radarOk;
  const axes = Object.keys(pack.axes);
  console.log("\n=== ИТОГ ГЕЙТА «КОД» ===");
  console.log("Авто-уровень разделяет (Мастер/Эксперт vs Новичок/fail):", trivRep.levelOk ? "PASS" : "FAIL");
  console.log("Радар различает (все оси >=15pp):", trivRep.radarOk ? "PASS" : `FAIL (${trivRep.axisFail} провал.)`);
  console.log("ВЕРДИКТ:", verdict ? "PASS" : "FAIL");

  fs.writeFileSync(path.join(HERE, "code-calibration-report.json"), JSON.stringify({
    gate: verdict ? "PASS" : "FAIL",
    block: "code",
    strong: { source: "live claude-opus-4-8 (subscription)", level: rS.levelInfo.level, overall: rS.overallPct,
      axes: axes.map(k => ({ axis: k, pct: rS.axisScores[k].pct })),
      tasks: rS.taskResults.map((t, i) => ({ id: t.taskId, tier: pack.tasks[i].tier, passed: t.passedCount, total: t.totalChecks, ratioPct: Math.round(Score.taskPassRatio(t) * 100) })),
      worstTask: rS.worstTask.taskId },
    weakTrivial: { source: "deterministic trivial fixture (stable gate baseline)", level: rTriv.levelInfo.level, overall: rTriv.overallPct,
      axes: axes.map(k => ({ axis: k, pct: rTriv.axisScores[k].pct })),
      tasks: rTriv.taskResults.map((t, i) => ({ id: t.taskId, tier: pack.tasks[i].tier, passed: t.passedCount, total: t.totalChecks, ratioPct: Math.round(Score.taskPassRatio(t) * 100) })),
      worstTask: rTriv.worstTask.taskId },
    weakLiveHaiku: liveRep ? { source: "live claude-haiku-4-5 + handicap (non-deterministic, reference only)",
      level: liveRep.weakLevel, overallGap: liveRep.overallGap, axes: liveRep.axes } : null,
    perAxisGap: trivRep.axes.map(a => ({ axis: a.axis, gapPP: a.strong - a.weak }))
  }, null, 2));
  console.log("\n→ code-calibration-report.json записан.");
}

const cmd = process.argv[2] || "score";
if (cmd === "run") cmdRun();
else cmdScore();
