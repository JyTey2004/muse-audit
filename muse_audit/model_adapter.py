"""Explicit extension seam, NOT a functioning Meta/Muse integration.

A future model may propose mappings or patches for human approval. Its output
must pass the same strict contracts and never becomes proof by itself. No API
key is read, no network call is made, no canned text is labeled model output.
"""
class ModelNotConfigured(RuntimeError):
    pass


def propose_requirements(*args, **kwargs):
    raise ModelNotConfigured('Live model integration is not configured or authorized in this prototype')
