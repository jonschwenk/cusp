from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from cusp.features.models import FeatureDefinition


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = REPO_ROOT / "docs"
FENCE_PATTERN = re.compile(
    r"^```(?P<info>[^\n]*)\n(?P<code>.*?)^```[ \t]*$",
    flags=re.MULTILINE | re.DOTALL,
)
INLINE_CODE_PATTERN = re.compile(r"`([^`\n]+)`")


@dataclass(frozen=True)
class MarkdownCodeBlock:
    path: Path
    line: int
    language: str
    code: str

    @property
    def label(self) -> str:
        return f"{self.path.relative_to(REPO_ROOT)}:{self.line}"


@dataclass(frozen=True)
class DocumentedCliCommand:
    block: MarkdownCodeBlock
    command: str
    tokens: tuple[str, ...]

    @property
    def module(self) -> str:
        return self.tokens[2]

    @property
    def subcommand(self) -> str | None:
        tail = self.tokens[3:]
        if self.module == "cusp.qc" and tail and not tail[0].startswith("-"):
            return tail[0]
        return None

    @property
    def options(self) -> set[str]:
        return {
            token.split("=", 1)[0]
            for token in self.tokens[3:]
            if token.startswith("--")
        }


def documentation_code_blocks() -> list[MarkdownCodeBlock]:
    blocks: list[MarkdownCodeBlock] = []
    for path in sorted(DOCS_ROOT.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        for match in FENCE_PATTERN.finditer(text):
            info = match.group("info").strip()
            language = info.split(maxsplit=1)[0].lower() if info else ""
            blocks.append(
                MarkdownCodeBlock(
                    path=path,
                    line=text.count("\n", 0, match.start()) + 1,
                    language=language,
                    code=match.group("code").rstrip(),
                )
            )
    return blocks


def documented_cusp_commands() -> list[DocumentedCliCommand]:
    commands: list[DocumentedCliCommand] = []
    for block in documentation_code_blocks():
        if block.language not in {"bash", "powershell"}:
            continue

        continuation = "`" if block.language == "powershell" else "\\"
        lines = block.code.splitlines()
        index = 0
        while index < len(lines):
            line = lines[index].strip()
            if not re.match(r"^python\s+-m\s+cusp(?:\.[A-Za-z_][A-Za-z0-9_]*)+", line):
                index += 1
                continue

            fragments = [line]
            while fragments[-1].endswith(continuation):
                fragments[-1] = fragments[-1][: -len(continuation)].rstrip()
                index += 1
                if index >= len(lines):
                    raise AssertionError(f"Unfinished command continuation at {block.label}")
                fragments.append(lines[index].strip())

            command = " ".join(fragments)
            commands.append(
                DocumentedCliCommand(
                    block=block,
                    command=command,
                    tokens=tuple(shlex.split(command, posix=True)),
                )
            )
            index += 1
    return commands


class DocumentationExampleTests(unittest.TestCase):
    def test_python_blocks_compile(self) -> None:
        for block in documentation_code_blocks():
            if block.language != "python":
                continue
            with self.subTest(block=block.label):
                compile(block.code, block.label, "exec")

    def test_executable_blocks_do_not_contain_literal_placeholders(self) -> None:
        forbidden = (
            "<your-earth-engine-project>",
            "path/to/",
            "/tmp/",
            "MY/DATASET/PATH",
        )
        for block in documentation_code_blocks():
            if block.language not in {"bash", "powershell", "python"}:
                continue
            with self.subTest(block=block.label):
                for placeholder in forbidden:
                    self.assertNotIn(placeholder, block.code)

    @unittest.skipIf(os.name == "nt", "Bash syntax is checked on Linux CI.")
    def test_bash_blocks_parse(self) -> None:
        for block in documentation_code_blocks():
            if block.language != "bash":
                continue
            with self.subTest(block=block.label):
                result = subprocess.run(
                    ["bash", "-n"],
                    input=block.code,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_documented_cusp_options_exist(self) -> None:
        required_options = {
            "cusp.citations": {"--input"},
            "cusp.features": {"--input"},
            "cusp.export": {"--version"},
        }
        help_options: dict[tuple[str, str | None], set[str]] = {}

        for documented in documented_cusp_commands():
            signature = (documented.module, documented.subcommand)
            if signature not in help_options:
                help_command = [sys.executable, "-m", documented.module]
                if documented.subcommand is not None:
                    help_command.append(documented.subcommand)
                help_command.append("--help")
                result = subprocess.run(
                    help_command,
                    cwd=REPO_ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(
                    result.returncode,
                    0,
                    f"{' '.join(help_command)} failed:\n{result.stdout}\n{result.stderr}",
                )
                help_options[signature] = set(
                    re.findall(r"--[a-z][a-z0-9-]*", result.stdout + result.stderr)
                )

            with self.subTest(block=documented.block.label, command=documented.command):
                self.assertEqual(documented.options - help_options[signature], set())
                if "--help" not in documented.options:
                    self.assertEqual(
                        required_options.get(documented.module, set()) - documented.options,
                        set(),
                    )

    def test_inline_export_commands_include_version(self) -> None:
        for path in sorted(DOCS_ROOT.rglob("*.md")):
            text = path.read_text(encoding="utf-8")
            for code in INLINE_CODE_PATTERN.findall(text):
                if not code.startswith("python -m cusp.export"):
                    continue
                with self.subTest(path=path.relative_to(REPO_ROOT), command=code):
                    self.assertIn("--version", shlex.split(code))

    def test_getting_started_python_and_citation_workflow(self) -> None:
        page = DOCS_ROOT / "getting-started" / "using-the-data.md"
        python_blocks = [
            block
            for block in documentation_code_blocks()
            if block.path == page and block.language == "python"
        ]
        citation_command = next(
            command
            for command in documented_cusp_commands()
            if command.block.path == page and command.module == "cusp.citations"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            workdir = Path(temp_dir)
            shutil.copy2(REPO_ROOT / "exports" / "latest" / "cusp_v1.1.csv", workdir)
            shutil.copy2(
                REPO_ROOT / "exports" / "latest" / "cusp_sources_v1.1.bib",
                workdir,
            )

            for block in python_blocks:
                result = subprocess.run(
                    [sys.executable, "-c", block.code],
                    cwd=workdir,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(
                    result.returncode,
                    0,
                    f"{block.label} failed:\n{result.stdout}\n{result.stderr}",
                )

            citation_tokens = [sys.executable, *citation_command.tokens[1:]]
            subprocess_env = os.environ.copy()
            subprocess_env["PYTHONPATH"] = os.pathsep.join(
                filter(None, [str(REPO_ROOT), subprocess_env.get("PYTHONPATH", "")])
            )
            result = subprocess.run(
                citation_tokens,
                cwd=workdir,
                env=subprocess_env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(
                result.returncode,
                0,
                f"{citation_command.command} failed:\n{result.stdout}\n{result.stderr}",
            )
            self.assertGreater((workdir / "lower_bound_absences.csv").stat().st_size, 0)
            self.assertGreater(
                (workdir / "lower_bound_absence_references.bib").stat().st_size,
                0,
            )

    def test_contributor_feature_example_registers_and_builds_smoke_input(self) -> None:
        page = DOCS_ROOT / "contributing" / "adding-gee-features.md"
        python_blocks = [
            block
            for block in documentation_code_blocks()
            if block.path == page and block.language == "python"
        ]
        function_block = next(block for block in python_blocks if "def sample_example_hand" in block.code)
        registry_block = next(
            block for block in python_blocks if 'FEATURE_REGISTRY["example_hand"]' in block.code
        )
        smoke_input_block = next(
            block for block in python_blocks if "cusp_v1.1_smoke25.csv" in block.code
        )

        namespace: dict[str, object] = {
            "FEATURE_REGISTRY": {},
            "FeatureDefinition": FeatureDefinition,
            "_sample_static_image": lambda **kwargs: kwargs,
        }
        exec(function_block.code, namespace)
        exec(registry_block.code, namespace)
        definition = namespace["FEATURE_REGISTRY"]["example_hand"]  # type: ignore[index]
        self.assertEqual(definition.output_columns, ("example_hand",))

        class FakeImage:
            def select(self, band: str) -> "FakeImage":
                self.band = band
                return self

        class FakeEarthEngine:
            @staticmethod
            def Image(asset: str) -> FakeImage:
                image = FakeImage()
                image.asset = asset
                return image

        sampled = namespace["sample_example_hand"](
            "table",
            "config",
            SimpleNamespace(ee=FakeEarthEngine()),
        )
        self.assertEqual(sampled["output_name"], "example_hand")
        self.assertEqual(sampled["image"].asset, "MERIT/Hydro/v1_0_1")
        self.assertEqual(sampled["image"].band, "hnd")

        with tempfile.TemporaryDirectory() as temp_dir:
            workdir = Path(temp_dir)
            release_dir = workdir / "exports" / "latest"
            release_dir.mkdir(parents=True)
            shutil.copy2(REPO_ROOT / "exports" / "latest" / "cusp_v1.1.csv", release_dir)
            result = subprocess.run(
                [sys.executable, "-c", smoke_input_block.code],
                cwd=workdir,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(
                result.returncode,
                0,
                f"{smoke_input_block.label} failed:\n{result.stdout}\n{result.stderr}",
            )
            smoke_input = pd.read_csv(workdir / "runs" / "examples" / "cusp_v1.1_smoke25.csv")
            self.assertEqual(len(smoke_input), 25)


if __name__ == "__main__":
    unittest.main()
