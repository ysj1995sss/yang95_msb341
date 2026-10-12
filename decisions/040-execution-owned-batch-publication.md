# 040: Stage privately; publish only for the current execution

Date: 2026-10-11. Spec 018, approved targeted ownership-boundary change. Local branch only.

## Choice

Both frontend hooks compute into private execution/job/attempt staging. The shared runner
checks batch ID, execution token, running job and active/draining ownership under the same
cross-process lock used for recovery, then publishes immutable PDF bytes and the atomic review
replacement. A returned False from review storage is a resumable failure, not done.
Lost ownership publishes nothing and does not update current outcomes or finish callbacks.
Stop retains the owned running job until it drains; it is distinct from recovery/token loss.

API callbacks run outside the runner lock, acquire the API run lock first, then guard their
write with the execution claim. They also cannot finish a newer single run. A recovered
batch's stale API status cannot prevent Continue. Both apps preserve frozen source metadata.

The former age-expiring exclusive-create lock could be stolen during a slow publication.
Standard-library `msvcrt`/`fcntl` OS locks now release on process exit, with a persistent lock
file. **Restart both frontends on adoption; old executable versions using exclusive-create
locking must not share the folder with this version.** Existing batch IDs/options and
format-2 review files stay compatible. No queue, dependency or model-call-wide lock was added.

Only validated, old inactive private attempts are cleaned. Current execution and live workers
are retained; symlinks/junctions/escapes are refused. Windows staging supports long absolute
paths. Interrupted publication leaves the old current review usable; orphan immutable bytes
do not become current.

Rejected: checking only after an unconditional hook save; checking then writing unlocked;
holding a lock for model/conversion work; a distributed queue/refactor. Arbitrary legacy
external callbacks that mutate storage before returning are outside this contract; the actual
deployed hooks use the staged path.

## Evidence / limits

Real pipeline thread races, actual API/Streamlit hook races, a Windows-spawn two-process race,
current public PDF download, failure/interruption controls, Stop/drain, delayed callbacks and
a real Windows junction test all passed. Read
`discovery/experiments/2026-10-11-specs-016-018-fixes.md` for exact counts.

The live real-model batch drained its first passing PDF safely; Continue's second model call
returned no answer and remains resumable. It is not a completed live batch. New live Streamlit
and real-model restart checks, POSIX CI and independent final sign-off remain open. Batch
restart detection still has the documented PID-reuse/three-minute heartbeat fallback.
