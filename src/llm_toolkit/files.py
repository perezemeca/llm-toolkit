from __future__ import annotations

from pathlib import Path


RTK_BEGIN = "<!-- LLM-TOOLKIT:RTK:BEGIN -->"
RTK_END = "<!-- LLM-TOOLKIT:RTK:END -->"


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def append_unique_line(path: Path, line: str) -> bool:
    content = read_text(path)
    lines = content.splitlines()
    if line in lines:
        return False
    suffix = "\n" if content and not content.endswith("\n") else ""
    write_text(path, f"{content}{suffix}{line}\n")
    return True


def render_marked_block(block_body: str) -> str:
    clean_body = block_body.strip("\n")
    return f"{RTK_BEGIN}\n{clean_body}\n{RTK_END}"


def upsert_marked_block(content: str, block_body: str) -> str:
    marked_block = render_marked_block(block_body)
    if RTK_BEGIN in content and RTK_END in content:
        before, rest = content.split(RTK_BEGIN, 1)
        _, after = rest.split(RTK_END, 1)
        updated = before.rstrip() + "\n\n" + marked_block + after
        return updated.strip() + "\n"
    if not content.strip():
        return marked_block + "\n"
    return content.rstrip() + "\n\n" + marked_block + "\n"


def upsert_agents_block(root: Path, block_body: str) -> bool:
    path = root / "AGENTS.md"
    before = read_text(path)
    after = upsert_marked_block(before, block_body)
    if before == after:
        return False
    write_text(path, after)
    return True


def ensure_rtk_excluded(root: Path, git_enabled: bool) -> Path:
    if git_enabled:
        target = root / ".git" / "info" / "exclude"
    else:
        target = root / ".gitignore"
    append_unique_line(target, ".rtk/")
    return target


def skill_has_valid_frontmatter(path: Path) -> bool:
    content = read_text(path)
    if not content.startswith("---\n"):
        return False
    parts = content.split("---", 2)
    if len(parts) < 3:
        return False
    frontmatter = parts[1]
    return "name:" in frontmatter and "description:" in frontmatter
