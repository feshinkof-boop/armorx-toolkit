# GIP report length variants (2026-09-28)

| capture | 32-byte frames | 48-byte frames | note |
|---|---|---|---|
| power-button | last at t=45.7805 s | first at t=45.8125 s, running to 91.62 s | switchover inside one file |
| control-map | 0 | 35,992 | steady state |
| precise | 0 | 12,435 | steady state |

Both lengths share type `0x20` and the prefix `20 00 <seq> 2c`, so this is **one GIP input type with a
32-byte startup form and a 48-byte steady-state form** - not two packet types and not a decoder artefact.

The earlier 32-byte histogram was taken from a head-limited slice of the opening frames of the
power-button capture, which is exactly the startup window; generalising it was my error and is retracted.
Still unproven: what changes at t~45.8 s.
