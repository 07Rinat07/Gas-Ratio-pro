# Доверие и проверка операторских калибровочных пакетов

Revision 1 · Gas Ratio Pro v225.12

## Назначение

Stage 5.3 добавляет управляемый trust workflow для операторских калибровочных пакетов. Исходный ZIP из Stage 5.2 остаётся неизменяемым. Подписи, решения проверяющих, отзывы, сроки действия, lineage и продвижение между средами хранятся отдельно.

## Требования перед активацией

Пакет можно сделать активным для финального отчёта только после выполнения всех условий:

1. ZIP импортирован и прошёл Stage 5.2 data-rights/calibration gate.
2. Для `package_fingerprint` импортирована detached Ed25519-подпись.
3. Публичный ключ присутствует в утверждённом trust registry, активен, разрешён для проекта и среды.
4. Технический проверяющий одобрил пакет.
5. Проверяющий прав и управления данными одобрил пакет.
6. Пакет последовательно продвинут `development → validation → production`.
7. Пакет, подпись и ключ не отозваны.
8. Права на данные, подпись и ключ не просрочены.

## Работа в Professional Print Center

В разделе операторской калибровки доступны:

- импорт операторского ZIP;
- импорт detached signature JSON;
- ввод ID, имени, роли и решения проверяющего;
- сохранение обоснования решения;
- продвижение в следующую среду;
- отзыв пакета с обязательным обоснованием;
- таблица текущей среды, подписи, review status и trust status;
- предупреждение об истекающих ключах, подписях и правах.

Активация пакета блокируется, пока production trust decision не пройдёт.

## Detached signature

Подпись создаётся вне приложения закрытым Ed25519-ключом:

```powershell
python scripts/sign_operator_calibration_package.py `
  --package operator-calibration.zip `
  --private-key D:\secure\operator-signing-key.pem `
  --output operator-calibration.signature.json `
  --key-id operator-key-2026 `
  --project-id PROJECT-001 `
  --signer-id signer-001 `
  --signer-name "Ответственный подписант" `
  --organization-id OPERATOR-ORG
```

Закрытый ключ нельзя хранить в каталоге проекта, Git, документации или релизном архиве.

## Trust registry

Публичные ключи регистрируются в `config/calibration_trust_registry_v225_12.json`. Пустой реестр поставляется по умолчанию: пользователь должен добавить утверждённые публичные ключи через контролируемый административный процесс.

Для каждого ключа задаются:

- `key_id`;
- алгоритм Ed25519;
- владелец и организация;
- разрешённые проекты;
- разрешённые среды;
- период действия;
- статус `active`, `suspended` или `revoked`.

## Reviewer workflow

Роли:

- `technical_reviewer` — проверяет численные результаты, calibration evidence и lineage;
- `data_governance_reviewer` — проверяет права, классификацию, срок действия и разрешение на production use.

Новое решение того же проверяющего не удаляет старое. Оно создаёт новый immutable record со ссылкой на предыдущий fingerprint. Последнее решение может заменить предыдущее, но вся история сохраняется.

## Отзыв и истечение срока

Отзыв может относиться к:

- пакету;
- публичному ключу;
- detached signature.

Отзыв начинает действовать с `effective_at` и немедленно блокирует последующую активацию и финальный экспорт. Expiry monitor отдельно показывает истёкшие и приближающиеся сроки.

## Lineage

Detached signature содержит отдельный lineage record:

- `root` — исходная версия;
- `supersedes` — заменяет предыдущий пакет;
- `derived_from` — производная калибровка;
- `recalibrated_from` — повторная калибровка на основе родительского пакета.

Родитель должен быть импортирован в том же проекте. Самоссылки, циклы и конфликтующие родители запрещены.

## Финальный экспорт

Перед созданием `PresentationModel` приложение повторно выполняет production trust decision. В export artifact и history v6 сохраняются:

- trust decision ID;
- trust registry fingerprint;
- signature fingerprint;
- promotion ID;
- project authorization package ID;
- operator package fingerprint.

Foundation Dual Water остаётся `blocked_final_report`. Trust workflow не меняет production formulas и не может обойти numerical/calibration/report-policy gates.
