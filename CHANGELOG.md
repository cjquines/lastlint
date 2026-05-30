# Changelog

## [0.4.0](https://github.com/cjquines/lastlint/compare/v0.3.0...v0.4.0) (2026-05-30)


### ⚠ BREAKING CHANGES

* rename to lastlint

### Documentation

* **readme:** update docs ([cb1dd42](https://github.com/cjquines/lastlint/commit/cb1dd420bd302847824492329e13ff29e2eeb75d))


### Miscellaneous Chores

* rename to lastlint ([c46d75d](https://github.com/cjquines/lastlint/commit/c46d75d3b603ce36f9b7a02a4f4f29697fe11971))

## [0.3.0](https://github.com/cjquines/lastlint/compare/v0.2.0...v0.3.0) (2026-05-22)


### Features

* exempt URL and comment lines from E001 ([9e652fa](https://github.com/cjquines/lastlint/commit/9e652fa7f88ea4ea8c16ec986c2a54bc149265a2))
* friendlier standalone CLI output and glob support ([2ffba81](https://github.com/cjquines/lastlint/commit/2ffba812e94358c62bb3c28c0130d6bc1cbfeace))


### Bug Fixes

* don't flag operator names inside \operatorname{...} in E003 ([fa6d131](https://github.com/cjquines/lastlint/commit/fa6d131bcbb2ffb23301b431354312412d6cf08e))

## [0.2.0](https://github.com/cjquines/lastlint/compare/v0.1.0...v0.2.0) (2026-05-22)


### Features

* add --ignore flag to skip rules globally ([8ef61db](https://github.com/cjquines/lastlint/commit/8ef61db22dd4098eba834fa60294be7007c18265))
* add otis-latex-lint-fix pre-commit hook ([070c3fc](https://github.com/cjquines/lastlint/commit/070c3fc3713e6b9f80ecb4bdf84e9d29148bf6eb))
* ignore comments and post-\end{document} content ([44ee8c5](https://github.com/cjquines/lastlint/commit/44ee8c5cadc589413dc6d6d70c90bd89030142de))
* switch E013 to a denylist of non-indenting envs ([efed5d8](https://github.com/cjquines/lastlint/commit/efed5d88ad1423229aba0ae1d8d67e7f284d5d94))


### Bug Fixes

* **E002:** ignore `\"` umlaut accent, not a literal quote ([874c2fb](https://github.com/cjquines/lastlint/commit/874c2fb2801f2be67b81f34b4a996b1b7189c96e))
* **E013:** don't pad lines past the E001 length limit ([0d42e34](https://github.com/cjquines/lastlint/commit/0d42e3471ab756a5a14a6b05d47f1c3670ba4665))
* **E013:** drop theorem-like envs from the indent allowlist ([8bdd117](https://github.com/cjquines/lastlint/commit/8bdd117c73cde5cd9391dec9153f51f29fe5a275))
* exempt control words from E006 space-before-punct ([228629e](https://github.com/cjquines/lastlint/commit/228629eb3627583378dbe962d58a63f78eaa5db7))
* only flag E017 colon when math span has a mapping arrow ([06e6a5d](https://github.com/cjquines/lastlint/commit/06e6a5d60c9f4a03749d28604b1902a172d1b14f))
* pick \dots variant from context in E004 fixer ([669c152](https://github.com/cjquines/lastlint/commit/669c152b2a9ea2efd4b937b8d754aff9162cf15f))
* run --fix to a fixpoint instead of a single pass ([c9ec94d](https://github.com/cjquines/lastlint/commit/c9ec94d4c747eef1b2598d2b2a2970920a5d1c05))


### Documentation

* add CLAUDE.md ([ce6de1f](https://github.com/cjquines/lastlint/commit/ce6de1f3744774e26deb288e5d90c1f600dbaf0a))
* **readme:** recommend fixer by default ([89c17f1](https://github.com/cjquines/lastlint/commit/89c17f1460fcc7dfb8f41bbf5c4494749ef8ba74))

## 0.1.0 (2026-05-22)


### Features

* add --fix flag with auto-fixer for E013 ([f807fbf](https://github.com/cjquines/lastlint/commit/f807fbf19bb23f8dcd2f5cad0d1e72df1f405486))
* add auto-fixers for E002-E010 and E017 ([3e5eb6d](https://github.com/cjquines/lastlint/commit/3e5eb6d4686300ab4f61f76fea4020edb2035866))
* add E014 (no trailing whitespace) rule and fixer ([31eb0ec](https://github.com/cjquines/lastlint/commit/31eb0ece8f1790d686d4a4aea6d8547d99867fd7))
* extend E004 (literal ...) and E009 (bad math operators) ([440d8c5](https://github.com/cjquines/lastlint/commit/440d8c591dd16cc6f7303fc0b0afad9e5091a603))
* initial linter for Evan's LaTeX style guide ([e877e60](https://github.com/cjquines/lastlint/commit/e877e609638fdc9678df3071c20a7fe99e1807f6))
