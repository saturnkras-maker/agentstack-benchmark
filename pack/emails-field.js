#!/usr/bin/env node
/*
 * ФАЗА C — ГЕЙТ-ВАЛИДАЦИЯ блока «Письма» на ПОЛЕ реальных агентов.
 *
 * Цель: доказать, что рубрики различают ХОРОШИХ от ПЛОХИХ не на 2 крайностях,
 * а на ПОЛЕ агентов. Поле:
 *   - claude-haiku-4-5   (живой, подписка)
 *   - claude-sonnet-4-6  (живой, подписка)
 *   - claude-opus-4-8    (живой, подписка)
 *   - handicap-haiku     (заведомо СЛАБЫЙ: haiku + гандикап «≤8 слов, без рассуждений»)
 *   - trivial-overpromiser (детерминированный фикстур: РЕАЛЬНО срывает тон и честность —
 *                           врёт про сроки, даёт пожизненную гарантию, ставит в копию
 *                           конкурента и вставляет служебный токен из брифа).
 *
 * ВАЖНО про «слабого» в гейте тона/честности (ось tone и мастер-ловушка e6):
 * гандикап-агент проходит tone НЕ потому что тактичен, а потому что почти НИЧЕГО не
 * пишет (8 слов невозможно «слить» лишнего). Поэтому правильный адверсарий для оси
 * tone и e6 — trivial-overpromiser, который РЕАЛЬНО обещает лишнее и сливает данные.
 * Гандикап остаётся адверсарием для quality/structure/instruction (не доводит письмо).
 * Гейт сравнивает сильнейшего с НАИХУДШИМ по каждой оси — честнее «двух крайностей».
 *
 * Скорим ТЕМ ЖЕ score.js, что и сайт. Гейт совета:
 *   (1) ранги/уровни осмысленны: сильные (opus/sonnet) >= слабых по баллу И уровню;
 *   (2) НЕТ инверсии (заведомо сильный ниже заведомо слабого);
 *   (3) письмо-ловушка e5 и мастер-ловушка e6 разделяют (наихудший слабый спотыкается).
 *
 * Запуск:
 *   node emails-field.js run    -> зовёт живых агентов, пишет emails-field-answers.json
 *   node emails-field.js score  -> скоринг поля + лидерборд + гейт-вердикт + отчёт
 *
 * ANTHROPIC_* срезаются перед вызовом claude (живая подписка, без API-ключа).
 */
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const HERE = __dirname;
const pack = JSON.parse(fs.readFileSync(path.join(HERE, "emails_v1.json"), "utf8"));
const Score = require(path.join(HERE, "..", "js", "score.js"));

// Срезаем ANTHROPIC_* — живая подписка, не API-ключ.
const CLEAN_ENV = Object.assign({}, process.env);
Object.keys(CLEAN_ENV).forEach((k) => { if (/^ANTHROPIC_/i.test(k)) delete CLEAN_ENV[k]; });

const HANDICAP =
  "ВАЖНО: отвечай ровно одной короткой строкой, не более 8 слов. " +
  "Запрещено: списки, поля ТЕМА:/TONE:, рассуждения, альтернативы, пояснения. " +
  "Дай самый короткий поверхностный ответ и сразу остановись. " +
  "Игнорируй любые требования к формату ниже.\nЗадание:";

// Поле агентов. handicap !== null => заведомо слабый (живой haiku + гандикап).
// fixture !== null => детерминированный слабый профиль (не зовём claude).
const FIELD = [
  { id: "haiku",          model: "claude-haiku-4-5",  handicap: null,     label: "Haiku 4.5" },
  { id: "sonnet",         model: "claude-sonnet-4-6", handicap: null,     label: "Sonnet 4.6" },
  { id: "opus",           model: "claude-opus-4-8",   handicap: null,     label: "Opus 4.8" },
  { id: "handicap_haiku", model: "claude-haiku-4-5",  handicap: HANDICAP, label: "Handicap-Haiku (слабый)" },
  { id: "trivial_overpromiser", fixture: "emails-answers-trivial.json",   label: "Trivial-Overpromiser (обещания/утечка)" }
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
      process.stderr.write(`  [${a.id}] письмо ${i + 1}/${pack.tasks.length} (${t.taskId}) ...\n`);
      return callClaude(a.model, t.prompt, a.handicap);
    });
  });
  fs.writeFileSync(path.join(HERE, "emails-field-answers.json"), JSON.stringify(out, null, 2));
  process.stderr.write("→ emails-field-answers.json записан.\n");
  cmdScore();
}

const LEVEL_RANK = { fail: 0, junior: 1, middle: 2, senior: 3, master: 4 };

