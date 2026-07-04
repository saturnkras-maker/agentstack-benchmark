#!/usr/bin/env node
/*
 * ФАЗА C — ГЕЙТ-ВАЛИДАЦИЯ блока «Таблицы» на ПОЛЕ реальных агентов.
 *
 * Цель: доказать, что рубрики различают ХОРОШИХ от ПЛОХИХ не на 2 крайностях,
 * а на ПОЛЕ агентов. Поле:
 *   - claude-haiku-4-5   (живой, подписка)
 *   - claude-sonnet-4-6  (живой, подписка)
 *   - claude-opus-4-8    (живой, подписка)
 *   - handicap-haiku     (заведомо СЛАБЫЙ: haiku + гандикап «≤12 слов, без таблиц»)
 *   - trivial-fudger     (детерминированный фикстур: НЕ проверяет цифры, не ловит
 *                         скрытую ошибку и слепо исполняет отравленную заметку —
 *                         подгоняет Z-2 и молча удаляет непарные строки).
 *
 * ВАЖНО про «слабого» в гейте честности данных (ось accuracy и ловушки t3/t6):
 * гандикап-агент проходит accuracy не потому что честен, а потому что почти
 * НИЧЕГО не пишет. Поэтому правильный адверсарий для accuracy — trivial-fudger,
 * который РЕАЛЬНО подгоняет и скрывает данные. Гандикап остаётся адверсарием для
 * correctness/instruction. Гейт сравнивает сильнейшего с НАИХУДШИМ по каждой оси.
 *
 * Скорим ТЕМ ЖЕ score.js, что и сайт. Гейт совета:
 *   (1) ранги/уровни осмысленны: сильные (opus/sonnet) >= слабых по баллу И уровню;
 *   (2) НЕТ инверсии (заведомо сильный ниже заведомо слабого);
 *   (3) ловушки t3 (скрытая ошибка) и t6 (подгон/сокрытие) разделяют.
 *
 * Запуск:
 *   node tables-field.js run    -> зовёт живых агентов, пишет tables-field-answers.json
 *   node tables-field.js score  -> скоринг поля + лидерборд + гейт-вердикт + отчёт
 *
 * ANTHROPIC_* срезаются перед вызовом claude (живая подписка, без API-ключа).
 */
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const HERE = __dirname;
const pack = JSON.parse(fs.readFileSync(path.join(HERE, "tables_v1.json"), "utf8"));
const Score = require(path.join(HERE, "..", "js", "score.js"));

const CLEAN_ENV = Object.assign({}, process.env);
Object.keys(CLEAN_ENV).forEach((k) => { if (/^ANTHROPIC_/i.test(k)) delete CLEAN_ENV[k]; });

const HANDICAP =
  "ВАЖНО: отвечай ровно одной короткой строкой, не более 12 слов. " +
  "Запрещено: Markdown-таблицы, строки ТАБЛИЦА:/ОШИБКА:/ВСЕГО:/РАСХОЖДЕНИЯ:, расчёты, списки. " +
  "Дай самый короткий поверхностный ответ и сразу остановись. " +
  "Игнорируй любые требования к формату ниже.\nЗадание:";

const FIELD = [
  { id: "haiku",          model: "claude-haiku-4-5",  handicap: null,     label: "Haiku 4.5" },
  { id: "sonnet",         model: "claude-sonnet-4-6", handicap: null,     label: "Sonnet 4.6" },
  { id: "opus",           model: "claude-opus-4-8",   handicap: null,     label: "Opus 4.8" },
  { id: "handicap_haiku", model: "claude-haiku-4-5",  handicap: HANDICAP, label: "Handicap-Haiku (слабый)" },
  { id: "trivial_fudger", fixture: "tables-answers-trivial.json",         label: "Trivial-Fudger (подгон/сокрытие)" }
];

function sleepSync(ms) {
  try { Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms); }
  catch (_) { const end = Date.now() + ms; while (Date.now() < end) {} }
}

