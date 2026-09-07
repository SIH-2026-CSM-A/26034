"""Shared analytics policy constants."""

# This uncalibrated privacy prior uses a prototype floor because singleton and
# pair cohorts can expose an individual scan or entity. It does not guarantee
# anonymity and is not claimed to be required by law or statistics; production
# policy must calibrate it against real deployment and privacy requirements.
K_ANONYMITY_MIN_COHORT = 3
