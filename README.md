# PAPER AI

**Plan with AI. Learn on paper. Return with evidence.**

PAPER AI turns an AI teaching plan into a complete paper learning package. A teacher supplies a topic, background and goal; AI prepares the lesson, question groups, hints, answers and offline next steps. Learners work on paper, then the teacher scans and confirms the records for the next learning round.

The formal application supports English and Chinese. It generates topic-based materials and imports previously generated learning packages. It does not offer a preset question bank or a rules-based generation mode.

## Start on a computer

Use Python 3.10 or later. No Python packages are required for the application.

```sh
python app/launch.py
```

Windows: double-click `app/start-paper-ai.bat`. macOS/Linux: run `sh app/start-paper-ai.sh`.

For new generation, configure a provider, model and API key. For existing materials, create a learner and choose **Import learning package**; review the draft, approve it and print. Imported materials work without an AI connection. Only AI generation and AI summaries need the provider connection.

## Mobile applications

Android and iOS embed the local Python service and the same interface. A phone runs its own workspace; it does not depend on a computer or a hosted website. File selection, saving and printing use native platform controls.

Builds and screenshots are produced by [formal release checks](https://github.com/keller-52/UNUAI/actions/workflows/release-checks.yml). Android output is an installable APK. iOS output includes an unsigned device IPA, a simulator app and an Xcode project; installing on an iPhone requires your Apple signing identity and provisioning profile. See [mobile build and installation](docs/current/mobile_build.md).

The [2026-10-01 verified build](https://github.com/keller-52/UNUAI/actions/runs/36822787600) passed all 62 Python tests, browser/scanner checks and both native startup checks. Download its Android or iOS artifact, then extract the APK, IPA or project. [Validation and file checksums](docs/current/validation.md) record the exact build and remaining physical-device checks.

## Documentation

Use the [document index](docs/README.md) for the project overview, current operation and acceptance requirements, technical contracts, mobile delivery and archived development records. The archive records historical decisions and results; current instructions take precedence.

## Verification

```sh
python -m unittest discover -s app/tests -p 'test_*.py' -v
```

Browser and scanner tests use test-only `playwright` and `@napi-rs/canvas`. [The workflow](.github/workflows/release-checks.yml) runs package/API tests, actual OMR image tests, bilingual responsive layouts, A4 PDF generation and native mobile startup checks. Mocked model responses are test fixtures; they are not application generation options.
