from core.data_platform import MetadataScanResult, build_metadata_import_preview


def _tr(key, **kwargs):
    values = {'import.preview.segy.summary':'SEG-Y preview','import.preview.field.trace_count':'Traces','import.preview.warning.segy.adapter.segyio_unavailable':'Unavailable'}
    return values.get(key, key).format(**kwargs)


def test_preview_is_compact_and_localized():
    result = MetadataScanResult(format_id='segy', metadata={'trace_count':5, 'ignored':'payload'}, warnings=('segy.adapter.segyio_unavailable',))
    preview = build_metadata_import_preview(result, _tr)
    assert preview['summary'] == 'SEG-Y preview'
    assert preview['fields'] == [{'key':'trace_count','label':'Traces','value':5}]
    assert preview['warnings'][0]['code'] == 'segy.adapter.segyio_unavailable'
