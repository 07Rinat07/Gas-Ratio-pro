# Next Step

Active module: Hydrocarbon Interval Engine.

Completed in the latest step:

- expanded interval schema to v4;
- added directional `gas_oil` and `oil_gas` classifications;
- added `water` and `uncertain` classes;
- extended graph marker rows for new interval classes;
- added tests for refined classification behavior.

Next implementation target:

- add merge/split metadata to HydrocarbonInterval;
- expose source-row coverage for each interval;
- keep Hydrocarbon Interval Engine as the only active module until Definition of Done is reached.

Validation status:

- compileall: PASS;
- pytest: 1041 passed / 0 failed.
