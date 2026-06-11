#!/usr/bin/env python3

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--write", action="store_true")
    return parser


if __name__ == "__main__":
    build_parser().parse_args()
