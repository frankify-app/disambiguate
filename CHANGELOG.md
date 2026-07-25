# Changelog

<!-- version list -->

## v0.2.1 (2026-07-25)

### Bug Fixes

- From-mode accepts document links when a source path is known
  ([`7470b81`](https://github.com/frankify-app/disambiguate/commit/7470b8132db3b11e447fb3c0437a7def39bc919f))

- Keep unknown wikilinks loud under resolve-then-classify
  ([`cf47ccb`](https://github.com/frankify-app/disambiguate/commit/cf47ccb184253575279e8d7ab799f71ff4eab80a))

- Pass the --from source path through the CLI
  ([`a315abe`](https://github.com/frankify-app/disambiguate/commit/a315abef15fe0367f3c99e3d0d80124cdb793fec))

- Resolve unknown-slug .md links against the source document
  ([`bca220a`](https://github.com/frankify-app/disambiguate/commit/bca220ac8ca7345f062c22f0e8e7836eb3829421))

### Documentation

- Enumerate every supported link form in cross-reference spec
  ([`149e8ff`](https://github.com/frankify-app/disambiguate/commit/149e8ffdccab04b1235268f0856e3f761a285173))

- From-mode spec describes resolve-then-classify
  ([`bb09b57`](https://github.com/frankify-app/disambiguate/commit/bb09b57e4ac9170795bfe005c74d252e930f6189))


## v0.2.0 (2026-07-13)

### Documentation

- Document display text and #fragment link forms
  ([`2e77292`](https://github.com/frankify-app/disambiguate/commit/2e77292cde58c5eb168e54d1691b436ce039ba09))

### Features

- **lint**: Fatal check for malformed piped wikilinks in term files
  ([`2cb3d81`](https://github.com/frankify-app/disambiguate/commit/2cb3d81b113224fc1d996a86749da06532cd4bfa))

- **parser**: Lenient Obsidian-style resolution of malformed pipe wikilinks
  ([`62fccf2`](https://github.com/frankify-app/disambiguate/commit/62fccf2f8a4ab18e99f4fffad0c9cd45eded2bfa))

- **parser**: Resolve display-text wikilinks to their slug
  ([`11232d1`](https://github.com/frankify-app/disambiguate/commit/11232d1183cbebdab253382f533a797171778868))

- **parser**: Strip #fragment from markdown .md links
  ([`d0a0f31`](https://github.com/frankify-app/disambiguate/commit/d0a0f31938765105afac84145dd8d119f536c1d2))

- **parser**: Strip #fragment from wikilink targets
  ([`be20fc6`](https://github.com/frankify-app/disambiguate/commit/be20fc6f3eb6b227e800604f8bc104d8f802ef3d))


## v0.1.4 (2026-07-13)

### Bug Fixes

- **ci**: Tolerate empty uv cache on no-op release runs
  ([`7c3def1`](https://github.com/frankify-app/disambiguate/commit/7c3def1b189eba212b27e7109682c272ae76a945))


## v0.1.3 (2026-07-12)

### Bug Fixes

- **release**: Install uv in semantic-release container and fail fast
  ([`7c42696`](https://github.com/frankify-app/disambiguate/commit/7c4269621c68a9309dba556cb8dd058a0d6ee2c3))


## v0.1.2 (2026-07-12)

### Bug Fixes

- **release**: Keep uv.lock in sync with semantic-release version bump
  ([`500324c`](https://github.com/frankify-app/disambiguate/commit/500324c95035863dcc07efc951d0a06425434960))

### Documentation

- **claude**: Drop stale ci_poll.py instructions
  ([`8760de0`](https://github.com/frankify-app/disambiguate/commit/8760de078a9450541d08c21a7ebad9e9afe7e06d))


## v0.1.1 (2026-07-12)

### Bug Fixes

- **ci**: Release from main branch checkout instead of detached HEAD
  ([`4c8449c`](https://github.com/frankify-app/disambiguate/commit/4c8449c797ae9fb49042a17544fe0532b1d37f5b))

- **tests**: Derive built artifact filenames from package version
  ([`1c38772`](https://github.com/frankify-app/disambiguate/commit/1c387729f02223a385a2459ff9231505503fb394))


## v0.1.0 (2026-05-14)

### Bug Fixes

- Create .env from .env.example if it doesn't exist
  ([`a22e22b`](https://github.com/frankify-app/disambiguate/commit/a22e22b3b348507f5e8af35158a5c7ab6979dc3d))

- Use prek instead of pre-commit
  ([`c0171f0`](https://github.com/frankify-app/disambiguate/commit/c0171f0dd9b12eea09bc2404aed9afdccf0bb2f2))

### Features

- Implement Disambiguate v0.1
  ([`085123e`](https://github.com/frankify-app/disambiguate/commit/085123e57e516829309b58d5274548a4bd751161))


## v0.0.0 (2026-05-08)

- Initial Release
