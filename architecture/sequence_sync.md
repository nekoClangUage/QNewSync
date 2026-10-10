# Compare, synchronize and cancel

Current implementation, inspected 2026-10-05. The phases are separated so each view can be read without a project-wide set of lifelines. These diagrams describe existing ordering, not atomic cancellation or automatic rollback on errors.

## Selection and comparison

```mermaid
sequenceDiagram
    actor User
    participant UI as MainWindow
    participant Worker as CompareWorkerThread
    participant Model as DirectorySyncModel
    participant Scanner as Directory scanner
    participant Diff as Selected diff strategy
    participant Hash as CachingHashProvider
    User->>UI: Select source and target
    UI->>Model: set_directories()
    Model->>Model: Resolve paths, validate nesting, invalidate changed paths
    UI->>Worker: start()
    Worker->>Model: Set progress callback, compare_directories()
    Note over Model: Lazy lookup from global registries
    opt Snapshots not cached
        Model->>Scanner: scan(source), scan(target)
        Scanner->>Scanner: Recursive scandir and metadata
        Scanner-->>Model: DirectorySnapshots
    end
    Model->>Model: Apply source regex rules
    Model->>Diff: compare(source, target, hash provider)
    opt Hashes required by diff mode
        Diff->>Hash: calculate_hashes()
        Hash->>Hash: Cache lookup, process pool for misses
        Hash-->>Diff: Path to hash mapping
    end
    Diff-->>Model: DiffResult
    Model-->>Worker: Tuple for UI highlights
    Worker->>Model: Restore progress callback on success
    Worker-->>UI: finished(result) signal
    UI->>UI: Update highlights
```

Scanner reads the filesystem; cache misses use process workers for file reads and MD5. These calls are summarized inside their responsible participants. Compare errors currently become an empty result; callback restoration is not in `finally`.

## Synchronization

```mermaid
sequenceDiagram
    actor User
    participant UI as MainWindow
    participant Worker as SyncWorkerThread
    participant Model as DirectorySyncModel
    participant Exec as DefaultSyncExecutor
    participant Pool as Copy process workers
    participant FS as Filesystem
    User->>UI: Synchronize
    UI->>Worker: start()
    Worker->>Model: Set stats callback, synchronize()
    Model->>Model: reset_stop(), clear snapshot caches
    Model->>FS: Ensure target root exists
    Model->>Model: Fresh source/target scan, source rules, diff
    Note over Model: Uses scanner and diff from comparison view
    Note over Model,Exec: No changes or early stop return before execute
    Model->>Model: Save planned paths and existing target directories
    opt Replacements planned
        Model->>FS: Create temporary backup directory
    end
    Model->>Exec: execute(diff, options, callbacks)
    opt copy_empty_dirs enabled
        Exec->>FS: Create missing directories first
    end
    Exec->>FS: Reserve temporary files in operation-owned directories
    Exec->>Pool: Manager event, imap_unordered(named partial tasks)
    loop Each file task
        Pool->>Pool: Check process stop event
        Pool->>FS: copy2(source, temporary file)
        Pool->>Pool: Check process stop event
        opt Replacement
            Pool->>FS: copy2(old target, temporary backup)
            Pool->>Pool: Check process stop event
            Pool->>FS: os.replace(temporary backup, backup)
        end
        Pool->>Pool: Check process stop event again
        Pool->>FS: os.replace(temporary file, target)
        Pool->>FS: Unlink remaining temporary files on normal exit
        Pool-->>Exec: File result
        Exec-->>Worker: Stats callback, same mutable object
        Worker-->>UI: stats_updated signal
    end
    Exec->>Pool: terminate(), join()
    Exec->>FS: Remove this operation's temporary directories after worker exit
    Exec-->>Model: SyncResult
    Model-->>Worker: Result dict
    Worker-->>UI: finished(result) signal
    Worker->>Model: Clear stats callback in finally
    UI->>Worker: Wait for worker exit
    UI->>UI: Handle result, or start Cancel worker if requested
```

Model rebuilds filesystem snapshots for sync but retains the hash cache. The copy worker installs fully prepared files; backup and target temporary files live on their respective destination filesystems. The result has no dedicated stopped status; UI handling depends on how and when stop was observed. Error/stop paths skip the pending installation.

## Stop and Cancel during synchronization

```mermaid
sequenceDiagram
    actor User
    participant UI as MainWindow
    participant Sync as SyncWorkerThread
    participant Cancel as CancelWorkerThread
    participant Model as DirectorySyncModel
    participant Exec as DefaultSyncExecutor
    participant FS as Filesystem
    Note over Sync,Exec: Synchronization already in progress
    User->>UI: Stop or Cancel
    UI->>Model: stop()
    Note over UI: Cancel also sets cancel_requested
    Exec->>Exec: Observe stop on result, set process event, terminate and join pool
    Exec->>FS: Remove registered temporary directories after worker exit
    Exec-->>Model: SyncResult
    Model-->>Sync: Result dict
    Sync-->>UI: finished(result) signal
    Sync->>Model: Clear stats callback in finally
    UI->>Sync: Wait for worker exit
    alt cancel_requested is true
        UI->>Cancel: start()
        Cancel->>Model: Set progress callback, reset_stop()
        Cancel->>Model: rollback_changes()
        Model->>Exec: rollback()
        Exec->>FS: Delete acknowledged and planned new files
        Exec->>FS: Restore replaced files from backup
        Exec->>FS: Remove backup, clean created empty directories
        Exec-->>Model: Errors list
        Model->>FS: Remove new empty target directories
        Model->>Model: Reset tracking
        Model-->>Cancel: Errors list
        Cancel->>Model: Restore progress callback on success
        Cancel-->>UI: finished(errors) signal
    else Stop without Cancel
        UI->>UI: Handle returned result without rollback
    end
```

This view shows stop observed during executor result consumption. Earlier stop may produce a model error result. Cancel is handled only while sync is running; a normal error without `cancel_requested` does not automatically start rollback.

Sources: [MainWindow handlers](../ui/main_window.py), [workers](../ui/workers.py), [model](../sync/directory_sync_model.py), [executor and copy workers](../sync/strategies.py).

`finished(result)` precedes full thread exit. Cancellation can interrupt temporary writes; complete installations may be missing from the acknowledged journal. Backup removal can still occur after restore errors. These are current limitations, not requirements to preserve.
