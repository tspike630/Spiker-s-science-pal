#!/usr/bin/python3 -I
"""Link the research skill into the agent directories Omarchy already reads."""

import os
from pathlib import Path

PACKAGE = Path(os.environ.get("SPIKERS_SCIENCE_PAL_SKILL_DIR")
               or "/usr/share/spikers-science-pal-research/skills/spikers-research")
TARGETS = (
    ".agents/skills/spikers-research",
    ".claude/skills/spikers-research",
    ".codex/skills/spikers-research",
    ".config/opencode/skills/spikers-research",
)


def main():
    if not (PACKAGE / "SKILL.md").is_file():
        return 0
    home = Path(os.environ["HOME"])
    for relative in TARGETS:
        link = home / relative
        link.parent.mkdir(parents=True, exist_ok=True)
        if link.is_symlink() or link.exists():
            if link.is_symlink() and link.resolve() == PACKAGE.resolve():
                continue
            if link.is_symlink():
                link.unlink()
            else:
                continue
        link.symlink_to(PACKAGE, target_is_directory=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