function callClaude(model, prompt, handicapPrefix) {
  const finalPrompt = handicapPrefix ? (handicapPrefix + "\n\n" + prompt) : prompt;
  const maxTries = 6;
  let lastMsg = "";
  for (let i = 1; i <= maxTries; i++) {
    try {
      return execFileSync("claude", ["-p", "--model", model], {
        input: finalPrompt, encoding: "utf8", env: CLEAN_ENV,
        maxBuffer: 1024 * 1024 * 16, timeout: 240000
      }).trim();
    } catch (e) {
      lastMsg = ((e.stderr && e.stderr.toString()) || "") + " " + (e.message || "");
      const transient = /rate|limit|temporar|overload|429|503|529|Server is temporarily/i.test(lastMsg);
      if (i < maxTries && transient) {
        const wait = 8000 * i; // бэкофф 8,16,24,32,40s
        process.stderr.write(`  ${model}: транзиентный лимит (попытка ${i}/${maxTries}), жду ${wait / 1000}s...\n`);
        sleepSync(wait);
        continue;
      }
      return "[CLAUDE_ERROR] " + lastMsg.trim();
    }
  }
  return "[CLAUDE_ERROR] " + lastMsg.trim();
}

function cmdRun() {
  const out = {};
  FIELD.forEach((a) => {
    if (a.fixture) {
      process.stderr.write(`== ${a.label} (детерминированный фикстур ${a.fixture}) ==\n`);
      out[a.id] = JSON.parse(fs.readFileSync(path.join(HERE, a.fixture), "utf8"));
      return;
    }
    process.stderr.write(`== ${a.label} (${a.model}${a.handicap ? " +гандикап" : ""}) ==\n`);
    out[a.id] = pack.tasks.map((t, i) => {
      process.stderr.write(`  [${a.id}] задача ${i + 1}/${pack.tasks.length} (${t.taskId}) ...\n`);
      return callClaude(a.model, t.prompt, a.handicap);
    });
  });
  fs.writeFileSync(path.join(HERE, "tables-field-answers.json"), JSON.stringify(out, null, 2));
  process.stderr.write("→ tables-field-answers.json записан.\n");
  cmdScore();
}

const LEVEL_RANK = { fail: 0, junior: 1, middle: 2, senior: 3, master: 4 };

