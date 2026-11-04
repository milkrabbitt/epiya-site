# EPIYA company website

Production: https://epiya.cn/  
Company: 杭州壹湃科技有限公司

The live website uses the existing Aliyun ECS. GitHub Pages is a retained historical configuration; pushing this repository alone is not a production ECS deployment.

## Build

Python 3: run python3 tools/build.py. The pages are buildless HTML/CSS/JavaScript at runtime. Update releases.json for download/channel metadata; do not advertise unpublished binaries. Optimized product screenshots are checked in under assets/, with source descriptions in tools/sources.json.

The old meow/ policy/help paths and original product assets remain available. Current founder attribution is 42; public contact uses the user-provided enterprise WeChat QR. Official mailbox delivery is still pending verification. /v1/, /healthz, /upload, /upload.js, /upload.css, /privacy, /support, and /policy.css belong to the existing Relic backend. Never replace their Nginx locations with a catch-all frontend route.

Relic purchases and website login remain closed. The separate private account/billing integration sandbox is not part of this public repository and must never be copied here.

## Design references

Original graphite visual system, outlined EPIYA wordmark, proportional product screenshots and event-driven material response. Methods studied from the official [Linear](https://linear.app), [Nothing](https://nothing.tech), [teenage engineering](https://teenage.engineering) and [Refik Anadol Studio](https://refikanadolstudio.com) sites: clear product hierarchy, restraint, confident product scale and motion that supports content. No reference brand artwork is reused.

## Release safety

Static production packages exclude .git, tools, private runtime files and all Relic server code. Deployment verifies archive SHA256, keeps the previous static root, uses an atomic directory/symlink exchange and checks both the website and the unchanged Relic health route. Source and production provenance are recorded separately in the deployment receipt.

Second redesign: the visual brief and layout reference Frontend Design (Apache-2.0) and UI UX Pro Max (MIT). React Bits was studied for interaction pacing; no React Bits component source is included. SVG wordmarks are original geometry derived from the user-provided Epiya mark. No external font is fetched. Product screenshots and synthetic examples are distinguished in page captions.
