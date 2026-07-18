# Операторские калибровочные пакеты — revision 1

Stage 5.2 позволяет подключать к проекту собственные калибровочные данные оператора без изменения production-формул Gas Ratio Pro.

## Что импортируется

Поддерживается ZIP-пакет, содержащий ровно три файла в корне:

- `manifest.json` — область проекта, владелец, правовое основание, разрешения и SHA-256;
- `calibration_registry.json` — acceptance thresholds, sensitivity и uncertainty policy;
- `calibration_dataset.json` — калибровочные случаи, входы, параметры, наблюдаемые значения и единицы.

Каталоги, дополнительные файлы, абсолютные пути и `..` внутри ZIP запрещены.

## Обязательные права на данные

Пакет принимается только когда:

- `legal_status` равен `operator_owned`, `licensed` или `public_domain`;
- указаны владелец и правовое основание;
- разрешены локальная обработка и производный анализ;
- текущий проект присутствует в `project_scope`;
- срок прав не истёк;
- отдельно указано, разрешено ли использование в финальном отчёте.

Разрешение на распространение не требуется для локального operator-owned пакета. Такой пакет остаётся внутри проекта и не включается в релизные архивы.

## Импорт в Professional Print Center

1. Откройте **Центр печати и экспорта**.
2. Разверните **Операторская калибровка проекта**.
3. Выберите ZIP и нажмите **Импортировать и проверить**.
4. Выберите импортированную версию и нажмите **Сделать активным**.
5. Выполните **Сравнить с базовой калибровкой**.

Интерфейс показывает оператора, версию, правовой статус, число методов, право финального отчёта, активность и сокращённый fingerprint.

## Неизменяемость и версии

`package_id + version` не может быть повторно использован с другим fingerprint. Исходный ZIP, registry, dataset, rights fingerprint и import evidence хранятся в проекте неизменяемо. Повреждение любого сохранённого файла блокирует сравнение и экспорт.

## Сравнение

Сравнение выполняется с project baseline или другой импортированной версией. Для каждого метода фиксируются:

- passed/failed;
- RMSE и его delta;
- максимальная абсолютная ошибка и delta;
- ширина uncertainty envelope и delta;
- статус `improved`, `degraded`, `equivalent`, `target_only` или `reference_only`.

Сравнение не меняет вычислительные формулы и не выбирает метод автоматически.

## Финальный экспорт

При наличии активного пакета export boundary повторно проверяет:

- numerical validation;
- operator calibration;
- report policy метода;
- актуальность data-rights;
- fingerprint активного пакета.

Результатом является versioned project authorization package. Его ID, gate IDs и fingerprint операторской калибровки записываются в артефакт и историю экспорта. Если пакет разрешён только для диагностики, финальный PDF/DOCX/HTML блокируется до запуска renderer.

## Создание пакета

```bash
python scripts/build_operator_calibration_package.py \
  --registry calibration_registry.json \
  --dataset calibration_dataset.json \
  --output operator_calibration.zip \
  --package-id operator-field-a \
  --version 1.0.0 \
  --project-id default \
  --operator-name "Example Operator" \
  --organization-id OP-001 \
  --owner "Example Operator" \
  --legal-status operator_owned \
  --legal-basis "Internal approval OP-001" \
  --final-report-use-allowed
```

Флаг `--redistribution-allowed` следует указывать только при наличии явного права на распространение данных.
