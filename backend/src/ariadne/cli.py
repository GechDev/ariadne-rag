"""Command-line interface for the ARIADNE backend."""

from __future__ import annotations

import argparse
import sys

from ariadne.logging import configure_logging, get_logger


def _run_serve(args: argparse.Namespace) -> None:
    import uvicorn

    from ariadne.config import get_settings

    settings = get_settings()
    uvicorn.run(
        "ariadne.main:app",
        host=args.host,
        port=args.port,
        reload=settings.debug,
    )


def _run_init_db(args: argparse.Namespace) -> None:
    from ariadne.db.init import init_db

    init_db()
    get_logger("cli").info("database initialized")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ariadne", description="ARIADNE backend CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve = subparsers.add_parser("serve", help="run the HTTP API server")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=8000)
    serve.set_defaults(func=_run_serve)

    subparsers.add_parser("init-db", help="create database tables").set_defaults(func=_run_init_db)

    return parser


def main(argv: list[str] | None = None) -> None:
    configure_logging()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except KeyboardInterrupt:  # pragma: no cover
        sys.exit(130)


if __name__ == "__main__":
    main()
