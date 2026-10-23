"""Benchmark download scripts and loaders (M3, slide 23). Data lives under data/ and is never committed."""

from bench.loaders import LOADERS, load

__all__ = ["LOADERS", "load"]
