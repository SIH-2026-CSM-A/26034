# app.contracts

**Owner:** @Abhiram-0910

The shared vocabulary: Pydantic models and enums that cross a module boundary — the
extracted-declaration shape, the rule-verdict shape, the evidence-bundle shape.

This is the bottom layer. It imports nothing from `app`, and no framework, database, or
I/O code belongs here — only types.

Changing a type here changes it for every module at once, so changes land through a PR
that names the modules affected.
