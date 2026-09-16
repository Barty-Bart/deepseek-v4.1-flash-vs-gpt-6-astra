#!/usr/bin/env python3
"""Deprecated: use tools/upload.sh instead.

Python's urllib normalises the Content-Type header, which invalidates the AWS
signature on the presigned upload url and returns 403. The shell helper uses curl
and works.
"""
raise SystemExit(__doc__)
