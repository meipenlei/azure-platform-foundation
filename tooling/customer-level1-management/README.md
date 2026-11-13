# APF Customer Level 1 Management Platform

Generates the Terraform root and protected GitHub workflows for the central
Level 1 management substrate.

Inputs:

- customer/foundation/platform configuration;
- Level 0 backend snapshot;
- Level 1 management-group snapshot.

Outputs include a deterministic
`.foundation/level1-management-platform.yaml` file. Later Policy-as-Code
generators consume the Log Analytics workspace and monitoring UAMI resource IDs
from that file.

Dry-run is the default. Use `--apply` only to write generated repository files.
The generator itself never changes Azure.
