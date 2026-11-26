# Security policy

## Supported versions

Only the latest release receives fixes. Update to the newest version through HACS or by copying
`custom_components/marstek_goedkoop_laden` again.

## Reporting a vulnerability

Please do not open a public issue for a security problem. Use
[private vulnerability reporting](https://github.com/rvdwal1991/Marstek-Cheap-Charging-for-HA/security/advisories/new)
on this repository. You can expect a first reply within a week.

The integration controls a home battery through your own Home Assistant. It does not open ports,
does not call external services and does not store credentials. Reports about unintended battery
commands or about data exposed through the dashboard cards are the most relevant.
