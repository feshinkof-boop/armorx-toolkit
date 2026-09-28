# F20 input report map

Status: NOT YET MAPPED. The receiver-alone baseline produced no reports at all (see
device-enumeration.md), which is expected: the F20 only emits once a wireless unit associates.
The 64-byte input report is vendor-defined on usage page 0xFF7A with no report ID, so every
byte must be mapped from live captures rather than from the descriptor.
