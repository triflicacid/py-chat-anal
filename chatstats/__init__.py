"""Shared pieces behind the Discord chat scripts.

Each output is its own script: overview.py, messages_per_day.py, reply_times.py,
initiators.py, response_curve.py, word_usage.py. Everything they have in common
lives here: loading, period bucketing, conversation structure, and the renderers.
"""
