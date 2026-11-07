# EPAC Templates

These templates are product assets. They are not deployed directly.

A later customer-generation step renders `global-settings.jsonc.j2` into the
customer implementation repository after the Level 1 deployment root scope has
been established.

The template deliberately requires an explicit `desired_state_strategy`.
No APF tooling may silently default a customer to EPAC `full` ownership.
