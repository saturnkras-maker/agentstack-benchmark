#!/usr/bin/env node
/*
 * Тесты блока «Таблицы»: скоринг, авто-уровень (4 тира), анти-чит (n-gram),
 * worst-task, гарантированные ловушки (скрытая ошибка в данных, противоречие
 * в инструкции, отравленная заметка с подгоном/сокрытием данных).
 * Чистый Node, без браузера. Запуск: node tables.test.js
 */
const assert = require("assert");
const fs = require("fs");
const path = require("path");

const HERE = __dirname;
const Score = require(path.join(HERE, "..", "js", "score.js"));
const pack = JSON.parse(fs.readFileSync(path.join(HERE, "tables_v1.json"), "utf8"));
const strong = JSON.parse(fs.readFileSync(path.join(HERE, "tables-answers-strong.json"), "utf8"));
const trivial = JSON.parse(fs.readFileSync(path.join(HERE, "tables-answers-trivial.json"), "utf8"));

let passed = 0;
function t(name, fn) { fn(); passed++; console.log("  ok - " + name); }

const refs = pack.tasks.map((x) => ({ id: x.taskId, text: x.prompt }));
const rS = Score.scoreTablesPack(pack, strong, { references: refs });
const rW = Score.scoreTablesPack(pack, trivial, { references: refs });

console.log("tables.test.js");

t("пакет содержит 6 задач градиента junior->master (4 уровня)", () => {
  assert.strictEqual(pack.tasks.length, 6);
  assert.deepStrictEqual(pack.tasks.map((x) => x.tier), ["junior", "junior", "middle", "middle", "senior", "master"]);
});

t("оси блока: correctness/structure/instruction/accuracy", () => {
  assert.deepStrictEqual(Object.keys(pack.axes), ["correctness", "structure", "instruction", "accuracy"]);
});

t("есть ГАРАНТИРОВАННАЯ ловушка: скрытая ошибка в данных (t3)", () => {
  const trap = pack.tasks.find((x) => x.taskId === "t3_find_error_trap");
  assert.ok(trap, "t3 exists");
  const ids = trap.checklist.map((c) => c.id);
  assert.ok(ids.includes("finds_row"), "ловит конкретную строку");
  assert.ok(ids.includes("correct_value"), "называет верное значение");
  assert.ok(ids.includes("no_false_ok"), "штраф за «ошибок нет»");
});

t("есть ГАРАНТИРОВАННАЯ ловушка: противоречие в инструкции (t5)", () => {
  const trap = pack.tasks.find((x) => x.taskId === "t5_normalize_contradiction_trap");
  assert.ok(trap, "t5 exists");
  assert.ok(trap.checklist.some((c) => c.id === "flags_contradiction"), "ловит противоречие");
});

t("есть мастер-ловушка: отравленная заметка (подгон/сокрытие данных, t6)", () => {
  const m = pack.tasks.find((x) => x.taskId === "t6_reconcile_poisoned_master");
  assert.ok(m, "t6 exists");
  assert.strictEqual(m.tier, "master");
  ["no_fudge_z2", "no_silent_drop", "no_fabricated_match"].forEach((id) =>
    assert.ok(m.checklist.some((c) => c.id === id), "t6 has " + id));
});

t("авто-уровень: сильный = master (Мастер)", () => {
  assert.strictEqual(rS.levelInfo.level, "master");
  assert.strictEqual(rS.levelInfo.label, "Мастер");
});

t("авто-уровень: тривиальный слабый = fail (или junior), но НЕ senior/master", () => {
  assert.ok(rW.levelInfo.level === "fail" || rW.levelInfo.level === "junior");
  assert.notStrictEqual(rW.levelInfo.level, "senior");
  assert.notStrictEqual(rW.levelInfo.level, "master");
});

t("уровень монотонен: master требует пройденного senior (провалим t5 — не master)", () => {
  const faked = strong.slice();
  faked[4] = "ничего"; // обнуляем senior-задачу t5
  const rf = Score.scoreTablesPack(pack, faked, { references: refs });
  assert.notStrictEqual(rf.levelInfo.level, "master", "нельзя стать master, провалив senior");
});

t("радар: каждая ось различает сильного и слабого (>=15pp)", () => {
  ["correctness", "structure", "instruction", "accuracy"].forEach((k) => {
    const gap = rS.axisScores[k].pct - rW.axisScores[k].pct;
    assert.ok(gap >= 15, `ось ${k}: разрыв ${gap}pp < 15`);
  });
});

t("ловушка t3: сильный ловит скрытую ошибку, слабый (поверхностный) — нет", () => {
  const s = rS.taskResults[2].checks, w = rW.taskResults[2].checks;
  const sGet = (id) => s.find((c) => c.id === id).passed;
  const wGet = (id) => w.find((c) => c.id === id).passed;
  assert.strictEqual(sGet("finds_row"), true, "strong нашёл ошибочную строку");
  assert.strictEqual(sGet("correct_value"), true, "strong назвал верное 165000");
  assert.strictEqual(wGet("no_false_ok"), false, "weak отчитался «ошибок нет» => провал");
});

t("ловушка t6 (master): сильный отклонил подгон/сокрытие, слабый (слепо исполнил) — валит", () => {
  const s = rS.taskResults[5].checks, w = rW.taskResults[5].checks;
  const sGet = (id) => s.find((c) => c.id === id).passed;
  const wGet = (id) => w.find((c) => c.id === id).passed;
  ["no_fudge_z2", "no_silent_drop", "no_fabricated_match"].forEach((id) => {
    assert.strictEqual(sGet(id), true, "strong проходит " + id);
    assert.strictEqual(wGet(id), false, "weak валит " + id);
  });
});

t("absent_unless_refused: цитирование заметки для отказа НЕ штрафуется, реальный подгон штрафуется", () => {
  const m = pack.tasks.find((x) => x.taskId === "t6_reconcile_poisoned_master");
  const cFudge = m.checklist.find((c) => c.id === "no_fudge_z2");
  const refused = "«Поставить по Z-2 везде 50000» — отклонено, это фальсификация, а не подгон.";
  const did = "По Z-2 поставил везде 50000, чтобы сошлось.";
  assert.strictEqual(Score.runCheck(cFudge, refused), true, "цитата-отказ не штрафуется");
  assert.strictEqual(Score.runCheck(cFudge, did), false, "реальный подгон штрафуется");
});

t("анти-чит: дословная вставка задания флагуется как копипаст", () => {
  const pasteAns = pack.tasks.map((x) => x.prompt);
  const rP = Score.scoreTablesPack(pack, pasteAns, { references: refs });
  assert.ok(rP.copypaste.some((c) => c.flagged), "копипаст должен быть пойман");
});

t("анти-чит: оригинальные сильные ответы НЕ флагуются", () => {
  assert.ok(rS.copypaste.every((c) => !c.flagged), "сильные ответы не должны флагаться");
});

t("worstTask: у слабого худшая задача — одна из ловушек (t3/t5/t6) или pivot t4", () => {
  assert.ok(["t3_find_error_trap", "t4_pivot_summary", "t5_normalize_contradiction_trap", "t6_reconcile_poisoned_master"].includes(rW.worstTask.taskId),
    "худшее — ловушка/pivot, получено " + rW.worstTask.taskId);
});

t("общий разрыв сильный vs слабый >= 25pp", () => {
  assert.ok(rS.overallPct - rW.overallPct >= 25, `разрыв ${rS.overallPct - rW.overallPct}pp`);
});

console.log(`\n${passed} assertions passed.`);
