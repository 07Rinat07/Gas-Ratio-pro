from reports.report_i18n import generated


def test_generated_summary_templates_are_language_specific():
    ru = generated('ru', 'summary.best_note', thickness='12.5', confidence='90%', total='22.0')
    kk = generated('kk', 'summary.best_note', thickness='12.5', confidence='90%', total='22.0')
    en = generated('en', 'summary.best_note', thickness='12.5', confidence='90%', total='22.0')
    assert 'Лучший интервал' in ru
    assert 'Үздік аралық' in kk
    assert 'Best interval' in en
    assert ru != kk != en


def test_generated_table_headers_are_localized():
    assert generated('ru', 'table.metric') == 'Показатель'
    assert generated('kk', 'table.metric') == 'Көрсеткіш'
    assert generated('en', 'table.metric') == 'Metric'
