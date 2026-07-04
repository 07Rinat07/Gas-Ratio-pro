from __future__ import annotations

import pandas as pd

from reports.export_las import export_las_bytes


def test_export_las_bytes_writes_curve_and_ascii_sections():
    df = pd.DataFrame({"DEPT": [1000.0, 1000.2], "C1": [80.0, None], "C2": [10.0, 9.0]})

    content = export_las_bytes(df, well_name="DEMO-1", depth_column="DEPT").decode("utf-8")

    assert "~Curve" in content
    assert "WELL. DEMO-1" in content
    assert "DEPT.M : DEPT" in content
    assert "C1. : C1" in content
    assert "1000 80 10" in content
    assert "1000.2 -999.25 9" in content
