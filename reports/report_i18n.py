from __future__ import annotations

from dataclasses import replace
from typing import Mapping

from core.internationalization.language_registry import normalize_language
from reports.export_html import HtmlReportTable

# Report-local catalogue. UI catalogues remain in resources/i18n; this module
# covers generated engineering prose/tables so exports never silently fall
# back to Russian when kk/en is selected.
_TEXT: dict[str, dict[str, str]] = {
    "ru": {
        "report.subtitle": "Инженерное заключение по вероятным УВ-интервалам",
        "report.source": "Источник данных",
        "report.project": "Проект",
        "report.analysis_interval": "Интервал анализа",
        "report.profile": "Профиль отчета",
        "report.profile.client": "Для заказчика",
        "report.profile.engineering": "Инженерный",
        "report.profile.expert": "Экспертный",
        "report.overview": "Обзорный планшет скважины",
        "report.overview.engineering": "Обзорный инженерный планшет",
        "report.interval": "Интервал {index}: {top}–{base} м · {fluids}",
        "report.detail": "Инженерный планшет · {top}–{base} м",
        "report.key_results": "Ключевые результаты",
        "report.engineering_appendix": "Инженерные результаты и расчетные приложения",
        "report.conclusion": "Заключение и ограничения",
        "report.scope.title": "Область применения",
        "report.scope.text": "Результаты предназначены для инженерной интерпретации и должны рассматриваться совместно с материалами ГИС, литологией, керном, испытаниями и данными разработки.",
        "report.limitations.title": "Ограничения интерпретации",
        "report.limitations.text": "Выводы отражают интерпретацию доступных данных газового каротажа. Окончательные решения принимаются после сопоставления с материалами ГИС, испытаниями и геологической моделью.",
        "report.hypothesis_note": "Каждая интерпретация является инженерной гипотезой и должна оцениваться совместно с ГИС, литологией, керном и испытаниями.",
        "fluid.gas": "Газ",
        "fluid.oil": "Нефть",
        "fluid.condensate": "Газоконденсат",
        "fluid.oil_gas": "Нефть–газ",
        "fluid.dry_gas": "Сухой газ",
        "fluid.transition": "Переходный",
        "fluid.unknown": "Неопределено",
    },
    "kk": {
        "report.subtitle": "Ықтимал көмірсутек аралықтары бойынша инженерлік қорытынды",
        "report.source": "Деректер көзі",
        "report.project": "Жоба",
        "report.analysis_interval": "Талдау аралығы",
        "report.profile": "Есеп профилі",
        "report.profile.client": "Тапсырыс берушіге арналған",
        "report.profile.engineering": "Инженерлік",
        "report.profile.expert": "Сараптамалық",
        "report.overview": "Ұңғыманың шолу планшеті",
        "report.overview.engineering": "Шолу инженерлік планшеті",
        "report.interval": "{index}-аралық: {top}–{base} м · {fluids}",
        "report.detail": "Инженерлік планшет · {top}–{base} м",
        "report.key_results": "Негізгі нәтижелер",
        "report.engineering_appendix": "Инженерлік нәтижелер және есептік қосымшалар",
        "report.conclusion": "Қорытынды және шектеулер",
        "report.scope.title": "Қолданылу саласы",
        "report.scope.text": "Нәтижелер инженерлік интерпретацияға арналған және ГИС материалдарымен, литологиямен, кернмен, сынақтармен және игеру деректерімен бірге қарастырылуы тиіс.",
        "report.limitations.title": "Интерпретация шектеулері",
        "report.limitations.text": "Қорытындылар қолжетімді газ каротажы деректерінің интерпретациясын көрсетеді. Соңғы шешімдер ГИС материалдарымен, сынақтармен және геологиялық модельмен салыстырғаннан кейін қабылданады.",
        "report.hypothesis_note": "Әрбір интерпретация инженерлік гипотеза болып табылады және ГИС, литология, керн және сынақтармен бірге бағалануы тиіс.",
        "fluid.gas": "Газ",
        "fluid.oil": "Мұнай",
        "fluid.condensate": "Газконденсат",
        "fluid.oil_gas": "Мұнай–газ",
        "fluid.dry_gas": "Құрғақ газ",
        "fluid.transition": "Өтпелі",
        "fluid.unknown": "Анықталмаған",
    },
    "en": {
        "report.subtitle": "Engineering assessment of probable hydrocarbon intervals",
        "report.source": "Data source",
        "report.project": "Project",
        "report.analysis_interval": "Analysis interval",
        "report.profile": "Report profile",
        "report.profile.client": "Client",
        "report.profile.engineering": "Engineering",
        "report.profile.expert": "Expert",
        "report.overview": "Well overview log",
        "report.overview.engineering": "Engineering overview log",
        "report.interval": "Interval {index}: {top}–{base} m · {fluids}",
        "report.detail": "Engineering log · {top}–{base} m",
        "report.key_results": "Key results",
        "report.engineering_appendix": "Engineering results and calculation appendices",
        "report.conclusion": "Conclusions and limitations",
        "report.scope.title": "Scope of use",
        "report.scope.text": "The results are intended for engineering interpretation and must be reviewed together with well logs, lithology, core, tests, and development data.",
        "report.limitations.title": "Interpretation limitations",
        "report.limitations.text": "The conclusions reflect interpretation of the available mud-gas logging data. Final decisions require correlation with well logs, tests, and the geological model.",
        "report.hypothesis_note": "Each interpretation is an engineering hypothesis and must be evaluated together with well logs, lithology, core, and tests.",
        "fluid.gas": "Gas",
        "fluid.oil": "Oil",
        "fluid.condensate": "Gas condensate",
        "fluid.oil_gas": "Oil–gas",
        "fluid.dry_gas": "Dry gas",
        "fluid.transition": "Transition",
        "fluid.unknown": "Undetermined",
    },
}

