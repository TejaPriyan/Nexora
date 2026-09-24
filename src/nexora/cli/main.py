"""NEXORA command-line interface.

Deliberately stdlib-only (argparse) so `nexora doctor`/`nexora version`
always work even in the lightweight base install.
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

from .. import __version__
from ..plugins import available_features

# feature -> the import name of the module its pip extra installs
OPTIONAL_EXTRAS = {
    "ghost": "rich",
    "world": "pygame",
    "vision": "PIL",
}


def _is_installed(module_name: str) -> bool:
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False


def cmd_version(_args: argparse.Namespace) -> int:
    print(f"nexora {__version__}")
    return 0


def cmd_doctor(_args: argparse.Namespace) -> int:
    print(f"nexora {__version__} -- environment check\n")
    print("Core:        OK (stdlib only)")
    for feature, module_name in OPTIONAL_EXTRAS.items():
        status = "installed" if _is_installed(module_name) else "not installed"
        print(f"[{feature:<10}] extra -> {module_name:<8} : {status}")
    ai_status = "installed" if _is_installed("numpy") else "not installed"
    print(f"[{'ai':<10}] extra -> numpy    : {ai_status}\n")
    print("Planned features (see docs/ROADMAP.md):")
    for name in sorted(available_features()):
        print(f"  - {name}")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    target = Path(args.path)
    target.mkdir(parents=True, exist_ok=True)
    app_file = target / "app.py"
    if app_file.exists() and not args.force:
        print(f"{app_file} already exists (use --force to overwrite)")
        return 1
    app_file.write_text(
        '"""A new NEXORA application, scaffolded by `nexora init`."""\n\n'
        "from nexora import App\n\n"
        "app = App()\n\n\n"
        "@app.task\n"
        "def hello():\n"
        '    print("Hello from NEXORA!")\n\n\n'
        'if __name__ == "__main__":\n'
        "    app.run()\n"
    )
    print(f"Created {app_file}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nexora", description="NEXORA runtime CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("version", help="Print the installed nexora version").set_defaults(
        func=cmd_version
    )

    sub.add_parser(
        "doctor", help="Check which optional extras are installed"
    ).set_defaults(func=cmd_doctor)

    init_parser = sub.add_parser("init", help="Scaffold a new NEXORA app")
    init_parser.add_argument("path", nargs="?", default=".", help="Target directory")
    init_parser.add_argument(
        "--force", action="store_true", help="Overwrite an existing app.py"
    )
    init_parser.set_defaults(func=cmd_init)

    return parser


def main(argv: "list[str] | None" = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
