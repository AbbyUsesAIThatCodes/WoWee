# Party Frame Regression

## Automated Interface Test

Build `framexml_run` with `-DWOWEE_BUILD_FRAMEXML_RUN=ON`, then run:

```text
python tools/test_party_frames.py --runner <build>/bin/framexml_run.exe --data <extracted-WotLK-directory> --output <results-directory> --manifest <metadata>/build-manifest.json
```

The data directory must contain the legally obtained, locally extracted
`interface/FrameXML/PartyMemberFrame.lua`. Blizzard files are not added to this
fork or uploaded. This uses real production Lua bindings, FrameXML and widget
tree, with synthetic roster/entity data and fresh config/logs. It runs with
fallback API globals both enabled and disabled. It never opens a socket or logs
in. Assertions cover membership, visible frames, name labels, health bars,
portrait unit registration, offline/out-of-range members, nearby entities,
empty slots, roster compaction, a new member, disbanding and no game handler.
The optional manifest preflight rejects an old runner while a rebuild is still
compiling or linking.

To register the same command with CTest, configure
`-DWOWEE_FRAMEXML_TEST_DATA=<extracted-WotLK-directory>` and run
`ctest --test-dir <build> -R party_frames --output-on-failure`.

The fixture updates the roster and dispatches the real roster events. Packet
decoding is covered separately by `test_group_list_parse`; this is not a
network protocol or server integration test. Real GPU portrait pixels are not
asserted by the headless test.

## Automated Windows Smoke Test

First prepare a separate data view. The client's startup synchronizes its own
expansion tables into the selected Data directory, so pointing a review client
directly at the original extraction could change it:

```text
python tools/prepare_review_data.py --source <original-Data-root> --destination <new-private-Data-root>
```

The script copies metadata and FrameXML and references the existing extracted
models/textures through a private manifest. It does not copy accounts, saved
credentials or realm configuration. Keep this local data view out of uploads.

```powershell
pwsh -NoProfile -File tools/smoke_review.ps1 -Executable <review>/wowee.exe -Data <private-Data-root> -Output <new-smoke-directory>
```

The script refuses to run when any WoWee process exists. It uses fresh config,
the client's existing `WOWEE_SCREENSHOT` hook, and a 60-second timeout. It
captures the login screen and exits without input or credentials. Inspect the
PNG for legibility and the complete build ID. This checks startup and login
rendering, not party portraits in a world. Reusing this artifact preserves its
build identity.

## Manual In-Game QA Still Needed

When the user chooses to try the separate review build: join a party, verify
four frames and actual portraits, inspect names and changing health, exercise
join/leave and out-of-range/offline members, and check Lua errors. Do not use
automation to change live accounts, characters or realm state.

## Traced Dependencies and Scope

`SMSG_GROUP_LIST` -> `SocialHandler::handleGroupList` -> `PARTY_MEMBERS_CHANGED`
-> `PartyMemberFrame_UpdateMember` -> `GetPartyMember` -> `Show/Hide` and
`UnitFrame_Update`. Unit names/health already use roster fallbacks when entities
are absent. `SetPortraitTexture` registers party1-party4 in `WidgetTree`;
`Application` maps the same roster order to `partyPortraits_` and supplies the
GPU textures when appearance data is available.

The confirmed visibility blocker is the always-false `GetPartyMember` stub.
The existing party-token and portrait mapping both use the first four other
roster members, while `GetNumPartyMembers` filters the local raid subgroup.
That broader raid-subgroup inconsistency is deferred; this focused party
repair keeps membership and displayed unit data in the same existing order.
