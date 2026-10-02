"""Exercise the ledger's compare-and-swap conflict path without GitHub writes."""
import base64
from concurrent.futures import ThreadPoolExecutor
import json
from subprocess import CompletedProcess
import threading
import unittest
from unittest.mock import patch

import review_identity


class LedgerTests(unittest.TestCase):
    def test_concurrent_reservations_retry_without_reusing_an_ordinal(self):
        lock = threading.Lock()
        barrier = threading.Barrier(2)
        ledger = []
        generation = 0
        first_reads = 0
        conflicts = 0

        def request(command, **kwargs):
            nonlocal generation, first_reads, conflicts
            if "PUT" not in command:
                with lock:
                    if not ledger:
                        response = CompletedProcess(command, 1, "", "HTTP 404")
                    else:
                        response = CompletedProcess(command, 0, json.dumps({
                            "sha": str(generation), "content": base64.b64encode(
                                json.dumps(ledger).encode()).decode()}), "")
                    first_reads += 1
                    wait = first_reads <= 2
                if wait:
                    barrier.wait(timeout=5)
                return response
            body = json.loads(kwargs["input"])
            with lock:
                expected = str(generation) if generation else None
                if body.get("sha") != expected:
                    conflicts += 1
                    return CompletedProcess(command, 1, "", "HTTP 409")
                ledger[:] = json.loads(base64.b64decode(body["content"]))
                generation += 1
                return CompletedProcess(command, 0, "{}", "")

        with patch.object(review_identity.subprocess, "run", side_effect=request), \
             patch.object(review_identity, "git", return_value="a" * 40):
            with ThreadPoolExecutor(max_workers=2) as pool:
                allocated = list(pool.map(lambda _: review_identity.reserve("owner/repo", 2), range(2)))
            third = review_identity.reserve("owner/repo", 2)
        self.assertEqual(sorted(allocated), [1, 2])
        self.assertEqual(third, 3)
        self.assertGreaterEqual(conflicts, 1)
        self.assertEqual([entry["ordinal"] for entry in ledger], [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