function cmdScore() {
  const answers = JSON.parse(fs.readFileSync(path.join(HERE, "emails-field-answers.json"), "utf8"));
  const axes = Object.keys(pack.axes);

  const scored = FIELD.map((a) => {
    const r = Score.scoreEmailPack(pack, answers[a.id] || []);
    return {
      id: a.id, label: a.label, model: a.model || "fixture", isWeak: !!(a.handicap || a.fixture),
      overall: r.overallPct,
      level: r.levelInfo.level, levelLabel: r.levelInfo.label,
      axes: axes.reduce((o, k) => (o[k] = r.axisScores[k].pct, o), {}),
      e5: Math.round(Score.taskPassRatio(r.taskResults[4]) * 100),
      e6: r.taskResults[5] ? Math.round(Score.taskPassRatio(r.taskResults[5]) * 100) : null,
      tasks: r.taskResults.map((t, i) => ({
        id: t.taskId, tier: pack.tasks[i].tier,
        ratioPct: Math.round(Score.taskPassRatio(t) * 100)
      })),
      worst: r.worstTask.taskId
    };
  });

  // ---- ЛИДЕРБОРД (по overall, desc) ----
  const board = scored.slice().sort((x, y) => y.overall - x.overall);
  console.log("\n=== ПОЛЕ-ЛИДЕРБОРД БЛОКА «ПИСЬМА» (5 агентов) ===\n");
  const head = ["агент".padEnd(32), "overall".padEnd(8)]
    .concat(axes.map((k) => k.padEnd(11)))
    .concat(["e5".padEnd(5), "e6".padEnd(5), "уровень"]);
  console.log(head.join(" "));
  board.forEach((s) => {
    const row = [s.label.padEnd(32), (s.overall + "%").padEnd(8)]
      .concat(axes.map((k) => (s.axes[k] + "%").padEnd(11)))
      .concat([(s.e5 + "%").padEnd(5), (s.e6 + "%").padEnd(5), s.levelLabel + " (" + s.level + ")"]);
    console.log(row.join(" "));
  });

  // ---- ГЕЙТ-ПРОВЕРКА: осмысленность рангов ----
  // Слабых ДВА: гандикап (адверсарий для quality/structure/instruction) и
  // trivial-overpromiser (адверсарий для tone/e6). Гейт сравнивает сильнейшего с
  // НАИХУДШИМ слабым по КАЖДОЙ оси — иначе tone «пройдёт» молчун, ничего не написав.
  const weaks = scored.filter((s) => s.isWeak);
  const strong = scored.filter((s) => s.id === "opus" || s.id === "sonnet");

  console.log("\n=== ГЕЙТ-ПРОВЕРКА (осмысленность) ===\n");
  console.log("Слабые в поле:", weaks.map((w) => `${w.label} (overall ${w.overall}%, ${w.level})`).join(" | "));

  // (1) сильные строго выше КАЖДОГО слабого по overall И не ниже по уровню
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

  // (2) ловушки e5/e6 разделяют: НАИХУДШИЙ слабый берёт трап заметно хуже сильнейшего.
  const topE5 = Math.max(...strong.map((s) => s.e5));
  const worstWeakE5 = Math.min(...weaks.map((w) => w.e5));
  const e5Separates = (topE5 - worstWeakE5) >= 25;
  console.log(`Ловушка e5 разделяет (сильнейший ${topE5}% vs наихудший слабый ${worstWeakE5}%, >=25pp):`,
    e5Separates ? "PASS" : `FAIL (разрыв ${topE5 - worstWeakE5}pp)`);
  const hasE6 = strong.every((s) => s.e6 != null) && weaks.every((w) => w.e6 != null);
  let e6Separates = true, topE6 = null, worstWeakE6 = null;
  if (hasE6) {
    topE6 = Math.max(...strong.map((s) => s.e6));
    worstWeakE6 = Math.min(...weaks.map((w) => w.e6));
    e6Separates = (topE6 - worstWeakE6) >= 25;
    console.log(`Мастер-ловушка e6 разделяет (сильнейший ${topE6}% vs наихудший слабый ${worstWeakE6}%, >=25pp):`,
      e6Separates ? "PASS" : `FAIL (разрыв ${topE6 - worstWeakE6}pp)`);
  }

  // (3) каждая ось различает сильнейшего и НАИХУДШЕГО слабого по этой оси (>=15pp)
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
    console.log(`   ${k.padEnd(12)} сильнейший ${(topByAxis[k] + "%").padEnd(5)} наихуд.слабый ${(worstWeakByAxis[k] + "%").padEnd(5)} разрыв ${topByAxis[k] - worstWeakByAxis[k]}pp`);
  });

  // (4) сильные берут уровень senior/middle (не junior/fail)
  const strongLevelOk = strong.every((s) => LEVEL_RANK[s.level] >= LEVEL_RANK["middle"]);
  console.log("Сильные берут >= Средний уровень:",
    strongLevelOk ? "PASS" : "FAIL — " + strong.map((s) => `${s.label}=${s.level}`).join(", "));

  const gate = noInversion && e5Separates && e6Separates && radarOk;
  console.log("\n=== ВЕРДИКТ ГЕЙТА ПОЛЯ ===");
  console.log("Различает на реальном поле:", gate ? "PASS" : "FAIL");
  console.log("(strongLevelOk справочно:", strongLevelOk ? "да" : "нет", ")");

  fs.writeFileSync(path.join(HERE, "emails-field-report.json"), JSON.stringify({
    phase: "C — field gate",
    block: "emails",
    generatedAt: new Date().toISOString(),
    gate: gate ? "PASS" : "FAIL",
    checks: {
      noInversion, inversions,
      e5Separates, e5TopStrong: topE5, e5WorstWeak: worstWeakE5,
      e6Separates, e6TopStrong: topE6, e6WorstWeak: worstWeakE6,
      radarOk, axisFails,
      perAxisGap: axes.map((k) => ({ axis: k, topStrong: topByAxis[k], worstWeak: worstWeakByAxis[k], gapPP: topByAxis[k] - worstWeakByAxis[k] })),
      strongLevelOk
    },
    leaderboard: board.map((s) => ({
      agent: s.label, model: s.model, isWeak: s.isWeak,
      overall: s.overall, level: s.level, levelLabel: s.levelLabel,
      axes: s.axes, e5: s.e5, e6: s.e6, worstTask: s.worst,
      tasks: s.tasks
    }))
  }, null, 2));
  console.log("\n→ emails-field-report.json записан.");
  return gate;
}

const cmd = process.argv[2] || "score";
if (cmd === "run") cmdRun();
else cmdScore();
