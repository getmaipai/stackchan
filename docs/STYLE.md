# Writing style

1. Write for the robot's owner. Short sentences, plain words, concrete numbers and names.
2. User docs read at grade 6. Developer docs may use technical terms, defined once.
3. Until v1.0.0 ships, user docs describe the finished product and the README carries a Draft notice. Remove the notice at release. Developer docs say what is confirmed on a unit.
4. Every error message says what went wrong and what to do next, in terms the person sees.
5. No em dashes. Use a comma, a period or a colon.
6. No filler vocabulary. The hygiene check lists the banned words.
7. No exclamation points. No rhetorical questions as transitions.
8. Do not mention, compare to or credit other projects. Required notices live only in LICENSE, NOTICE and THIRD-PARTY.md.
   The two upstream firmware bases are named only in `docs/dev/build-from-source.md`.
9. Examples use 192.0.2.x addresses, example.com and persona names. Never real names, addresses or hostnames.
10. Say "snapshots" for camera images, because the resolution is low.
11. MaiPai Home appears only as an optional brain.
12. Docs change in the same commit as the behaviour they describe.
13. Run `bash scripts/check.sh` before landing. It must print "hygiene: ok".
