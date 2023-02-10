import sys
import logging
from pathlib import Path
from argparse import ArgumentParser

from amalgamation import Amalgamation


_log = logging.getLogger(__name__)

if __name__ == '__main__':
    ap = ArgumentParser(description="Create C/C++ source code amalgamation")
    ap.add_argument("SOURCE", nargs="+", help="C/C++ source files")
    ap.add_argument("-o", "--output", type=Path, help="Output to a specific file instead of stdout")
    args = ap.parse_args()

    sources = [Path(p) for p in args.SOURCE]
    for source in sources:
        if not source.exists():
            _log.error(f"Input source path does not exist: {source}")
            sys.exit(1)

    amalgamation = Amalgamation()
    amalgamation.parse(sources=sources)

    output = args.output
    if output is not None:
        amalgamation.dump(file=output)
    else:
        amalgamation.print()
