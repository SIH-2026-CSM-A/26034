# app.core

**Owner:** @Abhiram-0910

Infrastructure every module needs and none should re-implement: settings
(`pydantic-settings`, read from environment — see `bck/.env.example`), the SQLAlchemy
engine and session factory, logging setup, and shared exception types.

May import `app.contracts`. May not import `app.modules` or `app.pipeline`.

No business rules. If it knows what a Legal Metrology declaration is, it belongs in a
module, not here.
