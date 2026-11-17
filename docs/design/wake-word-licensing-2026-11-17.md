# Wake word models and redistribution: position after review (2026-11-17)

Placement: research notes for a lawyer, not legal advice. Sources: the speech library's license file in the build's component, the model collection notices, and an outside review. Facts below are what the files say; the open questions are marked.

## What ships and where it comes from
The stock robot enables one wake word, "Hi, Stack Chan" (`wn9l_histackchan_tts3`, about 296 KB), and our patch 049 adds the English stop word model (`mn5q8_en`). Both come from Espressif's speech library (esp-sr 2.4.7), which the build downloads from the component registry. They are not in this repository.

## Position after review
| Point | Position |
|---|---|
| A public repo does not settle model licensing | Agreed. Code, closed libraries and trained models can have different terms. |
| The library license permits redistribution and sale | Yes for Espressif products, if the notice is kept. The published text is MIT with the clause "for use on all ESPRESSIF SYSTEMS products". Our unit is an Espressif chip. |
| No separate model license means permission cannot be shown | Too strong, withdrawn. A package license can cover files with no header. The open question is whether it covers the exact downloaded model package and whether any exception applies. |
| Espressif names only two free phrases | Misleading, withdrawn. Their page says "such as", giving examples. It does not say whether "Hi, Stack Chan" is cleared. |
| A build recipe is safe | Overconfident, withdrawn. It avoids our redistributing binaries; it does not remove commercial-use or AGPL questions for whoever builds and ships. |
| AGPL needs checking | Agreed, and it may be the bigger issue. Espressif's permission does not settle obligations our own license puts on a combined work. |
| A made-up phrase avoids every trademark issue | Withdrawn as an absolute claim. A coined phrase can still collide with a mark, and synthetic training voices have their own terms. |

## The public repo changes the question
Publishing the SOURCE and the build recipe is the low-risk step: the repo holds our patches, scripts and docs, and no model files and no closed libraries (the build downloads them). The risk is narrower: publishing PREBUILT images, because a binary bundles the closed libraries and models with our code.
Checks before the repo goes public: no model or library binary is committed (the boundary check enforces this; add a test that fails on any `.espdl`, `.bin` model or `.a` library), THIRD-PARTY and NOTICE list the speech library (done) and every downloaded model with its terms, and the recipe tells the builder to accept the vendor terms at download.

## The AGPL question, concretely
1. Which parts are AGPL. Today the whole repository is AGPL-3.0 (LICENSE). The firmware patches modify an MIT base; MIT code can be combined into an AGPL work, so the source repo is consistent.
2. Where it bites: a prebuilt firmware image is one combined executable (our patches, the MIT base, and Espressif's closed libraries). Whoever distributes that binary under AGPL has to give the corresponding source of the whole work, and the closed libraries cannot be offered under AGPL. Whether the vendor's license counts as a "system library" style exception or needs a written exception is a lawyer's question.
3. The host program is a separate program that talks to the unit over a network protocol, so the AGPL analysis for it is independent of the firmware.
4. A way to avoid the question: license the firmware patches under the base's own permissive license (MIT) and keep the host under AGPL. The firmware is then an MIT work linked with a vendor library whose terms permit that on Espressif chips, which is how the base project ships. This is a decision for the owner and a lawyer; nothing is changed here.

## The better wake word basis: microWakeWord models
The model collection's own notice says its Apache-2.0 license covers the trained weights and the manifests, and separately disclaims trademark rights. That is a clear basis for redistribution, including commercial use, subject to the license conditions (attribution, notice). The models are about 52 to 60 KB each. Open items: whether the keyword engine runs beside our audio front end on the unit, accuracy and false accepts, and the trademark check of each phrase (some phrases are other companies' product names). A made-up phrase trained locally avoids a known brand but still needs a name search and a look at the terms of any synthetic voices used for training.

## Recommendation
1. Publish the source and the recipe; add the no-model-binaries test.
2. Do not publish prebuilt images until a lawyer answers the questions below (or Espressif confirms in writing).
3. Keep "Hi, Stack Chan" as the default for private builds; plan a coined, searched phrase for the public product, with the Apache-licensed keyword engine as the alternate.
4. Put the firmware-license choice (permissive firmware, AGPL host) to the owner and the lawyer.

## Questions for a lawyer
1. Does the library license ("for use on all ESPRESSIF SYSTEMS products") cover the exact model package the build downloads, and does the clause count as an extra restriction for an AGPL work?
2. Can we publish a prebuilt image that bundles the closed libraries and models, under what notice?
3. Is the firmware best licensed permissively while the host stays AGPL?
4. What does a build recipe that downloads the library leave on us as the distributor?
5. Does the stock phrase "Hi, Stack Chan" need the hardware maker's consent in a public product?
6. What clearance does a coined phrase need?
