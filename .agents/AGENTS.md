# ToonShorts

An automated end-to-end Python pipeline for creating short, funny, animated vertical videos for YouTube Shorts.
It generates screenplays, voiceovers, camera motion, and subtitle burn-ins across multiple visual art styles.
The codebase is structured around a plugin architecture with isolated core logic and self-updating documentation.

## Agent Guidelines
1. Read docs/CODEMAP.md first, open only the files you need.
2. Before changing a module, check its Used-by list and run the tests for those modules.
3. After any change: update the file headers, run tools/update_docs.py, update FEATURES.md, add one CHANGELOG line, run all tests.
4. New voice engines, renderers, providers, and styles are plugins: follow docs/ARCHITECTURE.md.
5. Never append history or logs to this file.
