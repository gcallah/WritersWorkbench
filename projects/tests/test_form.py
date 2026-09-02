import projects.form as form


def test_get_form():
    assert isinstance(form.get_form(), list)


def test_get_form_descr():
    assert isinstance(form.get_form_descr(), dict)


def test_get_fld_names():
    assert isinstance(form.get_fld_names(), list)
