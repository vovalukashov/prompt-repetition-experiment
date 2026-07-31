# Runbook

Как воспроизвести прогон. Файлы исходного бандла не изменялись — их целостность
проверяется через `shasum -a 256 -c SHA256SUMS.txt`.

## Установка

```bash
python3.14 -m venv .venv
.venv/bin/pip install httpx pyyaml matplotlib numpy pytest
echo 'GOOGLE_GENERATIVE_AI_API_KEY=…' > .env && chmod 600 .env
```

`.env` в `.gitignore`. Ключ живёт только в переменной окружения и в заголовке
`x-goog-api-key`; в `config.yaml`, логи и `raw_runs.jsonl` он не попадает —
в сыром логе сохраняется payload с `"x-goog-api-key": "<redacted>"`.

## Проверки перед запуском

```bash
shasum -a 256 -c SHA256SUMS.txt
.venv/bin/python scripts/validate_tasks.py data/tasks.jsonl
.venv/bin/python -m pytest tests/ -q
```

Последняя команда прогоняет весь конвейер отчётов на синтетических данных,
поэтому ошибки форматирования всплывают до первого платного запроса.

## Прогон

```bash
.venv/bin/python runner.py --probe          # один запрос, показать сырой ответ
.venv/bin/python runner.py                  # warm-up + stability pilot + основной A/B
.venv/bin/python analyze.py out/<STAMP>     # метрики, графики, report.md, failures.md
.venv/bin/python make_post.py out/<STAMP>   # telegram_post_final.md
```

Абляции и вторая модель:

```bash
.venv/bin/python runner.py --conditions baseline,repeat_2,repeat_3,repeat_verbose \
  --skip-pilot --max-requests 1000 --tag ablations
.venv/bin/python analyze_ablation.py out/<STAMP>-ablations

.venv/bin/python runner.py --model gen3 --tag gen3 --max-requests 1500
.venv/bin/python analyze.py out/<STAMP>-gen3
```

`--max-requests` поднимает предохранитель от runaway-цикла. Он нужен, когда
stability pilot поднимает `repeats_per_condition` до 3: прогон вырастает
с 440 запросов до 1320, и дефолтный лимит 560 его обрывает.

Условия повторения (§14 спеки):

| условие | payload |
|---|---|
| `baseline` | `<QUERY>` |
| `repeat_2` | `<QUERY>\n\n<QUERY>` |
| `repeat_3` | `<QUERY>\n\n<QUERY>\n\n<QUERY>` |
| `repeat_verbose` | `<QUERY>\n\nПовторяю:\n<QUERY>` |

Маркер в `repeat_verbose` берётся по языку задания (`Повторяю:` для ru,
`Let me repeat that:` для en). Русский маркер на английском промпте подмешал бы
к сравнению ещё и переключение языка.

`runner.py` создаёт `out/<UTC_TIMESTAMP>/` и пишет туда `config_resolved.yaml`,
`dataset.sha256`, `raw_runs.jsonl` и `run_meta.json`. Всё остальное
пересчитывается из `raw_runs.jsonl` — прогон и анализ независимы.

## Что зафиксировано в протоколе

- каждый запрос — независимый single-turn без истории, system prompt и tools;
- `temperature = 0`, `maxOutputTokens = 64`, `candidateCount = 1`;
- reasoning выключен через `generationConfig.thinkingConfig.thinkingBudget = 0`,
  факт проверяется по `usageMetadata.thoughtsTokenCount` в каждом ответе;
- `repeat_2` — ровно две копии промпта через один пустой перевод строки,
  без «повторяю» и прочих добавок;
- порядок задач перемешан фиксированным seed, для каждой задачи отдельно
  разыгран порядок `AB` / `BA`, запросы идут round-robin при `concurrency = 1`;
- retry только на технических ошибках (408/409/429/5xx, сетевые, битый JSON),
  exponential backoff с jitter, максимум 5 попыток; неверный ответ модели
  никогда не переспрашивается;
- оценка ответов — только кодом по `expected`, без LLM-as-a-judge.

## Режимы reasoning по моделям

Проверено запросами к API 2026-07-31:

| модель | как выключается | что вернул API |
|---|---|---|
| `gemini-2.5-flash-lite` | `thinkingConfig.thinkingBudget = 0` | принято, `thoughtsTokenCount = 0` во всех ответах |
| `gemini-3.5-flash-lite` | **никак** | `thinkingBudget` → 400 `INVALID_ARGUMENT`; `thinkingLevel: "off"` → 400 (нет такого значения enum); пол — `minimal` |

Поэтому прогон на 3.5 помечен как `minimal_not_disableable` и не выдаётся за
строгую репликацию non-reasoning-условия из статьи.

## Ограничения

- Выводы относятся только к указанному model ID, режиму и дате прогона.
- `gemini-2.0-flash-lite`, на котором получен вирусный результат из статьи,
  отключён Google 1 июня 2026 — точная репликация недоступна.
- Google не документирует sampling seed для `generateContent`, поэтому полная
  побитовая воспроизводимость не гарантируется даже при `temperature = 0`.
  На `gemini-2.5-flash-lite` это не проявилось (0 расхождений из 20 в пилоте),
  на `gemini-3.5-flash-lite` проявилось сильно — см. отчёт прогона.
- Возможные скрытые системные инструкции, роутинг, квантизация и тихие
  обновления модели на стороне провайдера не наблюдаемы из клиента.
