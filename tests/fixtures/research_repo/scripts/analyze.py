#!/usr/bin/env python3

from pathlib import Path


def main() -> None:
    print(Path("results") / "summary.csv")


if __name__ == "__main__":
    main()
