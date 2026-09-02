import projects.fields as flds


def test_get_flds():
    assert isinstance(flds.get_flds(), dict)


def test_get_fld_names():
    names = flds.get_fld_names()
    assert isinstance(names, list)
    assert len(names) > 0
    for name in names:
        assert isinstance(name, str)


def test_get_disp_name():
    disp_nm = flds.get_disp_name(flds.TEST_FLD_NM)
    assert disp_nm == flds.TEST_FLD_DISP_NM
