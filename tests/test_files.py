from pathlib import Path

from llm_toolkit.files import RTK_BEGIN, atomic_write_text, ensure_rtk_excluded, skill_has_valid_frontmatter, upsert_agents_block, write_text


def test_insertar_bloque_rtk_sin_duplicarlo(tmp_path: Path) -> None:
    body = "## RTK\n\nContenido"

    upsert_agents_block(tmp_path, body)
    upsert_agents_block(tmp_path, body)

    content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert content.count(RTK_BEGIN) == 1


def test_reemplazar_bloque_rtk_existente(tmp_path: Path) -> None:
    path = tmp_path / "AGENTS.md"
    path.write_text("Antes\n\n<!-- LLM-TOOLKIT:RTK:BEGIN -->\nviejo\n<!-- LLM-TOOLKIT:RTK:END -->\n", encoding="utf-8")

    upsert_agents_block(tmp_path, "nuevo")

    content = path.read_text(encoding="utf-8")
    assert "nuevo" in content
    assert "viejo" not in content
    assert content.count(RTK_BEGIN) == 1


def test_crear_skill_con_frontmatter_valido(tmp_path: Path) -> None:
    path = tmp_path / ".agents" / "skills" / "rtk-codex" / "SKILL.md"
    write_text(path, "---\nname: rtk-codex\ndescription: Demo\n---\n\nContenido\n")

    raw = path.read_bytes()
    assert raw.startswith(b"---")
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert skill_has_valid_frontmatter(path) is True


def test_excluir_rtk_con_git_en_info_exclude(tmp_path: Path) -> None:
    (tmp_path / ".git" / "info").mkdir(parents=True)

    target = ensure_rtk_excluded(tmp_path, git_enabled=True)

    assert target == tmp_path / ".git" / "info" / "exclude"
    assert ".rtk/" in target.read_text(encoding="utf-8")
    assert not (tmp_path / ".gitignore").exists()


def test_excluir_rtk_sin_git_en_gitignore(tmp_path: Path) -> None:
    target = ensure_rtk_excluded(tmp_path, git_enabled=False)

    assert target == tmp_path / ".gitignore"
    assert ".rtk/" in target.read_text(encoding="utf-8")


def test_atomic_write_crea_archivo_final(tmp_path: Path) -> None:
    target = tmp_path / ".llm-toolkit" / "state" / "context_health.json"

    atomic_write_text(target, "{}\n")

    assert target.read_text(encoding="utf-8") == "{}\n"


def test_atomic_write_reemplaza_contenido(tmp_path: Path) -> None:
    target = tmp_path / "state.json"
    atomic_write_text(target, "viejo\n")

    atomic_write_text(target, "nuevo\n")

    assert target.read_text(encoding="utf-8") == "nuevo\n"


def test_atomic_write_no_deja_tmp_si_no_hay_error(tmp_path: Path) -> None:
    target = tmp_path / "state.json"

    atomic_write_text(target, "ok\n")

    assert not list(tmp_path.glob("*.tmp"))
