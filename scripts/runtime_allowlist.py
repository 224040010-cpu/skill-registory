#!/usr/bin/env python3
"""Compatibility entry point; use publish_catalog.py for new integrations."""

from publish_catalog import main


if __name__ == "__main__":
    print("DEPRECATED: use scripts/publish_catalog.py", flush=True)
    main()
