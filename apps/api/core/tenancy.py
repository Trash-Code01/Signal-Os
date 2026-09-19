"""Every ORM read, aggregate, bulk write and insert is account-scoped."""
from sqlalchemy import event, inspect, text
from sqlalchemy.orm import with_loader_criteria
from .database import SessionLocal, Base
from .models import OwnedRecord, User

@event.listens_for(SessionLocal, "do_orm_execute")
def scope_statement(state):
    if state.session.info.get("system_access"):
        return
    owner_id = state.session.info.get("owner_id", -1)
    if state.is_select or state.is_update or state.is_delete:
        state.statement = state.statement.options(with_loader_criteria(
            OwnedRecord, lambda model: model.owner_id == owner_id, include_aliases=True
        ))

@event.listens_for(SessionLocal, "before_flush")
def stamp_ownership(session, flush_context, instances):
    owner_id = session.info.get("owner_id")
    for obj in session.new | session.dirty | session.deleted:
        if not isinstance(obj, OwnedRecord):
            continue
        if owner_id is None:
            raise ValueError("An account is required to write business data")
        if obj in session.new and obj.owner_id is None:
            obj.owner_id = owner_id
        if obj.owner_id != owner_id:
            raise ValueError("Cross-account writes are forbidden")
        history = inspect(obj).attrs.owner_id.history
        if obj not in session.new and history.has_changes():
            raise ValueError("Ownership cannot be changed through the app")


def load_owned_job(db, model, record_id):
    """Trusted worker/webhook entry only, never a request-supplied owner ID."""
    db.info["system_access"] = True
    try:
        record = db.query(model).filter(model.id == record_id).first()
    finally:
        db.info.pop("system_access", None)
    if not record or record.owner_id is None:
        return None
    owner = db.get(User, record.owner_id)
    if not owner or not owner.is_active:
        return None
    db.info["owner_id"] = record.owner_id
    return record


def migrate_ownership(engine):
    existing = set(inspect(engine).get_table_names())
    with engine.begin() as conn:
        for mapper in Base.registry.mappers:
            if not issubclass(mapper.class_, OwnedRecord):
                continue
            table = mapper.local_table.name
            if table not in existing:
                continue
            columns = {c["name"] for c in inspect(engine).get_columns(table)}
            if "owner_id" not in columns:
                conn.execute(text(f'ALTER TABLE "{table}" ADD COLUMN owner_id INTEGER REFERENCES users(id)'))
            conn.execute(text(f'CREATE INDEX IF NOT EXISTS "ix_{table}_owner_id" ON "{table}" (owner_id)'))
    # Legacy rows remain unassigned and invisible until explicitly assigned offline.
