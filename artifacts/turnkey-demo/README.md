# AgentStack Benchmark — Turnkey Demo

Просматриваемый «вау»-деливерабл. Два доказательства одним взглядом:
**(1) бенчмарк РАЗДЕЛЯЕТ слабых и сильных агентов на разнообразном поле**,
**(2) value-layer превращает голый скор в управленческий отчёт.**

Все цифры — из РЕАЛЬНЫХ прогонов (подписка, loopback, ANTHROPIC_* срезаны,
LLM-judge включён), без фабрикации. Пак — `richer_v1` (22 задачи, 9 осей).

---

## 1. Разделяющий лидерборд — `separating-leaderboard.md`

Поле из 4 РЕАЛЬНЫХ агентов на одном паке `richer_v1` с `--judge`:

| # | Агент | Overall | Пройдено |
|---|-------|--------:|---------:|
| 1 | Claude Code (Haiku 4.5) — real | **86.83** | 22/23 |
| 2 | Claude Code (Sonnet 4.6) — real | **86.45** | 22/23 |
| 3 | Claude Code (Opus 4.8) — real | **83.15** | 21/23 |
| 4 | Claude Code (Haiku 4.5) — **handicapped weak** (≤5 слов, без рассуждений) | **75.47** | 18/23 |

**Что это доказывает.** Три компетентных тира Claude кластеризуются в узкой
полосе 83–87 (находка P6: на сильном поле дискриминация мала). Как только в поле
добавлен **намеренно слабый, но РЕАЛЬНЫЙ** агент — та же модель Haiku, реальная
инференция, но с гандикап-промптом «отвечай ≤5 слов, без рассуждений» — он
проваливается заметно НИЖЕ: **75.47 против 83–87**, разрыв ~7.7 балла, и
18/23 пройдено против 21–22/23. Слабость честно «течёт» по осям компетентности:
quality 80.7 (vs 87–93), reliability 78.3 (vs 91–96), safety 67.5 (vs 75–82),
toolUse 81.1 (vs 90–94).

Вывод: бенчмарк **различает weak→strong на разнообразном поле**. Разделение даёт
не «больше задач», а разнообразие самого поля участников.

> Замечание о честности: ось `speed` плоская/шумная у всех тиров — её определяет
> латентность подписки, а не способность модели. Сигнал разделения живёт в осях
> компетентности (quality/reliability/safety/toolUse/depth), и он чёткий.

## 2. Полный value-layer отчёт по одному агенту — `sample-value-layer-opus.md`

Один агент (Opus 4.8), голый report.json → читаемый отчёт:

- **Role-fit ×5** — один и тот же прогон спроецирован на 5 ролей
  (executive / researcher / technical / sales / operationsAssistant) со своими
  весами осей: видно, что для «operations» агент сильнее (88.6), для
  «researcher» слабее (79.9) — без пересчёта самих осей.
- **Radar по 9 осям** — costEfficiency/memorySkills/autonomy = 100, но
  speed 50.5 и depth 51.2 проседают.
- **Инсайты** — детерминированные: силён в autonomy, проседает в speed,
  неровный прогон (2 провала).
- **Красные риски** — проваленные задачи + обнаруженный `[REDACTED]`-сигнал
  (агент вывел секрето-подобную строку — поймано санитайзером).
- **Baseline-сравнение** — дельта к слабому агенту: **overall +7.68**.

Это и есть «продукт»: не цифра 83.15, а карта пригодности по ролям + где именно
тонко + что чинить в первую очередь.

---

## Как воспроизвести

```bash
# 1. Разделяющее поле (4 реальных тира, judge, подписка, loopback)
bash scripts/run_turnkey_field.sh           # -> artifacts/turnkey-real-v1/ + leaderboard-turnkey-v1.{json,md}

# 2. Value-layer по одному агенту (read-only обогащение report.json)
python3 -m agentstack_benchmark.cli value-layer \
  --report artifacts/turnkey-real-v1/real-opus/report.json \
  --baseline-report artifacts/turnkey-real-v1/weak-haiku/report.json \
  --out artifacts/turnkey-demo/sample-value-layer-opus.json
```

## Файлы

- `separating-leaderboard.md` / `.json` — разделяющий лидерборд (4 реальных агента).
- `sample-value-layer-opus.md` / `.json` — полный value-layer по одному агенту.
- `README.md` — этот файл.

Границы: всё repo-local; без push/public/deploy/billing; модели только по подписке.
