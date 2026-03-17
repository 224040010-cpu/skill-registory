# Rule 8 Sub-Rules Reference

Complete 33 sub-rules for network registration failure diagnosis.

## EMM Cause Codes (4G/LTE)

| Sub-Rule | emm_cause | Meaning | Solution |
|----------|-----------|---------|----------|
| 8-3 | 2 | IMSI unknown | Contact carrier to verify SIM activation |
| 8-4 | 3 | Illegal UE | Check if device/SIM is blacklisted |
| 8-5 | 5 | IMEI rejected | Contact support to check IMEI |
| 8-6 | 6 | Illegal ME | Check SIM-device binding |
| 8-7 | 7 | EPS not allowed | Verify data service is enabled on SIM |
| 8-8 | 8 | All services blocked | Check SIM status and regional restrictions |
| 8-9 | 11 | PLMN not allowed | Check roaming settings |
| 8-10 | 12 | TA not allowed | Check regional restrictions |
| 8-11 | 13 | Roaming not allowed | Enable roaming on SIM plan |
| 8-12 | 14 | EPS not allowed in PLMN | Change SIM or carrier |
| 8-13 | 15 | No suitable cells | **Most common: Arrears (欠费)** - Contact carrier |
| 8-14 | 22 | Congestion | Temporary - retry later |
| 8-15 | 42 | Severe network failure | Report to carrier |
| 8-16 | Other | Uncommon code | Log and contact support |

## ESM Cause Codes (APN/PDN)

| Sub-Rule | esm_cause | Meaning | Solution |
|----------|-----------|---------|----------|
| 8-17 | 27 | Unknown APN | **Common**: Fix APN name in config |
| 8-18 | 29 | Auth failed | **Common**: Fix APN username/password |
| 8-19 | 33 | Not subscribed | Contact carrier to enable data plan |
| 8-20 | 8 | Operator barred | Check SIM terms of service |
| 8-21 | 28 | Temporarily unavailable | Retry later |
| 8-22 | 50 | PDN type not supported | Verify SIM supports IPv4 |
| 8-23 | 51 | PDN type not supported on APN | Change APN or config |
| 8-24 | 26 | Insufficient resources | Retry later |
| 8-25 | Other | Uncommon code | Log and contact support |

## Signal-Related Sub-Rules

| Sub-Rule | Condition | Meaning | Solution |
|----------|-----------|---------|----------|
| 8-26 | CSQ=99, NOSERVICE | No signal | Check antenna connection and location |
| 8-27 | CSQ<10 | Weak signal | Use external antenna, improve location |
| 8-28 | CEREG=0/2, LIMSRV | PLMN mismatch | Check roaming agreement |
| 8-29 | mode_pref≠AUTO | Wrong network mode | Set AT+QNWPREFCFG="mode_pref",AUTO |
| 8-30 | CEREG=2, CSQ>=10 | Searching | Wait or restart |
| 8-31 | CEREG=3 | Registration denied | Contact SIM provider |
| 8-32 | CEREG=4 | Unknown state | Restart device |
| 8-33 | 5gmm_cause≠0 | 5G rejection | Try 4G mode or contact carrier |

## 5GMM Cause Codes (5G)

| Sub-Rule | Condition | Meaning |
|----------|-----------|---------|
| 8-1 | CEREG=1/5, 5gmm_cause≠0 | 5G rejected but 4G OK |
| 8-2 | All cause=0 but PS limited | Possible network issue |

## CSQ Signal Strength Reference

| CSQ | dBm | Quality |
|-----|-----|---------|
| 0-9 | < -95 | Poor - consider external antenna |
| 10-14 | -95 to -85 | Fair |
| 15-19 | -85 to -75 | Good |
| 20-31 | > -75 | Excellent |
| 99 | Unknown | No signal or detection error |

Formula: `dBm = -113 + (2 × CSQ)`

## Frequency Statistics

Based on field data:
- **emm_cause=15 (Arrears)**: ~40% of Rule 8 cases
- **esm_cause=27 (Wrong APN)**: ~20%
- **CSQ issues (weak/no signal)**: ~15%
- **esm_cause=29 (Auth failed)**: ~10%
- **Other codes**: ~15%
