---
id: counting
section: Counting
title: Counting the truck
summary: Start a count, walk the truck section by section, save as you go and complete it.
view: count
---
## Start a count
Inventory sheets › Count sheet. Pick the **Count type** (Daily end-of-shift, Weekly or Monthly) and the **Business date**, then press **Start count walk**. The screen tells you what the count covers before you begin.

## Walk the truck
Products appear section by section in your walking order. Type the amount or use the big **−** and **+** buttons (made for one hand on a phone). Progress saves as you go, so you can stop and come back; only one count can be in progress at a time.

## Complete the count
Press **Save & complete count**. The program then updates on-hand, Variance, the Order list, Home and the reports.

## Full counts and partial counts
- A **full count** (Weekly, Monthly) covers the whole truck. Anything left blank inside it is listed as missing.
- A **partial count** (Daily end-of-shift) covers only its watch list. Everything not on the list keeps its last count: it is never set to zero or flagged missing.

## Before service or end of shift
Each count type has a timing. "Before service" means the count happened before that day's sales; "End of shift" means after them. POS files carry dates, not times, so this setting keeps usage math honest.

## Count history
Reports › Money shows every completed count with its type, scope and who counted it.

## Counting from a phone
Run the program with `python server.py --lan` on the computer, then open the address it prints on a phone on the same Wi-Fi. Only do this on a network you trust.
