# Format plugin registry

`FormatPluginRegistry` binds an existing `DataFormatCapability` to a metadata scanner, quick-QC provider and importer/exporter identifiers. Heavy third-party objects must remain behind the adapter boundary.

The capability matrix is a JSON-safe Workbench contract. A new plugin must use a registered format and include tests, a license-governance entry and documentation in all three languages.
