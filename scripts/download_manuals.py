"""Download publicly available manufacturer manuals into data/manuals_real/.

    uv run python scripts/download_manuals.py

The PDFs are copyrighted by their manufacturers. They are fetched from the
manufacturers' own websites for local use and are never committed (the folder is
gitignored). A manifest with the source URL of every file is written next to them so
the ingestion pipeline can index them alongside the sample documents.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path

import httpx
import yaml
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "manuals_real"
USER_AGENT = "Mozilla/5.0 (compatible; MaintainAI manual downloader)"


@dataclass(frozen=True)
class Source:
    doc_id: str
    file: str
    title: str
    manufacturer: str
    machine_type: str
    url: str


SOURCES: tuple[Source, ...] = (
    Source(
        "THOMPSON-WPCP-TS",
        "thompson_wet_priming_centrifugal_troubleshooting.pdf",
        "Thompson Pump - Wet Priming Centrifugal Pump Troubleshooting Guide (Rev 2)",
        "Thompson Pump & Manufacturing",
        "pump",
        "https://www.thompsonpump.com/s/Wet-Priming-Centrifugal-Pump-Troubleshooting-Guide-Rev-2.pdf",
    ),
    Source(
        "THOMPSON-WPCP-DD",
        "thompson_wet_priming_centrifugal_dos_donts.pdf",
        "Thompson Pump - Wet Priming Centrifugal Pumps Do's and Don'ts (Rev 5)",
        "Thompson Pump & Manufacturing",
        "pump",
        "https://www.thompsonpump.com/s/Wet-Priming-Centrifugal-Pump-Dos-and-Donts-Rev-5.pdf",
    ),
    Source(
        "EATON-RS",
        "eaton_rotary_screw_compressor_manual.pdf",
        "Eaton Compressor - Rotary Screw Air Compressor Operating Instructions",
        "Eaton Compressor & Fabrication",
        "compressor",
        "https://eatoncompressor.com/wp-content/uploads/2024/10/eaton-rotary-screw-manual.pdf",
    ),
    Source(
        "SAYLOR-BEALL-700",
        "saylor_beall_700_series_owners_manual.pdf",
        "Saylor-Beall 703 / 705 / 707 Two-Stage Air Compressor Pumps - Owner's Manual",
        "Saylor-Beall Manufacturing",
        "compressor",
        "https://www.saylor-beall.com/wp-content/uploads/2025/07/SB-7OPS-Saylor-Beall-700-Series-Manual-1.pdf",
    ),
    Source(
        "BALDOR-MN408",
        "baldor_mn408_ac_induction_motors.pdf",
        "Baldor-Reliance MN408 - Integral Horsepower AC Induction Motors, "
        "Installation & Operating Manual",
        "Baldor Electric (ABB)",
        "motor",
        "https://www.baldor.com/mvc/DownloadCenter/Files/MN408",
    ),
    Source(
        "BALDOR-MN416",
        "baldor_mn416_motor_installation_maintenance.pdf",
        "Baldor-Reliance MN416 - AC & DC Motor Installation & Maintenance",
        "Baldor Electric (ABB)",
        "motor",
        "https://www.baldor.com/mvc/DownloadCenter/Files/MN416",
    ),
)


def fetch(client: httpx.Client, source: Source, *, force: bool) -> Path:
    target = OUT / source.file
    if target.exists() and not force:
        print(f"  have {source.file}")
        return target
    print(f"  downloading {source.url}")
    response = client.get(source.url)
    response.raise_for_status()
    if not response.content.startswith(b"%PDF"):
        raise RuntimeError(f"{source.url} did not return a PDF")
    target.write_bytes(response.content)
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="Download manufacturer manuals")
    parser.add_argument("--force", action="store_true", help="download again")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    entries, failed = [], []
    headers = {"User-Agent": USER_AGENT}
    with httpx.Client(headers=headers, follow_redirects=True, timeout=120) as client:
        for source in SOURCES:
            try:
                path = fetch(client, source, force=args.force)
            except (httpx.HTTPError, RuntimeError) as exc:
                print(f"  FAILED {source.doc_id}: {exc}", file=sys.stderr)
                failed.append(source.doc_id)
                continue
            entries.append(
                {
                    "file": source.file,
                    "doc_id": source.doc_id,
                    "title": source.title,
                    "machine_type": source.machine_type,
                    "access_level": "viewer",
                    "pages": len(PdfReader(path).pages),
                    "manufacturer": source.manufacturer,
                    "source_url": source.url,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )

    header = "# Written by scripts/download_manuals.py. Third-party documents, not committed.\n"
    manifest = OUT / "manifest.yaml"
    manifest.write_text(header + yaml.safe_dump({"documents": entries}, sort_keys=False))
    print(f"{len(entries)} manuals in {OUT.relative_to(ROOT)}; ingest them with `make ingest`.")
    if failed:
        sys.exit(f"could not download: {', '.join(failed)}")


if __name__ == "__main__":
    main()
