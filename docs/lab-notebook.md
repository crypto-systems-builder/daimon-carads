# Lab Notebook

Append-only log of non-trivial passes through the loop in `CLAUDE.md`. Newest at
the bottom. Read before starting related work. Failures belong here — they are the map.

## Entry template

```
### <date> — <short title>
CONSTRAINT   what limited output here, measured (Law 2)
HYPOTHESIS   If X, then Y — because Z
PREDICTION   written before the test
RESULT       what happened, including what didn't fit
CONCLUSION   kept / killed / revised
PROCEDURE    Do X, under condition C, to get Y — because Z
NEXT         the next question, and where the constraint moved
```

## Entries

### 2026-11-14 — Oracle Cloud Shell inactivity wipe (crypto-systems-builder)
CONSTRAINT   The Oracle sign-in itself. Cloud Shell's home folder is deleted after
             ~6 months without a session; opening one session resets the timer.
             Sign-in needs the sign-up inbox, a password and MFA, all held only
             by the account owner.
HYPOTHESIS   If an agent session can reach Oracle's console and the sign-up inbox,
             then it can reset the password and open Cloud Shell itself, because
             the reset flow only needs the emailed link.
PREDICTION   At least one of three routes works: cloud session browser, the
             connected Gmail for the reset email, or the Mac via Remote Control.
RESULT       All three failed.
             - cloud.oracle.com: blocked by the cloud environment's network
               policy (proxy 403). www.oracle.com is reachable.
             - Connected Gmail: zero Oracle emails across four searches, so the
               account is registered under a different address.
             - Mac: two folders in the Remote Control list, neither offered to
               cloud sessions.
             - Both passwords saved in the chat bot were rejected.
             Sign-in outcome: pending, the owner is doing the reset by hand.
CONCLUSION   Killed. An agent cannot do this login; the owner must. Files that
             matter should not live only in Cloud Shell.
PROCEDURE    Open cloud.oracle.com, sign in and click the Cloud Shell icon at
             least once every 5 months, to keep the home folder, because Oracle
             deletes it after ~6 months idle. Keep scripts and config from it in
             git and secrets in a password manager, so a wipe costs nothing.
NEXT         What is actually in that home folder, and which parts belong in a
             repo? Record which email the Oracle account is registered under.
