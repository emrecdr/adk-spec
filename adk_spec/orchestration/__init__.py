"""Everything ADK: the settings, the model factory, the stages, the graph and one guarded run. This layer may import
`domain` and `workspace`."""

import os

# ADK records each request and answer in its trace spans unless told not to, and `adk web` sends spans wherever an
# OpenTelemetry endpoint is set. A request holds a repository's code: none of it goes into a span unless the person
# has said so themselves.
os.environ.setdefault("ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS", "false")
