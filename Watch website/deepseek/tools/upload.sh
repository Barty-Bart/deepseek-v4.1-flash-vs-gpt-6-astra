#!/usr/bin/env bash
# Upload a local file to a presigned url obtained from the media_upload tool.
# curl is used deliberately: Python's urllib rewrites the Content-Type header and
# that invalidates the AWS signature (403).
#   tools/upload.sh <file> <content_type> <upload_url>
set -euo pipefail
file="$1"; ctype="$2"; url="$3"
curl -sS -o /dev/null -w "uploaded %{http_code} %{size_upload} bytes\n" \
  -X PUT -H "Content-Type: ${ctype}" --data-binary "@${file}" "${url}"
