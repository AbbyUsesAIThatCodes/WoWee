# Build Identity

The fork's authoritative release record is `release.json`: **3.1.41 First
Campfire**, an unfinished development repair based on upstream v3.1.41.
First Campfire retains the name of the existing setup. This work does not
change save formats, server protocols, or the installed release. A subsequent
release number will be agreed when this review is accepted.

## Review Builds

Reserve before each artifact-producing invocation, including a failed retry:

```text
python tools/review_identity.py --pr <number> --out <new-metadata-directory>
cmake -S . -B <build-directory> -G Ninja -DCMAKE_BUILD_TYPE=Release -DWOWEE_REVIEW_METADATA=<absolute-metadata-directory>/identity.cmake
cmake --build <build-directory> --parallel 4
```

The allocator uses GitHub's contents API with the previous blob SHA on the
fork's `build-ledger` branch. Concurrent updates conflict and retry; ordinals
are PR-local, durable across checkouts, and never reused. A reserved attempt
can fail; gaps do not imply missing successful artifacts. Retest or copy an
existing artifact without calling the allocator. Record the attempt's result
alongside its immutable manifest. Never reuse a manifest for a rebuild.

The identifier includes version, codename, PR, ordinal, one captured UTC time,
12-character source revision, dirty marker/fingerprint when applicable, and
target. The manifest retains the full SHA and input fingerprint. Deliver the
manifest, report, and logs within a directory or archive named with the full
identifier; keep `wowee.exe` stable inside it. Do not commit generated metadata.

## Location Inventory

| Surface | Source | Status |
|---|---|---|
| Release version and codename | `release.json` | Implemented for fork review builds |
| Durable ordinal | `build-ledger` branch, `build-ledger/pr-N.json` | CAS reservation |
| Manifest and metadata | `tools/review_identity.py` | One immutable manifest per attempt |
| Configure/build console | `cmake/GitVersion.cmake`, `wowee_version` | Prints complete review ID |
| Compiled identity | `include/core/version.hpp.in` | Generated from same metadata |
| Login footer | `src/ui/auth_screen.cpp` | Wrapped full ID; click to copy |
| Settings version | `src/ui/settings_panel.cpp` | Reads same generated string |
| Output and validation report | Versioned outer review directory | Packaging/handoff verification |
| Existing upstream local/CI/IDE entrypoints | `build.*`, `.github/workflows/*` | Unchanged; full identity only when review metadata is explicitly passed |
| Live deployment | Original v3.1.39 installation | Preserved; no deployment from this work |

This is a focused review-build path, not a complete retrofit of upstream's
release workflows. Graphical footer verification and actual in-game party QA
must be reported separately from headless assertions.
