"""Security-scoped persistence helpers for AutoTecPro AI.

These functions intentionally accept the Supabase client as a dependency so the
repository layer is testable without Streamlit and every conversation mutation
is scoped to its owning username.
"""
from __future__ import annotations


def conversation_owned_by_user(db, username, conversation_id) -> bool:
    username = str(username or '').strip()
    conversation_id = str(conversation_id or '').strip()
    if not username or not conversation_id:
        return False
    result = (
        db.table('conversations')
        .select('id')
        .eq('id', conversation_id)
        .eq('username', username)
        .limit(1)
        .execute()
    )
    return bool(result.data)


def load_messages_for_user(db, username, conversation_id, limit=2000):
    if not conversation_owned_by_user(db, username, conversation_id):
        return []
    result = (
        db.table('messages')
        .select('role,content,created_at')
        .eq('conversation_id', conversation_id)
        .order('created_at', desc=True)
        .limit(int(limit))
        .execute()
    )
    rows = list(reversed(result.data or []))
    return [
        {'role': row.get('role', 'assistant'), 'content': row.get('content', '')}
        for row in rows
    ]


def update_owned_conversation(db, username, conversation_id, payload, *, ownership_verified=False):
    # Fail closed by default. Callers may skip the duplicate DB ownership lookup
    # only after an application-level ownership gate has already succeeded.
    if not ownership_verified and not conversation_owned_by_user(db, username, conversation_id):
        raise PermissionError('Conversation is unavailable.')
    return (
        db.table('conversations')
        .update(dict(payload or {}))
        .eq('id', conversation_id)
        .eq('username', username)
        .execute()
    )


def insert_message_for_user(db, username, conversation_id, payload, *, ownership_verified=False):
    # Fail closed by default; verified=True is an explicit performance fast path.
    if not ownership_verified and not conversation_owned_by_user(db, username, conversation_id):
        raise PermissionError('Conversation is unavailable.')
    row = dict(payload or {})
    row['conversation_id'] = conversation_id
    return db.table('messages').insert(row).execute()


def delete_owned_conversation(db, username, conversation_id, *, ownership_verified=False):
    """Delete a conversation with best-effort rollback if parent deletion fails.

    Supabase/PostgREST cannot make two client-side table requests atomic. We first
    snapshot the child rows after ownership verification. If the parent deletion
    fails after child deletion, the exact child rows are reinserted before the
    original exception is raised. This removes the previously reproducible
    data-loss failure mode without requiring a schema migration.
    """
    if not ownership_verified and not conversation_owned_by_user(db, username, conversation_id):
        raise PermissionError('Conversation is unavailable.')

    snapshot_result = (
        db.table('messages').select('*')
        .eq('conversation_id', conversation_id).execute()
    )
    snapshot = [dict(row) for row in (snapshot_result.data or []) if isinstance(row, dict)]

    db.table('messages').delete().eq('conversation_id', conversation_id).execute()
    try:
        return (
            db.table('conversations').delete()
            .eq('id', conversation_id)
            .eq('username', username)
            .execute()
        )
    except Exception:
        if snapshot:
            try:
                db.table('messages').insert(snapshot).execute()
            except Exception as rollback_error:
                raise RuntimeError(
                    'Conversation deletion failed and message rollback also failed.'
                ) from rollback_error
        raise
