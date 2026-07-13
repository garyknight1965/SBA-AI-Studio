from sba_resolve.capture_time.parsers.registry import ParserRegistry


class CaptureTimeResolver:
    """
    Central capture time resolver.

    Automatically discovers every installed parser.
    """

    def __init__(self):

        registry = ParserRegistry()

        self._parsers = registry.parsers

    def resolve(self, metadata):

        best = None

        for parser in self._parsers:

            if not parser.supports(metadata):
                continue

            candidate = parser.parse(metadata)

            if candidate is None:
                continue

            if best is None:
                best = candidate
                continue

            if candidate.confidence > best.confidence:
                best = candidate
                continue

            if (
                candidate.confidence == best.confidence
                and candidate.timestamp < best.timestamp
            ):
                best = candidate

        return best