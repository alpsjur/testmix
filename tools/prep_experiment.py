#!/usr/bin/env python3
"""
setup_experiment.py

Resolve a baseline config with an optional override OR accept a resolved config dict,
set up runs/<name>/, generate grid/ini/bry files using tools/* helpers, and render the ROMS
input file from templates/testmix.in.j2.

Usage (standalone):
  python setup_experiment.py configs/baseline.yaml [configs/override.yaml]

Usage (from code, e.g., in a sweep):
  from setup_experiment import prepare_run_from_resolved
  result = prepare_run_from_resolved(cfg)  # cfg is already resolved
"""

import os
import sys
import yaml
from copy import deepcopy
from jinja2 import Environment, FileSystemLoader
import hashlib
import copy

# Tools
from tools.make_grd import make_grid_from_config
from tools.make_ini import make_ini_from_config
from tools.make_bry import make_bry_from_config


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def config_hash(cfg: dict) -> str:
    """Exact hash of the fully resolved config (including run/io)."""
    dumped = yaml.safe_dump(cfg, sort_keys=True)
    return _sha256_hex(dumped)[:12]


def deep_merge(a: dict, b: dict) -> dict:
    """Deep-merge dict b into a and return a new dict (b overrides a)."""
    out = deepcopy(a)
    for k, v in (b or {}).items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = deepcopy(v)
    return out


def resolve_config(baseline_path: str, override_path: str | None = None) -> dict:
    """Load baseline (+ optional override) and return resolved config."""
    with open(baseline_path, "r") as f:
        base = yaml.safe_load(f) or {}
    over = {}
    if override_path:
        with open(override_path, "r") as f:
            over = yaml.safe_load(f) or {}
    return deep_merge(base, over)


def prepare_run_dirs(run_name: str) -> tuple[str, str, str, str]:
    """Create runs/<name>/{input,output,logs} and return (run_dir, input_dir, output_dir, logs_dir)."""
    run_dir = os.path.join("runs", run_name)
    input_dir = os.path.join(run_dir, "input")
    output_dir = os.path.join(run_dir, "output")
    logs_dir = os.path.join(run_dir, "logs")
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)
    return run_dir, input_dir, output_dir, logs_dir


def write_resolved_config(cfg: dict, run_dir: str) -> str:
    """Write resolved_config.yaml into the run directory and return its path."""
    resolved_path = os.path.join(run_dir, "resolved_config.yaml")
    with open(resolved_path, "w") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)
    return resolved_path


def render_roms_input(cfg: dict, input_dir: str, template_dir: str = "templates", template_name: str = "testmix.in.j2") -> str:
    """Render ROMS input file from template into runs/<name>/input/testmix.in and return its path."""
    env = Environment(loader=FileSystemLoader(template_dir), autoescape=False)
    tmpl = env.get_template(template_name)
    rendered = tmpl.render(**cfg)
    out_in_path = os.path.join(input_dir, "testmix.in")
    with open(out_in_path, "w") as f:
        f.write(rendered)
    return out_in_path


def prepare_run_from_resolved(cfg: dict) -> dict:
    """
    Prepare a run from an already-resolved config dict.
    - Creates runs/<name>/{input,output,logs}
    - Writes resolved_config.yaml
    - Generates grid, ini, bry via tools/*
    - Renders templates/testmix.in.j2
    Returns a dict with paths for convenience.
    """
    run_name = cfg["run"]["name"]
    run_dir, input_dir, output_dir, logs_dir = prepare_run_dirs(run_name)

    cfg.setdefault("io", {})
    cfg["io"]["input_dir"] = input_dir
    cfg["io"]["output_dir"] = output_dir

    # Inject hashes into _meta
    cfg.setdefault("_meta", {})
    cfg["_meta"]["hash"] = {
        "exact": config_hash(cfg),
    }

    resolved_path = write_resolved_config(cfg, run_dir)

    # Generate artifacts
    grid_path = make_grid_from_config(cfg)
    ini_path = make_ini_from_config(cfg)
    bry_path = make_bry_from_config(cfg)
    in_path = render_roms_input(cfg, input_dir)

    # Summary
    print("Prepared run:")
    print(f"- run dir:    {run_dir}")
    print(f"- grid:       {grid_path}")
    print(f"- ini:        {ini_path}")
    print(f"- bry:        {bry_path}")
    print(f"- input:      {in_path}")
    print(f"- snapshot:   {resolved_path}")
    print(f"- output dir: {output_dir}")
    print(f"- logs dir:   {logs_dir}")

    return {
        "run_dir": run_dir,
        "input_dir": input_dir,
        "output_dir": output_dir,
        "logs_dir": logs_dir,
        "resolved_config": resolved_path,
        "grid": grid_path,
        "ini": ini_path,
        "bry": bry_path,
        "in_file": in_path,
        "hash_exact": cfg["_meta"]["hash"]["exact"], 
    }


def main():
    """CLI entry point: resolve baseline + optional override, then prepare the run."""
    baseline_path = sys.argv[1] if len(sys.argv) > 1 else "configs/baseline.yaml"
    override_path = sys.argv[2] if len(sys.argv) > 2 else None

    cfg = resolve_config(baseline_path, override_path)
    prepare_run_from_resolved(cfg)


if __name__ == "__main__":
    main()