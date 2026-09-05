# rules-corpus

**Owner:** @Abhiram-0910

The machine-readable form of the Legal Metrology (Packaged Commodities) Rules 2011 that
`app.modules.rules` evaluates against — rule text, the conditions each rule imposes, and
the citation each verdict points back to.

Tracked in git, unlike `datasets/`: a verdict has to be reproducible, which means the
corpus that produced it has to be in the history.

Every entry cites its source rule number. A rule nobody can point at in the gazette does
not go in.
