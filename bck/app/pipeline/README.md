# app.pipeline

**Owner:** @Abhiram-0910

The only place that composes modules. An image comes in; vision, extraction,
measurement, tamper and rules run in order; evidence assembles the result.

This is the top layer — it may import everything below it, and nothing may import it.
That asymmetry is deliberate: it means a module can be read, tested, and reviewed
without knowing where it sits in the run.
