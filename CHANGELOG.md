# Changelog

All notable changes to the `tryiton` Python SDK are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Deprecated

- `try_on_fashion(mode=..., moderation_level=...)`: the API ignores `mode` and validates `moderation_level` without applying it. Passing either now emits a `DeprecationWarning`; both are removed in 3.0.

## [2.1.0] - 2026-11-26

### Added

- Live (real-time webcam) try-on endpoints: `get_live_config`, `prepare_live_garment`, `start_live_session`,
  `get_live_session` and `stop_live_session`.
- Every request sends `User-Agent: tryiton-python/<version>`.
- Typed responses: `TypedDict`s `LiveConfig`, `LiveGarment`, `LiveSession`, `LiveSessionStart` (plus the nested
  `LiveGarmentInput`, `LiveSessionGarment`, `LiveConnection`) in `tryiton.types`, re-exported from `tryiton`. They are
  plain dicts at runtime. `Status` and `Credits` stay dataclasses and now live in `tryiton.types` too (still importable
  from `tryiton` and `tryiton.client`).
- `py.typed` marker, so type checkers use the package's annotations.
- The shared cross-SDK contract tests, unit tests, and a GitHub Actions workflow (Python 3.8 to 3.13, pytest + mypy).
  `pip install -e ".[dev]"` installs the tooling.

### Fixed

- API errors now carry the backend's `error.name` and `error.message` (`{"ok": false, "error": {...}}`). Before, the
  message was always `HTTP <status>` and `error_name` was empty. Legacy top-level `error`/`message` strings still work.
- `wait_for_result` on a failed job raised `AttributeError` instead of `TryItOnError`, because `GET /status` sends the
  failure reason as a plain string. It now raises `TryItOnError` with that reason as the message and `error_name`
  `"ProcessingError"`.
- `get_status` (and so `wait_for_result`) URL-escapes the job id.
- `Status.error` is annotated as `Optional[str]`, matching what the API returns (was `Optional[Dict[str, str]]`).
- `tryiton.__version__` was stuck at `0.1.0`; it now matches the package version.

## [2.0.0] - 2026-07-14

### Changed

- **Breaking:** `try_on_clothes` is now `try_on_fashion` and calls `POST /tryon/fashion` (it covers clothing, footwear,
  eyewear, headwear, jewelry and accessories).

## [1.1.0] - 2026-07-14

### Added

- `region` for `try_on_tattoo`: pins the tattoo to a normalized `{x, y, w, h}` box on the body image.

## [1.0.0] - 2026-06-24

### Added

- `num_samples` (1-4) and `output_format` (`png`/`jpeg`) on every try-on.

### Removed

- **Breaking:** the `seed`, `segmentation_free` and `garment_photo_type` options of the clothes try-on.

## [0.1.0] - 2026-06-22

### Added

- Initial release: clothing/accessory, hairstyle and tattoo try-on, `get_status`, `get_credits` and the
  `wait_for_result` polling helper.

[Unreleased]: https://github.com/tryiton-now/tryiton-python/compare/v2.1.0...HEAD
[2.1.0]: https://github.com/tryiton-now/tryiton-python/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/tryiton-now/tryiton-python/compare/v1.1.0...v2.0.0
[1.1.0]: https://github.com/tryiton-now/tryiton-python/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/tryiton-now/tryiton-python/compare/v0.1.0...v1.0.0
[0.1.0]: https://github.com/tryiton-now/tryiton-python/releases/tag/v0.1.0
