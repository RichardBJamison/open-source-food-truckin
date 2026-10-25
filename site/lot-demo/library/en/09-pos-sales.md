---
id: pos-sales
section: Sales & money
title: Importing POS sales
summary: Bring in last night's sales from Square, Toast, Clover or any CSV.
view: sales
---
## Export from your POS
Export item sales as a CSV from your point of sale:
- **Square**: Item Sales or Item Details.
- **Toast**: Item Selection Details or Product Mix. Voids are skipped.
- **Clover**: Item Sales report. Clover files have no dates, so pick the sales date when you import.
- **Any other POS**: any CSV with an item column and a quantity column works through column mapping.

## Import it
All inputs › POS sales. Choose the file, leave **POS format** on Auto-detect (or pick one), press **Preview**, check the lines, then **Import**. If columns are wrong, set the Date, Menu item, Quantity, Unit price or Line total columns by hand.

The Square, Toast and Clover column names come from their public docs and haven't been checked against every real export yet, so always look at the preview.

## Link sales to your menu
Sales lines are matched to menu plates by their POS name. Lines marked "Not linked to a menu item" need that name added to a plate on Menu & costing (Name(s) in POS).

## POS accounts
Settings › Accounts › POS accounts labels which registers feed sales in. They are labels only.

## Deleting an import
Each import is listed with its date and line count. Delete one if you imported the wrong file.
