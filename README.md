# EPIYA company website

Production: https://epiya.cn/  
Company: 杭州壹湃科技有限公司

The live website uses the existing Aliyun ECS. GitHub Pages is a retained historical configuration; pushing this repository alone is not a production ECS deployment.

## Build

Python 3: run python3 tools/build.py. The pages are buildless HTML/CSS/JavaScript at runtime. Update releases.json for download/channel metadata; do not advertise unpublished binaries. Optimized product screenshots are checked in under assets/, with source descriptions in tools/sources.json.

The old meow/ policy/help paths and their original assets remain available. /v1/, /healthz, /upload, /upload.js, /upload.css, /privacy, /support, and /policy.css belong to the existing Relic backend. Never replace their Nginx locations with a catch-all frontend route.

Relic purchases and website login remain closed. The separate private account/billing integration sandbox is not part of this public repository and must never be copied here.

## Design references

Original layout, typography and procedural fiber artwork. Methods studied from the official [Linear](https://linear.app), [Nothing](https://nothing.tech), [teenage engineering](https://teenage.engineering) and [Refik Anadol Studio](https://refikanadolstudio.com) sites: clear product hierarchy, restraint, confident product scale and motion that supports content. No reference brand artwork is reused.

## Release safety

Static production packages exclude .git, tools, private runtime files and all Relic server code. Deployment verifies archive SHA256, keeps the previous static root, uses an atomic directory/symlink exchange and checks both the website and the unchanged Relic health route. Source and production provenance are recorded separately in the deployment receipt.
