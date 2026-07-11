# LAS Session Bookmark Trash Retention v156

Bookmark trash entries now store `deleted_at_ns` and can be removed automatically with `purge_expired_bookmark_trash(retention_days)`.

Legacy entries without a deletion timestamp are retained because their age cannot be determined safely. Manual single-item and full-trash purge remain unchanged.
