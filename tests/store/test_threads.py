"""F4 (stress test): the store and the service are safe to share between threads."""

import threading

from memledger.core.factory import build_service
from memledger.core.types import Claim, Labels, Session, SourceKind, WriteProposal
from memledger.store.sqlite import SQLiteStore


def _run(n, fn):
    errors: list[BaseException] = []

    def work(i):
        try:
            fn(i)
        except BaseException as e:  # noqa: BLE001 - collected and asserted below
            errors.append(e)

    ts = [threading.Thread(target=work, args=(i,)) for i in range(n)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    return errors


def test_store_concurrent_writes_and_reads():
    store = SQLiteStore()

    def fn(i):
        for j in range(20):
            cid = f"c{i}_{j}"
            store.add_claim(Claim(cid, f"fact {i} {j}", Labels(f"t{i % 3}")))
            store.set_status(cid, "active", "touch", trust=0.5)
            got = store.get_claim(cid)
            assert got is not None and got.id == cid and got.text == f"fact {i} {j}"

    assert _run(16, fn) == []
    assert len(store.list_claims()) == 16 * 20


def test_service_concurrent_writes_keep_chain_valid():
    for version in ("baseline", "provenance"):
        svc = build_service(version)

        def fn(i, svc=svc):
            s = Session(f"u{i}", "team_a", "researcher", 1)
            src = svc.ingest(f"Internal note {i}: the build server is host-{i}.", SourceKind.INTERNAL, s)
            res = svc.propose_write(WriteProposal(f"The build server is host-{i}.", [src.id], s))
            assert res.claim_ids or res.verdicts

        assert _run(16, fn) == [], version
        if version == "provenance":  # has the hash chain
            ids = [c.id for c in svc.store.list_claims()]
            assert ids and all(svc.verify_claim(c) for c in ids)
