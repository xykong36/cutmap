# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html) (pre-1.0: minor bumps may
include breaking changes).

## [0.2.0] - 2026-07-21

### Changed
- **Breaking: output and directory-convention filenames are now English.** The generated
  browse page is `browse.html` (was `浏览.html`); directory-mode inputs default to
  `source.mp4` and `subtitle.srt` (were `源片.mp4` / `字幕.srt`). Re-run cutmap to
  regenerate pages, or rename existing files.
- Repositioned the README around its two real use cases — skimming a video to learn fast
  and studying an edit shot-by-shot ("拉片") — with the algorithm internals moved into
  collapsible sections. English README is now primary; Chinese lives in `README.zh-CN.md`.

### Added
- Bundled [Claude Code](https://claude.com/claude-code) skill (`skills/cutmap`): install
  it once and drive cutmap with a single plain-language sentence — the agent downloads
  the video, runs cutmap, and reads the result for you.

## [0.1.1] - 2026-07-20

### Fixed
- Broken images and links on the PyPI project page; switched PyPI metadata to English.

## [0.1.0] - 2026-07-20

### Added
- Initial release: perceptual-hash frame dedup, contact sheets, `index.json`, automatic
  B-roll extraction, subtitle term normalisation, and a self-contained browse page.

[0.2.0]: https://github.com/xykong36/cutmap/releases/tag/v0.2.0
[0.1.1]: https://github.com/xykong36/cutmap/releases/tag/v0.1.1
[0.1.0]: https://github.com/xykong36/cutmap/releases/tag/v0.1.0
