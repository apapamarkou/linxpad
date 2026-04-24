import pytest

from linxpad.models import Application, Folder
from linxpad.services.config import ConfigService


@pytest.fixture
def tmp_config(tmp_path):
    return ConfigService(str(tmp_path / "apps.json"))


def test_save_and_load_roundtrip(tmp_config):
    app = Application(
        id="a1", name="Firefox", exec="firefox.desktop", icon_name="firefox", sort_id=0
    )
    folder = Folder(id="f1", name="Dev", app_ids=["a1"], sort_id=1)
    tmp_config.save({"a1": app}, {"f1": folder})

    apps, folders = tmp_config.load()
    assert "a1" in apps
    assert apps["a1"].name == "Firefox"
    assert apps["a1"].exec == "firefox.desktop"
    assert "f1" in folders
    assert folders["f1"].app_ids == ["a1"]


def test_load_missing_file_returns_empty(tmp_config):
    apps, folders = tmp_config.load()
    assert apps == {}
    assert folders == {}


def test_is_empty(tmp_config):
    assert tmp_config.is_empty()
    tmp_config.save({}, {})
    assert not tmp_config.is_empty()


def test_load_corrupt_file(tmp_path):
    cfg_file = tmp_path / "apps.json"
    cfg_file.write_text("not json")
    svc = ConfigService(str(cfg_file))
    apps, folders = svc.load()
    assert apps == {} and folders == {}
