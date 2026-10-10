# Strategies, contracts and results

Current implementation, inspected 2026-10-05. The views separate selection, implementations and data flow. Members show important responsibilities, not full Python signatures. Protocol realization uses structural typing, not required Python inheritance.

## Selection and contracts

```mermaid
classDiagram
    direction LR
    class DirectorySyncModel {
        +set_directories(dir1, dir2)
        +set_filters(options)
        +set_diff_mode(mode)
        +compare_directories() tuple
        +synchronize() dict
        +rollback_changes() list
        +stop_event
        -_dir1_snapshot
        -_dir2_snapshot
    }
    class StrategyRegistry {
        +register(name, strategy)
        +get(name)
        +get_default()
        -_strategies
        -_lock
    }
    class DirectoryScanner {
        <<Protocol>>
        +scan(directory, options) DirectorySnapshot
    }
    class HashProvider {
        <<Protocol>>
        +calculate_hash(path)
        +calculate_hashes(files, options) dict
    }
    class DiffStrategy {
        <<Protocol>>
        +compare(source, target, hash_provider) DiffResult
    }
    class SyncExecutor {
        <<Protocol>>
        +execute(diff, options) SyncResult
        +rollback(options) list
    }
    DirectorySyncModel --> StrategyRegistry : lazy lookup
    StrategyRegistry o-- DirectoryScanner
    StrategyRegistry o-- HashProvider
    StrategyRegistry o-- DiffStrategy
    StrategyRegistry o-- SyncExecutor
```

Four global registries hold shared instances; bootstrap registers them once under a lock. Defaults are scanner `default`, hash `cached`, executor `default`; the model selects diff mode by key. Model/AppSettings default to `two-phase`, while the repository settings file selects `strict`.

## Concrete implementations

```mermaid
classDiagram
    direction LR
    class DefaultDirectoryScanner
    class DefaultHashProvider
    class CachingHashProvider {
        -_base_provider
        -_cache
        -_lock
    }
    class FullHashDiffStrategy
    class TwoPhaseDiffStrategy
    class FastDiffStrategy
    class DefaultSyncExecutor {
        -_target_path
        -_backup_dir
        -_copied_files
        -_replaced_files
        -_created_dirs
        +execute(diff, options) SyncResult
        +rollback(options) list
    }
    DefaultDirectoryScanner ..|> DirectoryScanner
    DefaultHashProvider ..|> HashProvider
    CachingHashProvider ..|> HashProvider
    CachingHashProvider o-- HashProvider : wraps base provider
    FullHashDiffStrategy ..|> DiffStrategy
    TwoPhaseDiffStrategy ..|> DiffStrategy
    FastDiffStrategy ..|> DiffStrategy
    DefaultSyncExecutor ..|> SyncExecutor
```

The hash cache keys on `(path, size, mtime)` and wraps batch hashing. The executor journal belongs to its instance, not a separate operation object. Registry lookup does not isolate the executor journal between overlapping operations.

## Data between operations

```mermaid
flowchart TB
    Scanner["DirectoryScanner.scan"] --> Snapshot["DirectorySnapshot<br/>root, files, directories"]
    Metadata["FileMeta<br/>paths, size, mtime, optional hash"] --> Snapshot
    Snapshot --> Diff["DiffStrategy.compare<br/>source and target snapshots"]
    Hash["HashProvider"] --> Diff
    Diff --> Result["DiffResult<br/>DiffEntry by relative path, missing directories"]
    Metadata -. source and target metadata .-> Result
    Result --> Execute["SyncExecutor.execute"]
    Execute --> SyncResult["SyncResult<br/>counts, affected paths, errors"]
    Execute --> Stats["SyncStats / SyncItem<br/>callback updates"]
    SyncResult --> Adapter["to_dict for SyncWorkerThread"]
```

Sources: [contracts and models](../sync/interfaces.py), [coordinator](../sync/directory_sync_model.py), [implementations and defaults](../sync/strategies.py), [bootstrap](../sync/bootstrap.py).
