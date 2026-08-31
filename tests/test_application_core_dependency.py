def test_application_layer_can_use_core():
    from application.core_dependency import load_text_file

    assert load_text_file is not None