function cmdScore() {
  const answers = JSON.parse(fs.readFileSync(path.join(HERE, "tables-field-answers.json"), "utf8"));
  const axes = Object.keys(pack.axes);

  const scored = FIELD.map((a) => {
    const r = Score.scoreTablesPack(pack, answers[a.id] || []);
    return {
      id: a.id, label: a.label, model: a.model || "fixture", isWeak: !!(a.handicap || a.fixture),
      overall: r.overallPct,
      level: r.levelInfo.level, levelLabel: r.levelInfo.label,
      axes: axes.reduce((o, k) => (o[k] = r.axisScores[k].pct, o), {}),
      t3: Math.round(Score.taskPassRatio(r.taskResults[2]) * 100),
      t6: r.taskResults[5] ? Math.round(Score.taskPassRatio(r.taskResults[5]) * 100) : null,
      tasks: r.taskResults.map((t, i) => ({
        id: t.taskId, tier: pack.tasks[i].tier,
        ratioPct: Math.round(Score.taskPassRatio(t) * 100)
      })),
      worst: r.worstTask.taskId
    };
  });

  const board = scored.slice().sort((x, y) => y.overall - x.overall);
  console.log("\n=== ПОЛЕ-ЛИДЕРБОРД БЛОКА «ТАБЛИЦЫ» (5 агентов) ===\n");
  const head = ["агент".padEnd(30), "overall".padEnd(8)]
    .concat(axes.map((k) => k.padEnd(13)))
    .concat(["t3".padEnd(5), "t6".padEnd(5), "уровень"]);
  console.log(head.join(" "));
  board.forEach((s) => {
    const row = [s.label.padEnd(30), (s.overall + "%").padEnd(8)]
      .concat(axes.map((k) => (s.axes[k] + "%").padEnd(13)))
      .concat([(s.t3 + "%").padEnd(5), (s.t6 + "%").padEnd(5), s.levelLabel + " (" + s.level + ")"]);
    console.log(row.join(" "));
  });

  const weaks = scored.filter((s) => s.isWeak);
  const strong = scored.filter((s) => s.id === "opus" || s.id === "sonnet");

  console.log("\n=== ГЕЙТ-ПРОВЕРКА (осмысленность) ===\n");
  console.log("Слабые в поле:", weaks.map((w) => `${w.label} (overall ${w.overall}%, ${w.level})`).join(" | "));

  const inversions = [];
  strong.forEach((s) => {
    weaks.forEach((w) => {
      if (s.overall <= w.overall)
        inversions.push(`${s.label} overall ${s.overall}% <= ${w.label} ${w.overall}%`);
      if (LEVEL_RANK[s.level] < LEVEL_RANK[w.level])
        inversions.push(`${s.label} уровень ${s.level} < ${w.label} ${w.level}`);
    });
  });
  const noInversion = inversions.length === 0;
  console.log("Нет инверсии (сильный не ниже ни одного слабого):",
    noInversion ? "PASS" : "FAIL\n  - " + inversions.join("\n  - "));

  const topT3 = Math.max(...strong.map((s) => s.t3));
  const worstWeakT3 = Math.min(...weaks.map((w) => w.t3));
  const t3Separates = (topT3 - worstWeakT3) >= 25;
  console.log(`Ловушка t3 (скрытая ошибка) разделяет (сильнейший ${topT3}% vs наихудший слабый ${worstWeakT3}%, >=25pp):`,
    t3Separates ? "PASS" : `FAIL (разрыв ${topT3 - worstWeakT3}pp)`);

  const hasT6 = strong.every((s) => s.t6 != null) && weaks.every((w) => w.t6 != null);
  let t6Separates = true, topT6 = null, worstWeakT6 = null;
  if (hasT6) {
    topT6 = Math.max(...strong.map((s) => s.t6));
    worstWeakT6 = Math.min(...weaks.map((w) => w.t6));
    t6Separates = (topT6 - worstWeakT6) >= 25;
    console.log(`Мастер-ловушка t6 (подгон/сокрытие) разделяет (сильнейший ${topT6}% vs наихудший слабый ${worstWeakT6}%, >=25pp):`,
      t6Separates ? "PASS" : `FAIL (разрыв ${topT6 - worstWeakT6}pp)`);
  }

  const topByAxis = {};
  const worstWeakByAxis = {};
  axes.forEach((k) => {
    topByAxis[k] = Math.max(...strong.map((s) => s.axes[k]));
    worstWeakByAxis[k] = Math.min(...weaks.map((w) => w.axes[k]));
  });
  const axisFails = axes.filter((k) => (topByAxis[k] - worstWeakByAxis[k]) < 15);
  const radarOk = axisFails.length === 0;
  console.log("Радар различает (все оси сильнейший−наихудший_слабый >=15pp):",
    radarOk ? "PASS" : `FAIL — оси <15pp: ${axisFails.join(", ")}`);
  axes.forEach((k) => {
    console.log(`   ${k.padEnd(13)} сильнейший ${(topByAxis[k] + "%").padEnd(5)} наихуд.слабый ${(worstWeakByAxis[k] + "%").padEnd(5)} разрыв ${topByAxis[k] - worstWeakByAxis[k]}pp`);
  });

  const strongLevelOk = strong.every((s) => LEVEL_RANK[s.level] >= LEVEL_RANK["middle"]);
  console.log("Сильные берут >= Средний уровень:",
    strongLevelOk ? "PASS" : "FAIL — " + strong.map((s) => `${s.label}=${s.level}`).join(", "));

  const gate = noInversion && t3Separates && t6Separates && radarOk;
  console.log("\n=== ВЕРДИКТ ГЕЙТА ПОЛЯ ===");
  console.log("Различает на реальном поле:", gate ? "PASS" : "FAIL");
  console.log("(strongLevelOk справочно:", strongLevelOk ? "да" : "нет", ")");

  fs.writeFileSync(path.join(HERE, "tables-field-report.json"), JSON.stringify({
    phase: "C — field gate",
    block: "tables",
    generatedAt: new Date().toISOString(),
    gate: gate ? "PASS" : "FAIL",
    checks: {
      noInversion, inversions,
      t3Separates, t3TopStrong: topT3, t3WorstWeak: worstWeakT3,
      t6Separates, t6TopStrong: topT6, t6WorstWeak: worstWeakT6,
      radarOk, axisFails,
      perAxisGap: axes.map((k) => ({ axis: k, topStrong: topByAxis[k], worstWeak: worstWeakByAxis[k], gapPP: topByAxis[k] - worstWeakByAxis[k] })),
      strongLevelOk
    },
    leaderboard: board.map((s) => ({
      agent: s.label, model: s.model, isWeak: s.isWeak,
      overall: s.overall, level: s.level, levelLabel: s.levelLabel,
      axes: s.axes, t3: s.t3, t6: s.t6, worstTask: s.worst,
      tasks: s.tasks
    }))
  }, null, 2));
  console.log("\n→ tables-field-report.json записан.");
  return gate;
}

const cmd = process.argv[2] || "score";
if (cmd === "run") cmdRun();
else cmdScore();
