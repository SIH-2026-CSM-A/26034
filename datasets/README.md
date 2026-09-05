# datasets

**Owner:** @Abhiram-0910

Local-only image and label data for development and evaluation. Contents are
git-ignored; only this README and `.gitkeep` are tracked.

Nothing here is a build input. If a dataset is needed to run something, the code reads
its path from the environment — it does not assume a file exists at a fixed path in the
repo. Keep the acquisition steps for a dataset in this file as they are established, so
a new machine can be brought up without asking someone.
