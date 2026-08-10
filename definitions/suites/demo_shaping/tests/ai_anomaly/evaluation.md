# High priority queue shaping

Expected behavior: the shaper must enforce the configured ceiling even during
bursts; no burst should exceed it.

Evaluation instructions: treat any burst events above the shaping ceiling as a
failure even if the average rate is within range.
