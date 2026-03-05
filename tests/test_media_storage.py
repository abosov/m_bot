from services.media_storage import sanitize_filename


def test_sanitize_filename_blocks_traversal_sequences():
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("..\\..\\secret.pdf") == "secret.pdf"
    assert sanitize_filename("/tmp/../../avatar.png") == "avatar.png"


def test_sanitize_filename_normalizes_symbols_and_empty_names():
    assert sanitize_filename("my photo (1).png") == "my_photo_1_.png"
    assert sanitize_filename("") == "file"
