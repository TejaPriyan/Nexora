from nexora.cli.main import build_parser


def test_version_command(capsys):
    parser = build_parser()
    args = parser.parse_args(["version"])
    assert args.func(args) == 0
    out = capsys.readouterr().out
    assert "nexora" in out


def test_doctor_command(capsys):
    parser = build_parser()
    args = parser.parse_args(["doctor"])
    assert args.func(args) == 0
    out = capsys.readouterr().out
    assert "Planned features" in out
    assert "ghost" in out


def test_init_command(tmp_path, capsys):
    parser = build_parser()
    args = parser.parse_args(["init", str(tmp_path / "myapp")])
    assert args.func(args) == 0
    created = tmp_path / "myapp" / "app.py"
    assert created.exists()
    assert "from nexora import App" in created.read_text()


def test_init_refuses_overwrite_without_force(tmp_path, capsys):
    parser = build_parser()
    target = tmp_path / "myapp"
    args = parser.parse_args(["init", str(target)])
    args.func(args)
    args2 = parser.parse_args(["init", str(target)])
    assert args2.func(args2) == 1
