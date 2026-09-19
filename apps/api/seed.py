"""Legacy entry point retained to prevent unsafe global seeding.

Account-isolated data must be created by an authenticated request or assigned
offline with the graph-wide migration runbook. A shared password admin and
ownerless sample records would violate both guarantees.
"""


def seed_db() -> None:
    raise RuntimeError(
        "Global seeding is disabled. Bootstrap the first Google admin with "
        "GOOGLE_ADMIN_EMAIL and use the authenticated application to create data."
    )


if __name__ == "__main__":
    seed_db()
