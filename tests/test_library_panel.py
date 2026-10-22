from PySide6.QtWidgets import QApplication

from linguapdf.domain.models import StudyFolder, StudyProject
from linguapdf.ui.i18n import set_language
from linguapdf.ui.library_panel import ROLE_TYPE, ProjectLibraryPanel
from linguapdf.ui.styles import build_stylesheet


def test_folder_tree_search_and_bilingual_theme_support() -> None:
    app = QApplication.instance() or QApplication([])
    set_language("en")
    panel = ProjectLibraryPanel()
    folder = StudyFolder("f1", "english_lessons", None, "now")
    nested = StudyFolder("f2", "travel", "f1", "now")
    project = StudyProject("p1", "airport_vocabulary", "vocabulary", "", "now", "now", 4, "f2")
    panel.set_library([folder, nested], [project], project.id)

    assert panel.tree.topLevelItemCount() == 1
    assert panel.tree.topLevelItem(0).data(0, ROLE_TYPE) == "folder"
    assert panel.current_folder_id == "f2"

    panel.search.setText("airport")
    app.processEvents()
    assert not panel.tree.topLevelItem(0).isHidden()
    panel.search.setText("missing")
    app.processEvents()
    assert panel.tree.topLevelItem(0).isHidden()

    set_language("vi")
    panel.retranslate_ui()
    assert panel.subtitle.text() == "THƯ VIỆN BÀI HỌC"
    assert "#0F172A" in build_stylesheet("dark")
    set_language("en")
    panel.close()
