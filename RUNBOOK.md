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

## Ограничения

- Выводы относятся только к указанному model ID, режиму и дате прогона.
- `gemini-2.0-flash-lite`, на котором получен вирусный результат из статьи,
  отключён Google 1 июня 2026 — точная репликация недоступна.
- Google не документирует sampling seed для `generateContent`, поэтому полная
  побитовая воспроизводимость не гарантируется даже при `temperature = 0`.
- Возможные скрытые системные инструкции, роутинг, квантизация и тихие
  обновления модели на стороне провайдера не наблюдаемы из клиента.
