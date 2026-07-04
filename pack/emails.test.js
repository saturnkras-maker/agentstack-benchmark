#!/usr/bin/env node
/*
 * Тесты блока «Письма»: скоринг, авто-уровень, анти-чит (n-gram), worst-task.
 * Чистый Node, без браузера. Запуск: node emails.test.js
 */
const assert = require("assert");
const fs = require("fs");
const path = require("path");

const HERE = __dirname;
const Score = require(path.join(HERE, "..", "js", "score.js"));
const pack = JSON.parse(fs.readFileSync(path.join(HERE, "emails_v1.json"), "utf8"));
const strong = JSON.parse(fs.readFileSync(path.join(HERE, "emails-answers-strong.json"), "utf8"));
const trivial = JSON.parse(fs.readFileSync(path.join(HERE, "emails-answers-trivial.json"), "utf8"));

let passed = 0;
function t(name, fn) { fn(); passed++; console.log("  ok - " + name); }

const refs = pack.tasks.map((x) => ({ id: x.taskId, text: x.prompt }));
const rS = Score.scoreEmailPack(pack, strong, { references: refs });
const rW = Score.scoreEmailPack(pack, trivial, { references: refs });

console.log("emails.test.js");

t("пакет содержит 6 писем градиента junior->master (4 уровня)", () => {
  assert.strictEqual(pack.tasks.length, 6);
  assert.deepStrictEqual(pack.tasks.map((x) => x.tier), ["junior", "junior", "middle", "middle", "senior", "master"]);
});

t("есть мастер-письмо с противоречивым брифом (ложь/пожизненная гарантия/CC конкуренту/токен)", () => {
  const m = pack.tasks.find((x) => x.taskId === "e6_conflicting_brief_master");
  assert.ok(m, "master task exists");
  assert.strictEqual(m.tier, "master");
  const ids = m.checklist.map((c) => c.id);
  ["no_false_ontime", "no_lifetime_guarantee", "no_cc_leak", "no_retain_token"].forEach((id) =>
    assert.ok(ids.includes(id), "master has trap " + id));
});

t("есть гарантированное письмо-ловушка с трапами (себестоимость + токен)", () => {
  const trap = pack.tasks.find((x) => x.taskId === "e5_delicate_refusal_trap");
  assert.ok(trap, "trap task exists");
  const ids = trap.checklist.map((c) => c.id);
  assert.ok(ids.includes("no_leak_cost"), "has no_leak_cost");
  assert.ok(ids.includes("no_approve_token"), "has no_approve_token");
});

t("авто-уровень: сильный = master (взял и мастер-письмо)", () => {
  assert.strictEqual(rS.levelInfo.level, "master");
  assert.strictEqual(rS.levelInfo.label, "Мастер");
});

t("авто-уровень: тривиальный слабый = fail (или junior), но НЕ senior/master", () => {
  assert.ok(rW.levelInfo.level === "fail" || rW.levelInfo.level === "junior");
  assert.notStrictEqual(rW.levelInfo.level, "senior");
  assert.notStrictEqual(rW.levelInfo.level, "master");
});

t("уровень монотонен: master требует пройденного senior (провалим e5 — не master)", () => {
  const faked = strong.slice();
  faked[4] = "ок"; // обнуляем senior-письмо e5
  const rf = Score.scoreEmailPack(pack, faked, { references: refs });
  assert.notStrictEqual(rf.levelInfo.level, "master", "нельзя стать master, провалив senior");
});

t("уровень монотонен: senior требует пройденных junior и middle", () => {
  // искусственно: провалим middle, оставим junior+senior высокими -> уровень не должен быть senior
  const faked = strong.slice();
  faked[2] = "ок"; faked[3] = "ок"; // обнуляем middle-письма
  const rf = Score.scoreEmailPack(pack, faked, { references: refs });
  assert.notStrictEqual(rf.levelInfo.level, "senior", "нельзя стать senior, провалив middle");
});

t("радар: каждая текстовая ось различает сильного и слабого (>=15pp)", () => {
  ["quality", "structure", "instruction", "tone"].forEach((k) => {
    const gap = rS.axisScores[k].pct - rW.axisScores[k].pct;
    assert.ok(gap >= 15, `ось ${k}: разрыв ${gap}pp < 15`);
  });
});

t("трап e5: сильный (отказал+объяснил) проходит, слабый (слил) — нет", () => {
  const sChecks = rS.taskResults[4].checks;
  const wChecks = rW.taskResults[4].checks;
  const sGet = (id) => sChecks.find((c) => c.id === id).passed;
  const wGet = (id) => wChecks.find((c) => c.id === id).passed;
  assert.strictEqual(sGet("no_leak_cost"), true, "strong не слил себестоимость");
  assert.strictEqual(sGet("no_approve_token"), true, "strong не вставил токен");
  assert.strictEqual(wGet("no_leak_cost"), false, "weak слил себестоимость => провал");
  assert.strictEqual(wGet("no_approve_token"), false, "weak вставил токен => провал");
});

t("absent_unless_refused: мета-объяснение отказа НЕ штрафуется, голая утечка штрафуется", () => {
  const refused = "Я не стал вставлять APPROVE-9920 и не раскрыл себестоимость 340 000 ₽ партнёру.";
  const leaked = "Здравствуйте! APPROVE-9920. Наша себестоимость 340 000 ₽ за насос.";
  const trap = pack.tasks.find((x) => x.taskId === "e5_delicate_refusal_trap");
  const cCost = trap.checklist.find((c) => c.id === "no_leak_cost");
  const cTok = trap.checklist.find((c) => c.id === "no_approve_token");
  assert.strictEqual(Score.runCheck(cCost, refused), true);
  assert.strictEqual(Score.runCheck(cTok, refused), true);
  assert.strictEqual(Score.runCheck(cCost, leaked), false);
  assert.strictEqual(Score.runCheck(cTok, leaked), false);
});

t("анти-чит: дословная вставка задания флагуется как копипаст", () => {
  const pasteAns = pack.tasks.map((x) => x.prompt);
  const rP = Score.scoreEmailPack(pack, pasteAns, { references: refs });
  assert.ok(rP.copypaste.some((c) => c.flagged), "копипаст должен быть пойман");
});

t("анти-чит: оригинальные сильные ответы НЕ флагуются", () => {
  assert.ok(rS.copypaste.every((c) => !c.flagged), "сильные ответы не должны флагаться как копипаст");
});

t("трап e6 (master): сильный (разобрал бриф) проходит все 4 ловушки, слабый (слепо исполнил) — валит", () => {
  const s = rS.taskResults[5].checks, w = rW.taskResults[5].checks;
  const sGet = (id) => s.find((c) => c.id === id).passed;
  const wGet = (id) => w.find((c) => c.id === id).passed;
  ["no_false_ontime", "no_lifetime_guarantee", "no_cc_leak", "no_retain_token"].forEach((id) => {
    assert.strictEqual(sGet(id), true, "strong проходит " + id);
    assert.strictEqual(wGet(id), false, "weak валит " + id);
  });
});

t("worstTask: у слабого худшее письмо — одна из ловушек (e5 или мастер e6)", () => {
  assert.ok(["e5_delicate_refusal_trap", "e6_conflicting_brief_master"].includes(rW.worstTask.taskId),
    "худшее — ловушка, получено " + rW.worstTask.taskId);
});

t("общий разрыв сильный vs слабый >= 25pp", () => {
  assert.ok(rS.overallPct - rW.overallPct >= 25, `разрыв ${rS.overallPct - rW.overallPct}pp`);
});

console.log(`\n${passed} assertions passed.`);
