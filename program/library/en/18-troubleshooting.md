---
id: troubleshooting
section: Help
title: Something looks wrong
summary: Quick fixes for the mic, AI, POS files, odd variance, phones and language.
view: home
---
## The mic doesn't listen
Use Chrome, Edge or Safari and allow the microphone when the browser asks. Firefox can't listen. You can always type in the same box.

## AI test fails
Check the key was pasted whole, the AI service matches the key, and the model name is right. Local Ollama must be running. Some accounts need billing set up with the AI company first.

## A POS file imports wrong
Open the preview and set the columns by hand. Clover files need the sales date picked. Make sure plates on Menu & costing have the POS names your file uses.

## Variance looks huge
Usually units. Recipe quantities must be in the product's own unit (0.25 lb, not 4 oz). Also check a delivery wasn't missed and both counts covered the same products.

## A product shows zero after a daily count
Daily counts never zero what they skip. If a product shows 0, it was on the watch list and counted as 0, or it was set to 0 in Voice count's Not said list.

## A phone can't connect
Start the program with `python server.py --lan`, use the address it prints, keep the phone on the same Wi-Fi, and allow Python through the computer's firewall.

## The page switches back to English
Use the EN/ES buttons at the top. If your browser offers to translate the page, say no: the program translates itself.

## Forgot a PIN
An admin can reset it in Settings › People.
