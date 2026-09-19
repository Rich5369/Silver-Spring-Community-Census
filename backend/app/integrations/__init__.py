"""Outbound clients for external public-data sources.

Each integration is responsible only for fetching raw payloads and the
metadata needed to cite them (request URL, parameters, retrieval time).
Normalisation happens downstream so that the provenance of a value is never
separated from the value itself.

Planned: US Census ACS, OpenStreetMap via Overpass, Montgomery County open
data. None are implemented yet.
"""