_EXACT: dict[str, dict[str, str]] = {
    "kk": {
        "Инженерная сводка перспективных интервалов": "Перспективалы аралықтардың инженерлік жиынтығы",
        "Приоритетные интервалы нефти, газа и конденсата": "Мұнай, газ және конденсаттың басым аралықтары",
        "Рекомендации и ограничения интерпретации": "Интерпретация бойынша ұсынымдар мен шектеулер",
        "Реестр интерпретированных УВ-интервалов": "Интерпретацияланған көмірсутек аралықтарының тізілімі",
        "Сводка выявленных УВ-интервалов": "Анықталған көмірсутек аралықтарының жиынтығы",
        "Инженерная интерпретация УВ-интервалов": "Көмірсутек аралықтарының инженерлік интерпретациясы",
        "Диагностика движка УВ-интервалов": "Көмірсутек аралықтары қозғалтқышының диагностикасы",
        "Кровля, м": "Төбесі, м", "Подошва, м": "Табаны, м", "Мощность, м": "Қалыңдығы, м",
        "Флюид": "Флюид", "Достоверность": "Сенімділік", "Решение": "Шешім",
        "Инженерный вывод": "Инженерлік қорытынды", "Рекомендация": "Ұсыным",
        "Ограничение": "Шектеу", "Комментарий": "Түсіндірме", "Глубина": "Тереңдік",
        "Тип": "Түрі", "Уверенность": "Сенімділік", "Интерпретация": "Интерпретация",
    },
    "en": {
        "Инженерная сводка перспективных интервалов": "Engineering summary of prospective intervals",
        "Приоритетные интервалы нефти, газа и конденсата": "Priority oil, gas, and condensate intervals",
        "Рекомендации и ограничения интерпретации": "Interpretation recommendations and limitations",
        "Реестр интерпретированных УВ-интервалов": "Interpreted hydrocarbon interval register",
        "Сводка выявленных УВ-интервалов": "Detected hydrocarbon interval summary",
        "Инженерная интерпретация УВ-интервалов": "Engineering interpretation of hydrocarbon intervals",
        "Диагностика движка УВ-интервалов": "Hydrocarbon interval engine diagnostics",
        "Кровля, м": "Top, m", "Подошва, м": "Base, m", "Мощность, м": "Thickness, m",
        "Флюид": "Fluid", "Достоверность": "Confidence", "Решение": "Decision",
        "Инженерный вывод": "Engineering conclusion", "Рекомендация": "Recommendation",
        "Ограничение": "Limitation", "Комментарий": "Comment", "Глубина": "Depth",
        "Тип": "Type", "Уверенность": "Confidence", "Интерпретация": "Interpretation",
    },
}

_PHRASES: dict[str, tuple[tuple[str, str], ...]] = {
    "kk": (
        ("Газовый интервал", "Газ аралығы"), ("Нефтяной интервал", "Мұнай аралығы"),
        ("Газоконденсатный интервал", "Газконденсат аралығы"), ("Переходный интервал", "Өтпелі аралық"),
        ("Требуется инженерная проверка", "Инженерлік тексеру қажет"),
        ("средняя", "орташа"), ("высокая", "жоғары"), ("низкая", "төмен"),
    ),
    "en": (
        ("Газовый интервал", "Gas interval"), ("Нефтяной интервал", "Oil interval"),
        ("Газоконденсатный интервал", "Gas-condensate interval"), ("Переходный интервал", "Transition interval"),
        ("Требуется инженерная проверка", "Engineering review required"),
        ("средняя", "medium"), ("высокая", "high"), ("низкая", "low"),
    ),
}


def tr(locale: str, key: str, **values: object) -> str:
    code = normalize_language(locale)
    template = _TEXT.get(code, _TEXT["ru"]).get(key, _TEXT["ru"].get(key, key))
    try:
        return template.format(**values)
    except (KeyError, ValueError):
        return template


def localize_text(value: object, locale: str) -> str:
    text = "" if value is None else str(value)
    code = normalize_language(locale)
    if code == "ru":
        return text
    text = _EXACT.get(code, {}).get(text, text)
    for source, target in _PHRASES.get(code, ()):
        text = text.replace(source, target)
    return text


def localize_table(table: HtmlReportTable | None, locale: str) -> HtmlReportTable | None:
    if table is None:
        return None
    return HtmlReportTable(
        title=localize_text(table.title, locale),
        headers=tuple(localize_text(item, locale) for item in table.headers),
        rows=tuple(tuple(localize_text(cell, locale) for cell in row) for row in table.rows),
    )


def fluid_label(fluid_type: object, locale: str) -> str:
    key = str(fluid_type or "unknown").strip().lower()
    return tr(locale, f"fluid.{key}" if f"fluid.{key}" in _TEXT["ru"] else "fluid.unknown")
